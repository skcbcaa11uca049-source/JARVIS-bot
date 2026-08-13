import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread

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


@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} online-ku vandhudan master!")


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
        value=target.joined_at.strftime("%b %d, %Y"),
        inline=False,
    )

    if is_caller_master:
        embed.set_footer(
            text="JARVIS Protocol v1.0 | Exclusively serving Master Sunraku"
        )
    else:
        embed.set_footer(text="JARVIS Personal Assistant System v1.0")

    await interaction.response.send_message(embed=embed)


# Web server-a background-la start pannrom
keep_alive()

TOKEN = os.getenv("BOT_TOKEN")
bot.run(TOKEN)
