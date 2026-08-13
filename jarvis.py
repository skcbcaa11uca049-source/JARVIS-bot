import asyncio
import os
import traceback
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
import anthropic

# Render Port Timeout-a prevent panna dummy Web Server
app = Flask("")


@app.route("/")
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
# 🧠 AI Brain Setup (Anthropic Claude)
# ---------------------------------------------------------------------------
# Render / Replit / wherever you host this needs an env var: ANTHROPIC_API_KEY
# Get one from https://console.anthropic.com/
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("⚠️ ANTHROPIC_API_KEY illa! Render/host env vars-la add pannunga, illana AI reply work aagadhu.")
ai_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
# Use a known-good dated model snapshot (safer than a "-latest" alias which
# can change or 404 depending on your API access). Override via AI_MODEL env
# var if you want a different Claude model.
AI_MODEL = os.getenv("AI_MODEL", "claude-3-5-sonnet-20241022")

JARVIS_SYSTEM_PROMPT = (
    "You are JARVIS, a witty and helpful Tamil-English (Tanglish) speaking "
    "Discord assistant for the 'Rock Fox Games Tamil' community. Reply in "
    "friendly Tanglish (mix of Tamil + English) unless the user clearly "
    "writes in pure English or another language, then match their language. "
    "Keep answers concise and clear, suitable for a Discord chat message "
    "(avoid huge walls of text unless the question needs detail). "
    "If the user is your creator/master, be extra respectful and call them "
    "'Master'."
)

# very small in-memory per-user chat history so replies stay contextual
# (resets when the bot restarts — good enough for a Discord assistant)
chat_history = {}
MAX_HISTORY_TURNS = 6  # keep last N user+assistant pairs per user


async def ask_ai(user_id: int, question: str) -> str:
    """Send a question to Claude and return the text reply."""
    history = chat_history.get(user_id, [])
    history.append({"role": "user", "content": question})
    history = history[-(MAX_HISTORY_TURNS * 2):]

    try:
        response = await asyncio.to_thread(
            ai_client.messages.create,
            model=AI_MODEL,
            max_tokens=600,
            system=JARVIS_SYSTEM_PROMPT,
            messages=history,
        )
        answer = response.content[0].text.strip()
    except Exception as e:
        print(f"⚠️ AI error: {e}")
        traceback.print_exc()
        return "Sorry da, en AI brain-la konjam network issue vandhurichu! 🥲 Konjam nerathula try pannunga."

    history.append({"role": "assistant", "content": answer})
    chat_history[user_id] = history
    return answer


@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} online-ku vandhudan master!")


@bot.event
async def on_message(message: discord.Message):
    # ignore the bot's own messages
    if message.author.bot:
        return

    # respond whenever JARVIS is @mentioned anywhere in the message
    if bot.user in message.mentions:
        question = message.content
        for mention in (f"<@{bot.user.id}>", f"<@!{bot.user.id}>"):
            question = question.replace(mention, "")
        question = question.strip()

        if not question:
            await message.reply(
                "Sollunga master, enna ketkanum? 🤖 (e.g. `@JARVIS what is python?`)"
            )
            return

        async with message.channel.typing():
            answer = await ask_ai(message.author.id, question)
        await message.reply(answer)

    # still let prefix "!" commands (if any) work normally
    await bot.process_commands(message)


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
    joined = target.joined_at.strftime("%b %d, %Y") if target.joined_at else "Unknown"
    embed.add_field(name="Joined Date", value=joined, inline=False)
    if is_caller_master:
        embed.set_footer(
            text="JARVIS Protocol v1.0 | Exclusively serving Master Sunraku"
        )
    else:
        embed.set_footer(text="JARVIS Personal Assistant System v1.0")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ask", description="Ask JARVIS anything (AI powered)")
@app_commands.describe(question="What do you want to ask JARVIS?")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    answer = await ask_ai(interaction.user.id, question)
    if len(answer) > 1900:
        answer = answer[:1900] + "…"
    await interaction.followup.send(answer)


@bot.tree.command(name="reset", description="Clear your AI chat memory with JARVIS")
async def reset(interaction: discord.Interaction):
    chat_history.pop(interaction.user.id, None)
    await interaction.response.send_message(
        "✅ Memory clear pannitten master, fresh-a start pannalam!", ephemeral=True
    )


# Web server-a background-la start pannrom
keep_alive()

TOKEN = os.getenv("BOT_TOKEN")
bot.run(TOKEN)
