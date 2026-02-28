import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from flask import Flask
from threading import Thread

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

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    await bot.change_presence(activity=discord.Game(name="!play"))

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! 🏓 `{round(bot.latency * 1000)}ms`")

@bot.command()
async def debug(ctx):
    """Diagnostic command to check bot status"""
    msg = f"**🔍 DIAGNOSTIC REPORT**\n"
    msg += f"✅ Bot Online: YES\n"
    msg += f"📡 Latency: {round(bot.latency * 1000)}ms\n"
    
    if ctx.voice_client:
        msg += f"🔊 In Voice: YES (Channel: {ctx.voice_client.channel.name})\n"
        if ctx.voice_client.is_playing():
            msg += f"▶️ Playing: YES\n"
        elif ctx.voice_client.is_paused():
            msg += f"⏸️ Playing: PAUSED\n"
        else:
            msg += f"⏹️ Playing: NO\n"
    else:
        msg += f"🔊 In Voice: NO\n"
    
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        msg += f"📋 Queue: {len(queues[ctx.guild.id])} songs\n"
    else:
        msg += f"📋 Queue: EMPTY\n"
    
    if ctx.author.voice:
        msg += f"👤 You are in: {ctx.author.voice.channel.name}\n"
    else:
        msg += f"👤 You are: NOT in voice\n"
    
    await ctx.send(msg)

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query):
    """Play a song"""
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
        await ctx.send("🔄 Extracting audio...")
        
        # FIXED: Format the search query properly for yt-dlp
        if not query.startswith('http'):
            # This is a search query, not a URL
            search_query = f"ytsearch:{query}"
        else:
            search_query = query
        
        ytdl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
        }
        
        loop = asyncio.get_event_loop()
        
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            try:
                # Extract info
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(search_query, download=False))
                
                # Handle search results
                if 'entries' in info:
                    # Get the first search result
                    info = info['entries'][0]
                
                url = info['url']
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                
                # Format duration
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}:{seconds:02d}"
                
                await ctx.send(f"✅ Found: **{title}** ({duration_str})")
                
                # FFmpeg options
                ffmpeg_opts = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }
                
                # Create audio source
                source = discord.FFmpegPCMAudio(url, **ffmpeg_opts)
                
                # Add to queue with title
                queues[ctx.guild.id].append((source, title))
                await ctx.send(f"✅ Added to queue: **{title}**")
                
                # Start playing if not playing
                if not ctx.voice_client.is_playing():
                    await play_next(ctx)
                    
            except Exception as e:
                await ctx.send(f"❌ yt-dlp error: {str(e)[:200]}")
                print(f"Full error: {e}")
                
    except Exception as e:
        await ctx.send(f"❌ General error: {str(e)[:200]}")

async def play_next(ctx):
    """Play next in queue"""
    if ctx.guild.id not in queues or not queues[ctx.guild.id]:
        await ctx.send("🏁 Queue finished")
        return
    
    source, title = queues[ctx.guild.id].pop(0)
    
    def after_playing(error):
        if error:
            print(f"Playback error: {error}")
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    
    ctx.voice_client.play(source, after=after_playing)
    await ctx.send(f"🎵 **Now Playing:** {title}")

@bot.command(name='skip', aliases=['s'])
async def skip(ctx):
    """Skip current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped")
    else:
        await ctx.send("❌ Nothing to skip")

@bot.command(name='pause')
async def pause(ctx):
    """Pause current song"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused")
    else:
        await ctx.send("❌ Nothing playing")

@bot.command(name='resume')
async def resume(ctx):
    """Resume paused song"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed")
    else:
        await ctx.send("❌ Nothing paused")

@bot.command(name='queue', aliases=['q'])
async def queue(ctx):
    """Show queue"""
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        queue_list = queues[ctx.guild.id]
        queue_text = "\n".join([f"`{i+1}.` {title}" for i, (_, title) in enumerate(queue_list[:10])])
        if len(queue_list) > 10:
            queue_text += f"\n`... and {len(queue_list) - 10} more`"
        await ctx.send(f"**📋 Queue:**\n{queue_text}")
    else:
        await ctx.send("📋 Queue is empty")

@bot.command(name='stop')
async def stop(ctx):
    """Stop playing"""
    if ctx.voice_client:
        ctx.voice_client.stop()
        if ctx.guild.id in queues:
            queues[ctx.guild.id] = []
        await ctx.send("⏹️ Stopped")

@bot.command(name='leave')
async def leave(ctx):
    """Leave voice"""
    if ctx.voice_client:
        if ctx.guild.id in queues:
            queues[ctx.guild.id] = []
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left voice channel")

# Start
keep_alive()

if __name__ == "__main__":
    print("🔄 Starting bot...")
    bot.run(BOT_TOKEN)
