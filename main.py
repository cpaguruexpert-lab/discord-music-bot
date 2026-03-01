import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from flask import Flask
from threading import Thread
import random
import tempfile

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Flask web server
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Queue storage
queues = {}
current_songs = {}

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    print(f"✅ Connected to {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!play"))

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! 🏓 `{round(bot.latency * 1000)}ms`")

@bot.command()
async def help(ctx):
    """Show all commands"""
    embed = discord.Embed(title="🎵 Music Bot Commands", color=0x00ff00)
    embed.add_field(name="!play [song]", value="Play a song or add to queue", inline=False)
    embed.add_field(name="!pause", value="Pause current song", inline=False)
    embed.add_field(name="!resume", value="Resume paused song", inline=False)
    embed.add_field(name="!skip", value="Skip to next song", inline=False)
    embed.add_field(name="!stop", value="Stop and clear queue", inline=False)
    embed.add_field(name="!queue", value="Show all songs in queue", inline=False)
    embed.add_field(name="!np", value="Show current song", inline=False)
    embed.add_field(name="!shuffle", value="Shuffle the queue", inline=False)
    embed.add_field(name="!clear", value="Clear the queue", inline=False)
    embed.add_field(name="!remove [number]", value="Remove song at position", inline=False)
    embed.add_field(name="!leave", value="Disconnect bot", inline=False)
    embed.add_field(name="!ping", value="Check bot latency", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def debug(ctx):
    """Diagnostic command"""
    msg = f"**🔍 DIAGNOSTIC REPORT**\n"
    msg += f"✅ Bot Online: YES\n"
    msg += f"📡 Latency: {round(bot.latency * 1000)}ms\n"
    
    if ctx.voice_client:
        msg += f"🔊 In Voice: YES\n"
        if ctx.voice_client.is_playing():
            msg += f"▶️ Playing: YES\n"
            if ctx.guild.id in current_songs:
                msg += f"🎵 Current: {current_songs[ctx.guild.id]['title'][:50]}\n"
        else:
            msg += f"⏹️ Playing: NO\n"
    else:
        msg += f"🔊 In Voice: NO\n"
    
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        msg += f"📋 Queue: {len(queues[ctx.guild.id])} songs\n"
    else:
        msg += f"📋 Queue: EMPTY\n"
    
    if ctx.author.voice:
        msg += f"👤 You are in voice\n"
    else:
        msg += f"👤 You are NOT in voice\n"
    
    await ctx.send(msg)

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query):
    """Play a song or add to queue"""
    # Check voice
    if not ctx.author.voice:
        await ctx.send("❌ You're not in a voice channel!")
        return
    
    # Connect/join
    try:
        if ctx.voice_client is None:
            vc = await ctx.author.voice.channel.connect()
            await ctx.send(f"✅ Joined {ctx.author.voice.channel.name}")
        else:
            vc = ctx.voice_client
            if vc.channel != ctx.author.voice.channel:
                await vc.move_to(ctx.author.voice.channel)
                await ctx.send(f"✅ Moved to {ctx.author.voice.channel.name}")
    except Exception as e:
        await ctx.send(f"❌ Failed to join voice: {str(e)[:50]}")
        return
    
    # Initialize queue
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []
    
    await ctx.send(f"🔍 Searching for: **{query}**")
    
    try:
        # Format search query
        if not query.startswith('http'):
            search_query = f"ytsearch:{query}"
        else:
            search_query = query
        
        # FIXED: Add headers to mimic browser
        ytdl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            'extract_flat': False,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'logtostderr': False,
            'extract_flat': False,
            'add_headers': [
                ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
                ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                ('Accept-Language', 'en-us,en;q=0.5'),
                ('Sec-Fetch-Mode', 'navigate'),
            ]
        }
        
        loop = asyncio.get_event_loop()
        
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            try:
                # Extract info with retry
                info = None
                for attempt in range(3):  # Try 3 times
                    try:
                        info = await loop.run_in_executor(None, lambda: ydl.extract_info(search_query, download=False))
                        break
                    except Exception as e:
                        if attempt == 2:  # Last attempt
                            raise e
                        await asyncio.sleep(2)  # Wait 2 seconds before retry
                
                # Handle search results
                if 'entries' in info:
                    # Get the first search result
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
                    duration_str = "Unknown"
                
                # FFmpeg options
                ffmpeg_opts = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }
                
                # Create audio source
                source = discord.FFmpegPCMAudio(url, **ffmpeg_opts)
                
                # Create song info
                song_info = {
                    'source': source,
                    'title': title,
                    'url': webpage_url,
                    'duration': duration_str,
                    'requester': ctx.author.name
                }
                
                # Add to queue
                queues[ctx.guild.id].append(song_info)
                await ctx.send(f"✅ **Added:** `{title}` ({duration_str})")
                
                # Start playing if not playing
                if not ctx.voice_client.is_playing():
                    await play_next(ctx)
                    
            except Exception as e:
                error_msg = str(e)
                if "Sign in" in error_msg:
                    await ctx.send("❌ **YouTube is blocking the request. Trying alternative method...**")
                    # Try with different options
                    await play_alternative(ctx, query)
                else:
                    await ctx.send(f"❌ Error: {error_msg[:200]}")
                
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)[:200]}")

async def play_alternative(ctx, query):
    """Alternative method for blocked videos"""
    try:
        await ctx.send("🔄 Trying alternative source...")
        
        # Use ytsearch with different options
        search_query = f"ytsearch:{query}"
        
        ytdl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            'extract_flat': True,
            'nocheckcertificate': True,
        }
        
        loop = asyncio.get_event_loop()
        
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(search_query, download=False))
            
            if 'entries' in info and info['entries']:
                # Get video ID from first result
                video_id = info['entries'][0]['id']
                video_title = info['entries'][0]['title']
                
                # Now extract with different options
                ytdl_opts2 = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'source_address': '0.0.0.0',
                    'nocheckcertificate': True,
                    'add_headers': [
                        ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
                    ]
                }
                
                with yt_dlp.YoutubeDL(ytdl_opts2) as ydl2:
                    video_url = f"https://youtube.com/watch?v={video_id}"
                    info2 = await loop.run_in_executor(None, lambda: ydl2.extract_info(video_url, download=False))
                    
                    url = info2['url']
                    
                    ffmpeg_opts = {
                        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                        'options': '-vn'
                    }
                    
                    source = discord.FFmpegPCMAudio(url, **ffmpeg_opts)
                    
                    song_info = {
                        'source': source,
                        'title': video_title,
                        'url': video_url,
                        'duration': "Unknown",
                        'requester': ctx.author.name
                    }
                    
                    queues[ctx.guild.id].append(song_info)
                    await ctx.send(f"✅ **Added:** `{video_title}`")
                    
                    if not ctx.voice_client.is_playing():
                        await play_next(ctx)
            else:
                await ctx.send("❌ Could not find song")
                
    except Exception as e:
        await ctx.send(f"❌ Alternative method failed: {str(e)[:200]}")

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

@bot.command(name='skip', aliases=['s'])
async def skip(ctx):
    """Skip current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ **Skipped**")
    else:
        await ctx.send("❌ Nothing to skip")

@bot.command(name='pause')
async def pause(ctx):
    """Pause current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ **Paused**")
    else:
        await ctx.send("❌ Nothing playing")

@bot.command(name='resume')
async def resume(ctx):
    """Resume paused song"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ **Resumed**")
    else:
        await ctx.send("❌ Nothing paused")

@bot.command(name='queue', aliases=['q'])
async def queue(ctx):
    """Show queue"""
    msg = "**📋 Queue**\n"
    
    if ctx.guild.id in current_songs:
        msg += f"**Now Playing:** `{current_songs[ctx.guild.id]['title']}`\n\n"
    
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        for i, song in enumerate(queues[ctx.guild.id][:10]):
            msg += f"`{i+1}.` `{song['title'][:50]}`\n"
        
        if len(queues[ctx.guild.id]) > 10:
            msg += f"\n`... and {len(queues[ctx.guild.id]) - 10} more`"
    else:
        msg += "Queue is empty"
    
    await ctx.send(msg)

@bot.command(name='np', aliases=['nowplaying'])
async def nowplaying(ctx):
    """Show current song"""
    if ctx.guild.id in current_songs:
        song = current_songs[ctx.guild.id]
        await ctx.send(f"🎵 **Now Playing:** `{song['title']}`")
    else:
        await ctx.send("❌ Nothing playing")

@bot.command(name='shuffle')
async def shuffle(ctx):
    """Shuffle queue"""
    if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 1:
        random.shuffle(queues[ctx.guild.id])
        await ctx.send("🔀 **Queue shuffled**")
    else:
        await ctx.send("❌ Not enough songs")

@bot.command(name='clear')
async def clear(ctx):
    """Clear queue"""
    if ctx.guild.id in queues:
        queues[ctx.guild.id] = []
        await ctx.send("🗑️ **Queue cleared**")
    else:
        await ctx.send("📋 Queue already empty")

@bot.command(name='remove')
async def remove(ctx, index: int):
    """Remove song at position"""
    if ctx.guild.id in queues and 0 < index <= len(queues[ctx.guild.id]):
        removed = queues[ctx.guild.id].pop(index - 1)
        await ctx.send(f"❌ Removed: `{removed['title'][:50]}`")
    else:
        await ctx.send("❌ Invalid position")

@bot.command(name='leave')
async def leave(ctx):
    """Leave voice"""
    if ctx.voice_client:
        if ctx.guild.id in queues:
            queues[ctx.guild.id] = []
        current_songs.pop(ctx.guild.id, None)
        await ctx.voice_client.disconnect()
        await ctx.send("👋 **Left voice channel**")

# Start
keep_alive()

if __name__ == "__main__":
    print("🔄 Starting bot...")
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"❌ Error: {e}")
