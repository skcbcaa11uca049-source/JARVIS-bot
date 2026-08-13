import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
from google import genai
from google.genai import types

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

JARVIS_SYSTEM_PROMPT = (
    "You are JARVIS, a witty, authentic, and helpful Tamil-English (Tanglish) speaking "
    "Discord assistant for the 'Rock Fox Games Tamil' community. Reply in "
    "friendly Tanglish (mix of Tamil + English) unless the user clearly "
    "writes in pure English or another language, then match their language. "
    "Keep answers concise and clear, suitable for a Discord chat message. "
    "If the user is your creator/master (User ID: 1503884431453327400), be extra respectful and call them 'Master'."
)

async def ask_gemini(question: str) -> str:
    """Send a question to Gemini AI and return the text reply."""
    if not gemini_client:
        return "⚠️ Master, Render-la `GEMINI_API_KEY` set aagala! Check Environment Variables."

    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model="gemini-1.5-flash",  # High limit free model (1,500 RPD)
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=JARVIS_SYSTEM_PROMPT,
                max_output_tokens=800,
            )
        )
        if response and response.text:
            return response.text.strip()
        return "Master, response empty-a vandhurukku!"
    except Exception as e:
        print(f"⚠️ Gemini API Error Details: {e}")
        return f"Sorry Master, API Error: `{e}`"

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
            answer = await ask_gemini(question)
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
    answer = await ask_gemini(question)
    if len(answer) > 1900:
        answer = answer[:1900] + "…"
    await interaction.followup.send(answer)

# Web server start
keep_alive()

TOKEN = os.getenv("BOT_TOKEN")
bot.run(TOKEN)
