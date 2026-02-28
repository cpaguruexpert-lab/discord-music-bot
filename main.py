import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# Get token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Flask web server for Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    print(f"✅ Connected to {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Game(name="!play"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! 🏓 {round(bot.latency * 1000)}ms")

@bot.command()
async def play(ctx, *, query):
    if not ctx.author.voice:
        await ctx.send("❌ Join a voice channel first!")
        return
    await ctx.send(f"🔍 Searching for: {query}")

# Start both web server and bot
keep_alive()

try:
    print("🔄 Starting Discord bot...")
    bot.run(BOT_TOKEN)
except Exception as e:
    print(f"❌ Error: {e}")
