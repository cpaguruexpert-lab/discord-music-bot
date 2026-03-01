import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from flask import Flask
from threading import Thread
import random

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Flask web server for Render (keeps bot alive)
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

# Remove default help command so we can use our own
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Queue storage for each server
queues = {}
current_songs = {}

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    print(f"✅ Connected to {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!play"))

# ==================== HELPER FUNCTIONS ====================

async def play_next(ctx):
    """Play the next song in queue"""
    if ctx.guild.id not in queues or not queues[ctx.guild.id]:
        current_songs.pop(ctx.guild.id, None)
        await ctx.send("🏁 **Queue finished!** Add more with `!play`")
        return
    
    song_info = queues[ctx.guild.id].pop(0)
    source = song_info['source']
    title = song_info['title']
    
    current_songs[ctx.guild.id] = song_info
    
    def after_playing(error):
        if error:
            print(f"Playback error: {error}")
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    
    ctx.voice_client.play(source, after=after_playing)
    await ctx.send(f"🎵 **Now Playing:** `{title}`")

# ==================== COMMANDS ====================

@bot.command(name='help')
async def help_command(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🎵 Music Bot Commands",
        description="Here are all the commands you can use:",
        color=0x00ff00
    )
    embed.add_field(name="**🎵 Music Controls**", value="`!play [song]` - Play or add song to queue\n`!pause` - Pause current song\n`!resume` - Resume paused song\n`!skip` - Skip to next song\n`!stop` - Stop and clear queue\n`!volume [0-100]` - Adjust volume", inline=False)
    embed.add_field(name="**📋 Queue Management**", value="`!queue` - Show all songs in queue\n`!np` - Show currently playing song\n`!shuffle` - Shuffle the queue\n`!clear` - Clear the queue\n`!remove [number]` - Remove song at position", inline=False)
    embed.add_field(name="**⚙️ Other Commands**", value="`!ping` - Check bot latency\n`!leave` - Disconnect bot from voice\n`!help` - Show this menu", inline=False)
    embed.set_footer(text="Join a voice channel first before using !play!")
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    """Check bot latency"""
    await ctx.send(f"Pong! 🏓 `{round(bot.latency * 1000)}ms`")

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query):
    """Play a song or add to queue"""
    # Check if user is in voice channel
    if not ctx.author.voice:
        await ctx.send("❌ You need to be in a **voice channel** first!")
        return
    
    # Connect to voice channel
    try:
        if ctx.voice_client is None:
            vc = await ctx.author.voice.channel.connect()
            await ctx.send(f"✅ Joined **{ctx.author.voice.channel.name}**")
        else:
            vc = ctx.voice_client
            if vc.channel != ctx.author.voice.channel:
                await vc.move_to(ctx.author.voice.channel)
                await ctx.send(f"✅ Moved to **{ctx.author.voice.channel.name}**")
    except Exception as e:
        await ctx.send(f"❌ Failed to join voice: {str(e)[:50]}")
        return
    
    # Initialize queue for this server
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []
    
    await ctx.send(f"🔍 Searching for: **{query}**")
    
    try:
        # Format search query for YouTube
        if not query.startswith('http'):
            search_query = f"ytsearch:{query}"
        else:
            search_query = query
        
        # YouTube DL options with browser headers to avoid blocking
        ytdl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'extract_flat': False,
            'add_headers': [
                ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
                ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                ('Accept-Language', 'en-us,en;q=0.5'),
            ]
        }
        
        loop = asyncio.get_event_loop()
        
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            try:
                # Extract video info
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(search_query, download=False))
                
                # Handle search results
                if 'entries' in info:
                    info = info['entries'][0]
                
                url = info['url']
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                webpage_url = info.get('webpage_url', query)
                
                # Format duration
                if duration:
                    minutes = duration // 60
                    seconds = duration % 60
                    duration_str = f"{minutes}:{seconds:02d}"
                else:
                    duration_str = "Live"
                
                # FFmpeg options for audio streaming
                ffmpeg_opts = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }
                
                # Create audio source
                source = discord.FFmpegPCMAudio(url, **ffmpeg_opts)
                
                # Create song info dictionary
                song_info = {
                    'source': source,
                    'title': title,
                    'url': webpage_url,
                    'duration': duration_str,
                    'requester': ctx.author.name
                }
                
                # Add to queue
                queues[ctx.guild.id].append(song_info)
                await ctx.send(f"✅ **Added to queue:** `{title}` ({duration_str})")
                
                # Start playing if not already playing
                if not ctx.voice_client.is_playing():
                    await play_next(ctx)
                    
            except Exception as e:
                error_msg = str(e)
                if "Sign in" in error_msg:
                    await ctx.send("❌ **YouTube is blocking the request. Please try a different song.**")
                else:
                    await ctx.send(f"❌ Error: {error_msg[:200]}")
                
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)[:200]}")

@bot.command(name='pause')
async def pause(ctx):
    """Pause current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ **Paused**")
    else:
        await ctx.send("❌ Nothing is playing")

@bot.command(name='resume')
async def resume(ctx):
    """Resume paused song"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ **Resumed**")
    else:
        await ctx.send("❌ Nothing is paused")

@bot.command(name='skip', aliases=['s'])
async def skip(ctx):
    """Skip current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ **Skipped**")
    else:
        await ctx.send("❌ Nothing to skip")

@bot.command(name='stop')
async def stop(ctx):
    """Stop playing and clear queue"""
    if ctx.voice_client:
        ctx.voice_client.stop()
        if ctx.guild.id in queues:
            queues[ctx.guild.id] = []
        current_songs.pop(ctx.guild.id, None)
        await ctx.send("⏹️ **Stopped and queue cleared**")
    else:
        await ctx.send("❌ Bot is not in a voice channel")

@bot.command(name='queue', aliases=['q'])
async def queue(ctx):
    """Show current queue"""
    embed = discord.Embed(title="📋 Music Queue", color=0x00ff00)
    
    # Show currently playing
    if ctx.guild.id in current_songs:
        current = current_songs[ctx.guild.id]
        embed.add_field(name="**Now Playing:**", value=f"`{current['title']}` ({current['duration']})", inline=False)
    else:
        embed.add_field(name="**Now Playing:**", value="Nothing", inline=False)
    
    # Show upcoming songs
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        queue_list = queues[ctx.guild.id]
        queue_text = ""
        for i, song in enumerate(queue_list[:10]):
            queue_text += f"`{i+1}.` `{song['title'][:50]}` ({song['duration']})\n"
        
        if len(queue_list) > 10:
            queue_text += f"\n`... and {len(queue_list) - 10} more songs`"
        
        embed.add_field(name="**Up Next:**", value=queue_text, inline=False)
    else:
        embed.add_field(name="**Up Next:**", value="Queue is empty", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='np', aliases=['nowplaying'])
async def nowplaying(ctx):
    """Show current song"""
    if ctx.guild.id in current_songs:
        song = current_songs[ctx.guild.id]
        await ctx.send(f"🎵 **Now Playing:** `{song['title']}` ({song['duration']})")
    else:
        await ctx.send("❌ Nothing is playing")

@bot.command(name='shuffle')
async def shuffle(ctx):
    """Shuffle the queue"""
    if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 1:
        random.shuffle(queues[ctx.guild.id])
        await ctx.send("🔀 **Queue shuffled**")
    else:
        await ctx.send("❌ Not enough songs to shuffle")

@bot.command(name='clear')
async def clear(ctx):
    """Clear the queue"""
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        queues[ctx.guild.id] = []
        await ctx.send("🗑️ **Queue cleared**")
    else:
        await ctx.send("📋 Queue is already empty")

@bot.command(name='remove')
async def remove(ctx, index: int):
    """Remove a song from queue by position"""
    if ctx.guild.id in queues and 0 < index <= len(queues[ctx.guild.id]):
        removed = queues[ctx.guild.id].pop(index - 1)
        await ctx.send(f"❌ Removed: `{removed['title'][:50]}`")
    else:
        await ctx.send("❌ Invalid position number")

@bot.command(name='volume', aliases=['vol'])
async def volume(ctx, vol: int):
    """Set volume (0-100)"""
    if 0 <= vol <= 100:
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = vol / 100
            await ctx.send(f"🔊 Volume set to **{vol}%**")
        else:
            await ctx.send("❌ Nothing is playing")
    else:
        await ctx.send("❌ Volume must be between 0 and 100")

@bot.command(name='leave', aliases=['dc', 'disconnect'])
async def leave(ctx):
    """Leave voice channel"""
    if ctx.voice_client:
        if ctx.guild.id in queues:
            queues[ctx.guild.id] = []
        current_songs.pop(ctx.guild.id, None)
        await ctx.voice_client.disconnect()
        await ctx.send("👋 **Disconnected**")
    else:
        await ctx.send("❌ Bot is not in a voice channel")

# ==================== START BOT ====================

# Start the Flask web server
keep_alive()

if __name__ == "__main__":
    print("🔄 Starting Discord bot...")
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"❌ Error: {e}")
