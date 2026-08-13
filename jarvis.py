import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
from openai import OpenAI

# Render Port Timeout-a prevent panna Web Server
app = Flask("")

@app.route('/')
def home():
    return "JARVIS (DeepSeek Powered) is Online 24/7!"

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
# 🧠 DeepSeek AI Brain Setup
# ---------------------------------------------------------------------------
deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

JARVIS_SYSTEM_PROMPT = (
    "You are JARVIS, a witty, authentic, and helpful Tamil-English (Tanglish) speaking "
    "Discord assistant for the 'Rock Fox Games Tamil' community. Reply in "
    "friendly Tanglish (mix of Tamil + English) unless the user clearly "
    "writes in pure English or another language, then match their language. "
    "Keep answers concise and clear, suitable for a Discord chat message. "
    "If the user is your creator/master (User ID: 1503884431453327400), be extra respectful and call them 'Master'."
)

async def ask_deepseek(question: str) -> str:
    """Send a question to DeepSeek AI and return the text reply."""
    try:
        response = await asyncio.to_thread(
            deepseek_client.chat.completions.create,
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": JARVIS_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            max_tokens=800,
            temperature=0.7,
        )
        if response and response.choices:
            return response.choices[0].message.content.strip()
        return "Master, response empty-a vandhurukku!"
    except Exception as e:
        print(f"⚠️ DeepSeek API ERROR: {e}")
        return f"Sorry Master, internal API issue: `{e}`"

@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} (DeepSeek AI Powered) online-ku vandhudan master!")

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
            answer = await ask_deepseek(question)
        await message.reply(answer)

    await bot.process_commands(message)

@bot.tree.command(name="hello", description="Greets the user")
async def hello(interaction: discord.Interaction):
    user = interaction.user
    if user.id == MASTER_ID:
        greeting = f"Vanakkam **Master {user.mention}**! 👑 Command me, I am at your service!"
    else:
        greeting = f"Vanakkam Agent {user.mention}! Naan thaan JARVIS, Rock Fox Games Tamil assistant!"
    await interaction.response.send_message(greeting)

@bot.tree.command(name="ask", description="Ask JARVIS anything (Powered by DeepSeek AI)")
@app_commands.describe(question="What do you want to ask JARVIS?")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    answer = await ask_deepseek(question)
    if len(answer) > 1900:
        answer = answer[:1900] + "…"
    await interaction.followup.send(answer)

# Web server start
keep_alive()

TOKEN = os.getenv("BOT_TOKEN")
bot.run(TOKEN)
