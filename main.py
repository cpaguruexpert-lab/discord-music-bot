import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
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

# Music player setup
queues = {}

class MusicPlayer:
    def __init__(self):
        self.queue = []
        self.current = None
        self.vc = None
        self.loop = False

players = {}

# YouTube DL options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

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

@bot.command(name="play", aliases=["p", "pplay"])
async def play(ctx, *, query):
    """Play a song from YouTube"""
    # Check if user is in voice channel
    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a voice channel first!")
        return
    
    # Connect to voice channel
    voice_channel = ctx.author.voice.channel
    
    if ctx.voice_client is None:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client
        if vc.channel != voice_channel:
            await vc.move_to(voice_channel)
    
    # Create player for this guild if not exists
    if ctx.guild.id not in players:
        players[ctx.guild.id] = MusicPlayer()
        players[ctx.guild.id].vc = vc
    
    # Let user know we're searching
    await ctx.send(f"🔍 Searching for: **{query}**")
    
    try:
        # Get the audio source
        player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
        
        # Add to queue
        players[ctx.guild.id].queue.append(player)
        
        await ctx.send(f"✅ Added to queue: **{player.title}**")
        
        # If not playing, start playing
        if not vc.is_playing():
            await play_next(ctx)
            
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)[:100]}")

async def play_next(ctx):
    """Play the next song in queue"""
    if ctx.guild.id not in players:
        return
    
    player = players[ctx.guild.id]
    
    if len(player.queue) > 0:
        # Get next song
        next_player = player.queue.pop(0)
        player.current = next_player
        
        # Play it
        player.vc.play(next_player, after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(ctx), bot.loop
        ))
        
        await ctx.send(f"🎵 Now playing: **{next_player.title}**")
    else:
        player.current = None

@bot.command(name="np", aliases=["nowplaying", "now"])
async def nowplaying(ctx):
    """Show currently playing song"""
    if ctx.guild.id in players and players[ctx.guild.id].current:
        await ctx.send(f"🎵 Now playing: **{players[ctx.guild.id].current.title}**")
    else:
        await ctx.send("❌ Nothing is playing right now")

@bot.command(name="pause", aliases=["pa"])
async def pause(ctx):
    """Pause the current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused")
    else:
        await ctx.send("❌ Nothing is playing")

@bot.command(name="resume", aliases=["r"])
async def resume(ctx):
    """Resume the paused song"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed")
    else:
        await ctx.send("❌ Nothing is paused")

@bot.command(name="skip", aliases=["s"])
async def skip(ctx):
    """Skip the current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped")
        await play_next(ctx)
    else:
        await ctx.send("❌ Nothing to skip")

@bot.command(name="queue")
async def queue(ctx):
    """Show the current queue"""
    if ctx.guild.id in players and players[ctx.guild.id].queue:
        queue_list = players[ctx.guild.id].queue
        queue_text = "\n".join([f"{i+1}. {song.title}" for i, song in enumerate(queue_list[:10])])
        await ctx.send(f"**Queue:**\n{queue_text}")
    else:
        await ctx.send("📋 Queue is empty")

@bot.command(name="volume", aliases=["vol", "v"])
async def volume(ctx, vol: int):
    """Set volume (0-100)"""
    if 0 <= vol <= 100:
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = vol / 100
            await ctx.send(f"🔊 Volume set to {vol}%")
        else:
            await ctx.send("❌ Nothing is playing")
    else:
        await ctx.send("❌ Volume must be between 0 and 100")

@bot.command(name="loop")
async def loop(ctx):
    """Toggle loop mode"""
    if ctx.guild.id in players:
        players[ctx.guild.id].loop = not players[ctx.guild.id].loop
        await ctx.send(f"🔄 Loop: {'ON' if players[ctx.guild.id].loop else 'OFF'}")

@bot.command(name="leave", aliases=["disconnect"])
async def leave(ctx):
    """Leave the voice channel"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        if ctx.guild.id in players:
            del players[ctx.guild.id]
        await ctx.send("👋 Disconnected")

# Start both web server and bot
keep_alive()

try:
    print("🔄 Starting Discord bot...")
    bot.run(BOT_TOKEN)
except Exception as e:
    print(f"❌ Error: {e}")
