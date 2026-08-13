import asyncio
import os
import time
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
# Render Port Timeout-a prevent panna Web Server
app = Flask("")
@app.route('/')
def home():
    return "JARVIS is Online 24/7!"
def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
def keep_alive():
    t = Thread(target=run_web)
    t.start()
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Commands synced to Discord UI!")
bot = Client()
MASTER_ID = 1503884431453327400
# ---------------------------------------------------------------------------
# 🧠 Gemini AI Brain Setup
# ---------------------------------------------------------------------------
api_key = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=api_key) if api_key else None

# Gemini model names AND free-tier quotas change over time (the 1.5 series
# was retired; some newer models like a hypothetical "3.6-flash" ship with a
# tiny free quota e.g. 20 requests/day while older/"-lite" models usually
# have a much more generous free allowance). Instead of hardcoding one model
# and hoping it stays available/affordable, we:
#   1. Ask Gemini which Flash-class models actually exist for this API key.
#   2. Order them so cheaper/"-lite" models (higher free quota) are tried
#      before newer flagship ones (lower free quota, more likely to 429).
#   3. At request time, if a model returns 429 (quota) or 503 (overloaded),
#      put it on a temporary cooldown and automatically retry with the next
#      model in the list — so one exhausted/overloaded model doesn't take
#      the whole bot down.
_manual_override = os.getenv("AI_MODEL")


def discover_gemini_models(client) -> list:
    """Return an ordered list of Flash-class Gemini models live for this key."""
    if _manual_override:
        base = [_manual_override]
    else:
        base = []
    if not client:
        return base or ["gemini-2.0-flash"]
    try:
        live = []
        for m in client.models.list():
            name = m.name.split("/")[-1] if "/" in m.name else m.name
            actions = m.supported_actions or []
            if actions and "generateContent" not in actions:
                continue
            if "flash" in name.lower():
                live.append(name)
        seen = set()
        live = [n for n in live if not (n in seen or seen.add(n))]
        # cheaper "-lite" variants first (generally a much higher free
        # quota), then the rest in whatever order Google returned them
        live.sort(key=lambda n: 0 if "lite" in n.lower() else 1)
        for name in live:
            if name not in base:
                base.append(name)
        print(f"✅ Gemini models available for this key: {base}")
    except Exception as e:
        print(f"⚠️ Could not list Gemini models, using defaults. Reason: {e}")
        base += ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
    return base or ["gemini-2.0-flash"]


CANDIDATE_MODELS = discover_gemini_models(gemini_client)
# model_name -> unix timestamp until which we skip it (rate-limited/overloaded)
_model_cooldown = {}

JARVIS_SYSTEM_PROMPT = (
    "You are JARVIS, a witty, authentic, and helpful Tamil-English (Tanglish) speaking "
    "Discord assistant for the 'Rock Fox Games Tamil' community. Reply in "
    "friendly Tanglish (mix of Tamil + English) unless the user clearly "
    "writes in pure English or another language, then match their language. "
    "Keep answers concise and clear, suitable for a Discord chat message. "
    "If the user is your creator/master (User ID: 1503884431453327400), be extra respectful and call them 'Master'."
)
# Per-user conversation memory, so follow-ups like "ama full ah sollu" or
# "adha vera maadhiri sollu" actually know what the previous message was
# about. Resets when the bot restarts (in-memory only) — that's fine for a
# Discord assistant. Use /reset to clear it manually mid-conversation.
chat_history = {}
MAX_HISTORY_TURNS = 8  # keep last N user+model exchanges per user


async def ask_gemini(user_id: int, question: str) -> str:
    """Send a question (with this user's recent history) to Gemini AI."""
    if not gemini_client:
        return "⚠️ Master, Render-la `GEMINI_API_KEY` set aagala! Check Environment Variables."

    history = chat_history.get(user_id, [])
    history.append({"role": "user", "parts": [{"text": question}]})
    history = history[-(MAX_HISTORY_TURNS * 2):]

    now = time.time()
    last_error = None
    answer = None

    for model_name in CANDIDATE_MODELS:
        cooldown_until = _model_cooldown.get(model_name, 0)
        if cooldown_until > now:
            continue  # this model recently 429'd / 503'd — skip it for now
        try:
            response = await asyncio.to_thread(
                gemini_client.models.generate_content,
                model=model_name,
                contents=history,
                config=types.GenerateContentConfig(
                    system_instruction=JARVIS_SYSTEM_PROMPT,
                    max_output_tokens=800,
                )
            )
            if not (response and response.text):
                last_error = "Master, response empty-a vandhurukku!"
                continue
            answer = response.text.strip()
            break
        except genai_errors.APIError as e:
            print(f"⚠️ Gemini API Error on '{model_name}': {e}")
            if e.code == 429:
                # daily/per-minute quota hit — cool this model down for 10 min
                _model_cooldown[model_name] = now + 600
                last_error = f"Sorry Master, API Error: `{e}`"
                continue
            if e.code == 503:
                # temporarily overloaded on Google's side — cool down 30s
                # and try the next model straight away
                _model_cooldown[model_name] = now + 30
                last_error = f"Sorry Master, API Error: `{e}`"
                continue
            # anything else (bad request, auth error, etc.) won't be fixed
            # by switching models — stop trying and report it
            last_error = f"Sorry Master, API Error: `{e}`"
            break
        except Exception as e:
            print(f"⚠️ Unexpected Gemini error on '{model_name}': {e}")
            last_error = f"Sorry Master, API Error: `{e}`"
            break

    if answer is None:
        return last_error or "Sorry Master, ellaa AI models-um busy-ah irukku, konjam neram kalichu try pannunga! 🥲"

    history.append({"role": "model", "parts": [{"text": answer}]})
    chat_history[user_id] = history
    return answer
@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} online-ku vandhudan master!")
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if bot.user in message.mentions:
        question = message.content
        for mention in (f"<@{bot.user.id}>", f"<@!{bot.user.id}>"):
            question = question.replace(mention, "")
        question = question.strip()
        if not question:
            await message.reply("Sollunga master, enna ketkanum? 🤖")
            return
        async with message.channel.typing():
            answer = await ask_gemini(message.author.id, question)
        await message.reply(answer)
    await bot.process_commands(message)
# ---------------------------------------------------------------------------
# 📜 Discord Commands
# ---------------------------------------------------------------------------
@bot.tree.command(name="hello", description="Greets the user")
async def hello(interaction: discord.Interaction):
    user = interaction.user
    if user.id == MASTER_ID:
        greeting = f"Vanakkam **Master {user.mention}**! 👑 Command me, I am at your service!"
    else:
        greeting = f"Vanakkam Agent {user.mention}! Naan thaan JARVIS, Rock Fox Games Tamil assistant!"
    await interaction.response.send_message(greeting)
@bot.tree.command(
    name="aboutme", description="Get details about yourself or another member"
)
@app_commands.describe(member="Select a member to view details")
async def tell_about_me(
    interaction: discord.Interaction, member: discord.Member = None
):
    caller = interaction.user
    target = member or caller
    is_caller_master = caller.id == MASTER_ID
    roles = [
        role.mention for role in target.roles if role.name != "@everyone"
    ]
    roles_str = ", ".join(roles) if roles else "No Special Roles"
    if target.id == MASTER_ID:
        title = f"👑 Master Profile: {target.display_name}"
        desc = "**The Boss & Creator of JARVIS** | Lead Game Developer 🚀"
        color = discord.Color.gold()
    else:
        title = f"👤 Member Profile: {target.display_name}"
        desc = "Valuable Member of Rock Fox Games Tamil"
        color = discord.Color.blue()
    embed = discord.Embed(title=title, description=desc, color=color)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
    embed.add_field(name="Username", value=target.name, inline=True)
    embed.add_field(name="User ID", value=target.id, inline=True)
    embed.add_field(name="Server Roles", value=roles_str, inline=False)
    embed.add_field(
        name="Joined Date",
        value=target.joined_at.strftime("%b %d, %Y") if target.joined_at else "Unknown",
        inline=False,
    )
    if is_caller_master:
        embed.set_footer(
            text="JARVIS Protocol v1.0 | Exclusively serving Master Sunraku"
        )
    else:
        embed.set_footer(text="JARVIS Personal Assistant System v1.0")
    await interaction.response.send_message(embed=embed)
@bot.tree.command(name="ask", description="Ask JARVIS anything (Powered by Gemini AI)")
@app_commands.describe(question="What do you want to ask JARVIS?")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    answer = await ask_gemini(interaction.user.id, question)
    if len(answer) > 1900:
        answer = answer[:1900] + "…"
    await interaction.followup.send(answer)
@bot.tree.command(name="reset", description="Clear your AI chat memory with JARVIS")
async def reset(interaction: discord.Interaction):
    chat_history.pop(interaction.user.id, None)
    await interaction.response.send_message(
        "✅ Memory clear pannitten master, fresh-a start pannalam!", ephemeral=True
    )
# Web server start
keep_alive()
TOKEN = os.getenv("BOT_TOKEN")
bot.run(TOKEN)
