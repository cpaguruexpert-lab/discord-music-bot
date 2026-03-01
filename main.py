import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from flask import Flask
from threading import Thread
import random
import json
import datetime
import re
from collections import deque

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Flask web server for 24/7
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# ==================== DATABASE SIMULATION ====================
# In a real bot, you'd use MongoDB. For simplicity, using JSON files
# But this structure shows how premium/playlists work

class Database:
    def __init__(self):
        self.prefixes = {}  # guild_id: prefix
        self.languages = {}  # guild_id: language
        self.premium = {}    # guild_id: bool
        self.playlists = {}  # user_id: {name: [songs]}
        self.settings = {}   # guild_id: settings
    
    async def get_prefix(self, guild_id):
        return self.prefixes.get(guild_id, "!")
    
    async def set_prefix(self, guild_id, prefix):
        self.prefixes[guild_id] = prefix
    
    async def get_lang(self, guild_id):
        return self.languages.get(guild_id, "en")
    
    async def set_lang(self, guild_id, lang):
        self.languages[guild_id] = lang
    
    async def is_premium(self, guild_id):
        return self.premium.get(guild_id, False)
    
    async def set_premium(self, guild_id, status):
        self.premium[guild_id] = status
    
    async def create_playlist(self, user_id, name):
        if user_id not in self.playlists:
            self.playlists[user_id] = {}
        self.playlists[user_id][name] = []
    
    async def add_to_playlist(self, user_id, name, song):
        if user_id in self.playlists and name in self.playlists[user_id]:
            self.playlists[user_id][name].append(song)
    
    async def get_playlist(self, user_id, name):
        if user_id in self.playlists and name in self.playlists[user_id]:
            return self.playlists[user_id][name]
        return None
    
    async def get_all_playlists(self, user_id):
        if user_id in self.playlists:
            return list(self.playlists[user_id].keys())
        return []
    
    async def delete_playlist(self, user_id, name):
        if user_id in self.playlists and name in self.playlists[user_id]:
            del self.playlists[user_id][name]

db = Database()

# ==================== MULTI-LANGUAGE SUPPORT ====================

translations = {
    "en": {
        "no_voice": "❌ You need to be in a **voice channel** first!",
        "joined": "✅ Joined **{channel}**",
        "moved": "✅ Moved to **{channel}**",
        "searching": "🔍 **Finding:** `{query}`",
        "not_found": "❌ **Could not find that song.**",
        "added": "✅ **Added:** `{title}` ({duration})",
        "now_playing": "🎵 **Now Playing:** `{title}`",
        "queue_finished": "🏁 **Queue finished!** Add more with `!play`",
        "paused": "⏸️ **Paused**",
        "resumed": "▶️ **Resumed**",
        "skipped": "⏭️ **Skipped**",
        "stopped": "⏹️ **Stopped and queue cleared**",
        "nothing_playing": "❌ Nothing is playing",
        "nothing_paused": "❌ Nothing is paused",
        "nothing_to_skip": "❌ Nothing to skip",
        "queue_empty": "📋 Queue is empty",
        "volume_set": "🔊 Volume set to **{vol}%**",
        "invalid_volume": "❌ Volume must be 0-100",
        "disconnected": "👋 **Disconnected**",
        "not_in_voice": "❌ Bot is not in voice",
        "premium_only": "⭐ This command is only available for **Premium servers**!",
        "invalid_position": "❌ Invalid position",
        "removed": "❌ Removed: `{title}`",
        "shuffled": "🔀 **Queue shuffled**",
        "not_enough": "❌ Not enough songs to shuffle",
        "playlist_created": "✅ Playlist **{name}** created!",
        "playlist_deleted": "✅ Playlist **{name}** deleted!",
        "playlist_added": "✅ Added to playlist **{name}**",
        "playlist_loaded": "✅ Loaded playlist **{name}** into queue",
        "no_playlists": "📭 You have no playlists",
        "playlists_list": "📋 Your playlists: {list}",
        "prefix_changed": "✅ Prefix changed to `{prefix}`",
        "language_changed": "✅ Language set to **{lang}**",
        "247_enabled": "✅ 24/7 mode enabled for this server",
        "247_disabled": "✅ 24/7 mode disabled",
        "setup_complete": "✅ Premium setup complete!",
    },
    "es": {
        "no_voice": "❌ ¡Necesitas estar en un **canal de voz** primero!",
        "joined": "✅ Unido a **{channel}**",
        "moved": "✅ Movido a **{channel}**",
        "searching": "🔍 **Buscando:** `{query}`",
        "not_found": "❌ **No se pudo encontrar esa canción.**",
        "added": "✅ **Añadido:** `{title}` ({duration})",
        "now_playing": "🎵 **Reproduciendo:** `{title}`",
        "queue_finished": "🏁 **¡Cola terminada!** Añade más con `!play`",
        "paused": "⏸️ **Pausado**",
        "resumed": "▶️ **Reanudado**",
        "skipped": "⏭️ **Saltado**",
        "stopped": "⏹️ **Detenido y cola limpiada**",
        "nothing_playing": "❌ No hay nada reproduciéndose",
        "nothing_paused": "❌ No hay nada pausado",
        "nothing_to_skip": "❌ Nada que saltar",
        "queue_empty": "📋 La cola está vacía",
        "volume_set": "🔊 Volumen establecido al **{vol}%**",
        "invalid_volume": "❌ El volumen debe ser 0-100",
        "disconnected": "👋 **Desconectado**",
        "not_in_voice": "❌ El bot no está en un canal de voz",
        "premium_only": "⭐ ¡Este comando solo está disponible para **servidores Premium**!",
        "invalid_position": "❌ Posición inválida",
        "removed": "❌ Eliminado: `{title}`",
        "shuffled": "🔀 **Cola mezclada**",
        "not_enough": "❌ No hay suficientes canciones para mezclar",
        "playlist_created": "✅ ¡Lista de reproducción **{name}** creada!",
        "playlist_deleted": "✅ ¡Lista de reproducción **{name}** eliminada!",
        "playlist_added": "✅ Añadido a la lista **{name}**",
        "playlist_loaded": "✅ Lista **{name}** cargada en la cola",
        "no_playlists": "📭 No tienes listas de reproducción",
        "playlists_list": "📋 Tus listas: {list}",
        "prefix_changed": "✅ Prefijo cambiado a `{prefix}`",
        "language_changed": "✅ Idioma cambiado a **{lang}**",
        "247_enabled": "✅ Modo 24/7 activado para este servidor",
        "247_disabled": "✅ Modo 24/7 desactivado",
        "setup_complete": "✅ ¡Configuración Premium completada!",
    }
}

def get_text(guild_id, key, **kwargs):
    lang = db.languages.get(guild_id, "en")
    text = translations.get(lang, translations["en"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

# ==================== MUSIC PLAYER ====================

class MusicPlayer:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.queue = deque()
        self.current = None
        self.loop = False
        self.loop_queue = False
        self.volume = 0.5
        self.filter = None
        self.vc = None
        self.text_channel = None
        self._24_7 = False

players = {}

# ==================== YT-DLP CONFIGURATION ====================

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'nocheckcertificate': True,
    'extract_flat': False,
    'source_address': '0.0.0.0',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'extractor_args': {
        'youtube': {
            'skip': ['dash', 'hls', 'webpage'],
            'player_client': ['android', 'web'],
        }
    },
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

def extract_audio(query):
    """Extract audio from any source"""
    try:
        ydl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
        
        # Handle search queries
        if not query.startswith(('http://', 'https://')):
            search_query = f"ytsearch1:{query}"
            info = ydl.extract_info(search_query, download=False)
            if info and 'entries' in info and info['entries']:
                info = info['entries'][0]
        else:
            info = ydl.extract_info(query, download=False)
        
        if not info:
            return None, None, None, None
        
        # Get audio URL
        audio_url = info.get('url')
        if not audio_url and 'formats' in info:
            for f in info['formats']:
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    audio_url = f.get('url')
                    break
        
        title = info.get('title', 'Unknown')
        duration = info.get('duration', 0)
        webpage_url = info.get('webpage_url', query)
        
        # Determine source
        source = "YouTube"
        if 'spotify.com' in webpage_url:
            source = "Spotify"
        elif 'soundcloud.com' in webpage_url:
            source = "SoundCloud"
        elif 'deezer.com' in webpage_url:
            source = "Deezer"
        elif 'twitch.tv' in webpage_url:
            source = "Twitch"
        elif 'apple.com' in webpage_url:
            source = "Apple Music"
        elif 'bandcamp.com' in webpage_url:
            source = "Bandcamp"
        
        return audio_url, title, duration, source
        
    except Exception as e:
        print(f"Extraction error: {e}")
        return None, None, None, None

async def play_next(ctx, guild_id):
    """Play next song in queue"""
    player = players.get(guild_id)
    if not player or not player.vc:
        return
    
    # Handle loop modes
    if player.loop and player.current:
        # Loop current song
        player.queue.appendleft(player.current)
    elif player.loop_queue and player.current:
        # Loop entire queue - add current to end
        player.queue.append(player.current)
    
    if not player.queue:
        player.current = None
        if not player._24_7:
            await player.vc.disconnect()
            players.pop(guild_id, None)
        await player.text_channel.send(get_text(guild_id, "queue_finished"))
        return
    
    # Get next song
    next_song = player.queue.popleft()
    player.current = next_song
    
    # Create audio source
    source = discord.FFmpegPCMAudio(next_song['url'], **FFMPEG_OPTIONS)
    source = discord.PCMVolumeTransformer(source, volume=player.volume)
    
    def after_playing(error):
        if error:
            print(f"Playback error: {error}")
        asyncio.run_coroutine_threadsafe(
            play_next(ctx, guild_id), 
            bot.loop
        )
    
    player.vc.play(source, after=after_playing)
    
    # Send now playing message
    duration_str = format_duration(next_song['duration'])
    await player.text_channel.send(
        f"🎵 **Now Playing:** `{next_song['title']}` ({duration_str}) | Source: {next_song['source']}"
    )
    
    # Add reaction controls
    try:
        msg = await player.text_channel.send("_ _")
        await msg.add_reaction("⏯️")  # Play/Pause
        await msg.add_reaction("⏭️")  # Skip
        await msg.add_reaction("⏹️")  # Stop
        await msg.add_reaction("🔊")  # Volume up
        await msg.add_reaction("🔉")  # Volume down
    except:
        pass

def format_duration(seconds):
    if not seconds:
        return "Live"
    minutes = seconds // 60
    seconds = seconds % 60
    hours = minutes // 60
    minutes = minutes % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

# ==================== BOT SETUP ====================

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=self.get_prefix, intents=intents, help_command=None)
    
    async def get_prefix(self, message):
        if not message.guild:
            return "!"
        return await db.get_prefix(message.guild.id)
    
    async def setup_hook(self):
        print(f"✅ Bot is ready!")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.reactions = True

bot = MusicBot()

# ==================== EVENTS ====================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ONLINE!")
    print(f"✅ Connected to {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!help"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Handle custom prefix
    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.invoke(ctx)
    else:
        # Check for song requests in any channel (if enabled)
        # This is where you'd implement song request system
        pass

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    # Handle reaction controls
    if reaction.message.author == bot.user and reaction.message.channel.id in [p.text_channel.id for p in players.values() if p.text_channel]:
        # Find which guild this is for
        for guild_id, player in players.items():
            if player.text_channel and player.text_channel.id == reaction.message.channel.id:
                if reaction.emoji == "⏯️":
                    # Toggle pause/play
                    if player.vc and player.vc.is_playing():
                        player.vc.pause()
                        await reaction.message.channel.send("⏸️ Paused")
                    elif player.vc and player.vc.is_paused():
                        player.vc.resume()
                        await reaction.message.channel.send("▶️ Resumed")
                elif reaction.emoji == "⏭️":
                    # Skip
                    if player.vc and player.vc.is_playing():
                        player.vc.stop()
                        await reaction.message.channel.send("⏭️ Skipped")
                elif reaction.emoji == "⏹️":
                    # Stop
                    if player.vc:
                        player.queue.clear()
                        player.vc.stop()
                        await reaction.message.channel.send("⏹️ Stopped")
                elif reaction.emoji == "🔊":
                    # Volume up
                    if player.vc and player.vc.source:
                        player.volume = min(1.0, player.volume + 0.1)
                        player.vc.source.volume = player.volume
                        await reaction.message.channel.send(f"🔊 Volume: {int(player.volume * 100)}%")
                elif reaction.emoji == "🔉":
                    # Volume down
                    if player.vc and player.vc.source:
                        player.volume = max(0.1, player.volume - 0.1)
                        player.vc.source.volume = player.volume
                        await reaction.message.channel.send(f"🔉 Volume: {int(player.volume * 100)}%")
                break

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user:
        # Bot moved or disconnected
        if not after.channel:
            # Bot disconnected
            if member.guild.id in players:
                player = players[member.guild.id]
                if player._24_7:
                    # Reconnect if 24/7 mode is enabled
                    await asyncio.sleep(5)
                    if member.guild.id in players:  # Check if still needed
                        try:
                            if player.text_channel and player.text_channel.guild.voice_client is None:
                                vc = await player.text_channel.guild.get_channel(member.guild.id).connect()
                                player.vc = vc
                        except:
                            pass
                else:
                    players.pop(member.guild.id, None)

# ==================== COMMANDS ====================

@bot.command(name='help')
async def help_command(ctx):
    """Show all commands"""
    prefix = await db.get_prefix(ctx.guild.id)
    
    embed = discord.Embed(
        title="🎵 Music Bot Commands",
        description=f"**Prefix:** `{prefix}`\n**Supported:** YouTube, Spotify, SoundCloud, Deezer, Twitch, Apple Music, Bandcamp, Radio",
        color=0x00ff00
    )
    
    embed.add_field(name="**🎵 Music**", 
                   value=f"`{prefix}play [song/url]` - Play music\n`{prefix}np` - Now playing\n`{prefix}queue` - Show queue\n`{prefix}pause` - Pause\n`{prefix}resume` - Resume\n`{prefix}skip` - Skip\n`{prefix}skipto [pos]` - Skip to position\n`{prefix}stop` - Stop & clear\n`{prefix}volume [0-100]` - Volume", 
                   inline=False)
    
    embed.add_field(name="**🔄 Loop**", 
                   value=f"`{prefix}loop` - Toggle loop current\n`{prefix}loopall` - Toggle loop queue\n`{prefix}repeat` - Alias for loop\n`{prefix}repeatall` - Alias for loopall", 
                   inline=False)
    
    embed.add_field(name="**📋 Playlist**", 
                   value=f"`{prefix}playlist create [name]` - Create playlist\n`{prefix}playlist add [name] [url]` - Add song\n`{prefix}playlist list` - Your playlists\n`{prefix}playlist load [name]` - Load playlist\n`{prefix}playlist delete [name]` - Delete playlist", 
                   inline=False)
    
    embed.add_field(name="**⚙️ Settings**", 
                   value=f"`{prefix}setprefix [new]` - Change prefix (Admin)\n`{prefix}setlang [en/es]` - Change language (Admin)\n`{prefix}247` - 24/7 mode (Premium)\n`{prefix}setup` - Premium setup", 
                   inline=False)
    
    embed.add_field(name="**🔊 Filters**", 
                   value=f"`{prefix}filter [name]` - Apply audio filter (Premium)\n`{prefix}filters` - List available filters", 
                   inline=False)
    
    embed.add_field(name="**🔄 Other**", 
                   value=f"`{prefix}shuffle` - Shuffle queue\n`{prefix}clear` - Clear queue\n`{prefix}remove [pos]` - Remove song\n`{prefix}leave` - Disconnect\n`{prefix}ping` - Latency\n`{prefix}help` - This menu", 
                   inline=False)
    
    embed.set_footer(text="React to now playing messages for controls! ⏯️⏭️⏹️🔊🔉")
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    """Check bot latency"""
    await ctx.send(f"Pong! 🏓 `{round(bot.latency * 1000)}ms`")

@bot.command(name='play', aliases=['p', 'pplay'])
async def play(ctx, *, query):
    """Play music from any source"""
    # Check voice
    if not ctx.author.voice:
        await ctx.send(get_text(ctx.guild.id, "no_voice"))
        return
    
    # Connect to voice
    try:
        if ctx.voice_client is None:
            vc = await ctx.author.voice.channel.connect()
            await ctx.send(get_text(ctx.guild.id, "joined", channel=ctx.author.voice.channel.name))
        else:
            vc = ctx.voice_client
            if vc.channel != ctx.author.voice.channel:
                await vc.move_to(ctx.author.voice.channel)
                await ctx.send(get_text(ctx.guild.id, "moved", channel=ctx.author.voice.channel.name))
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)[:50]}")
        return
    
    # Get or create player
    if ctx.guild.id not in players:
        players[ctx.guild.id] = MusicPlayer(ctx.guild.id)
    
    player = players[ctx.guild.id]
    player.vc = ctx.voice_client
    player.text_channel = ctx.channel
    
    await ctx.send(get_text(ctx.guild.id, "searching", query=query))
    
    # Extract audio
    audio_url, title, duration, source = await asyncio.get_event_loop().run_in_executor(
        None, extract_audio, query
    )
    
    if not audio_url or not title:
        await ctx.send(get_text(ctx.guild.id, "not_found"))
        return
    
    duration_str = format_duration(duration)
    
    # Create song object
    song = {
        'url': audio_url,
        'title': title,
        'duration': duration,
        'source': source,
        'requester': ctx.author.name
    }
    
    # Add to queue
    player.queue.append(song)
    await ctx.send(get_text(ctx.guild.id, "added", title=title, duration=duration_str))
    
    # Start playing if not playing
    if not ctx.voice_client.is_playing():
        await play_next(ctx, ctx.guild.id)

@bot.command(name='np', aliases=['nowplaying', 'now'])
async def nowplaying(ctx):
    """Show current song"""
    player = players.get(ctx.guild.id)
    if player and player.current:
        song = player.current
        duration_str = format_duration(song['duration'])
        await ctx.send(get_text(ctx.guild.id, "now_playing", title=song['title']) + f" ({duration_str}) | Source: {song['source']}")
    else:
        await ctx.send(get_text(ctx.guild.id, "nothing_playing"))

@bot.command(name='queue', aliases=['q'])
async def queue(ctx):
    """Show queue"""
    player = players.get(ctx.guild.id)
    
    embed = discord.Embed(title="📋 Music Queue", color=0x00ff00)
    
    # Now playing
    if player and player.current:
        current = player.current
        duration_str = format_duration(current['duration'])
        embed.add_field(name="**Now Playing:**", 
                       value=f"`{current['title'][:50]}` ({duration_str}) | {current['source']}", 
                       inline=False)
    else:
        embed.add_field(name="**Now Playing:**", value="Nothing", inline=False)
    
    # Up next
    if player and player.queue:
        queue_list = list(player.queue)
        queue_text = ""
        total_duration = 0
        
        for i, song in enumerate(queue_list[:10]):
            duration_str = format_duration(song['duration'])
            queue_text += f"`{i+1}.` `{song['title'][:40]}` ({duration_str})\n"
            total_duration += song['duration'] or 0
        
        if len(queue_list) > 10:
            queue_text += f"\n`... and {len(queue_list) - 10} more songs`"
        
        # Calculate total time
        if total_duration:
            hours = total_duration // 3600
            minutes = (total_duration % 3600) // 60
            if hours > 0:
                time_left = f"{hours}h {minutes}m"
            else:
                time_left = f"{minutes}m"
            embed.set_footer(text=f"{len(queue_list)} songs • {time_left} total")
        
        embed.add_field(name="**Up Next:**", value=queue_text, inline=False)
    else:
        embed.add_field(name="**Up Next:**", value=get_text(ctx.guild.id, "queue_empty"), inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='pause', aliases=['pa'])
async def pause(ctx):
    """Pause current song"""
    player = players.get(ctx.guild.id)
    if player and player.vc and player.vc.is_playing():
        player.vc.pause()
        await ctx.send(get_text(ctx.guild.id, "paused"))
    else:
        await ctx.send(get_text(ctx.guild.id, "nothing_playing"))

@bot.command(name='resume', aliases=['r'])
async def resume(ctx):
    """Resume paused song"""
    player = players.get(ctx.guild.id)
    if player and player.vc and player.vc.is_paused():
        player.vc.resume()
        await ctx.send(get_text(ctx.guild.id, "resumed"))
    else:
        await ctx.send(get_text(ctx.guild.id, "nothing_paused"))

@bot.command(name='skip', aliases=['s'])
async def skip(ctx):
    """Skip current song"""
    player = players.get(ctx.guild.id)
    if player and player.vc and player.vc.is_playing():
        player.vc.stop()
        await ctx.send(get_text(ctx.guild.id, "skipped"))
    else:
        await ctx.send(get_text(ctx.guild.id, "nothing_to_skip"))

@bot.command(name='skipto', aliases=['st'])
async def skipto(ctx, position: int):
    """Skip to position in queue"""
    player = players.get(ctx.guild.id)
    if not player or not player.queue:
        await ctx.send(get_text(ctx.guild.id, "queue_empty"))
        return
    
    if position < 1 or position > len(player.queue):
        await ctx.send(get_text(ctx.guild.id, "invalid_position"))
        return
    
    # Remove songs before position
    for _ in range(position - 1):
        if player.queue:
            player.queue.popleft()
    
    # Skip current
    if player.vc and player.vc.is_playing():
        player.vc.stop()
    
    await ctx.send(f"⏭️ Skipped to position **{position}**")

@bot.command(name='stop')
async def stop(ctx):
    """Stop playing and clear queue"""
    player = players.get(ctx.guild.id)
    if player and player.vc:
        player.queue.clear()
        player.vc.stop()
        await ctx.send(get_text(ctx.guild.id, "stopped"))
    else:
        await ctx.send(get_text(ctx.guild.id, "not_in_voice"))

@bot.command(name='loop', aliases=['repeat'])
async def loop(ctx, mode=None):
    """Toggle loop mode"""
    player = players.get(ctx.guild.id)
    if not player:
        return
    
    if mode == "current" or mode is None:
        player.loop = not player.loop
        player.loop_queue = False
        await ctx.send(f"🔄 Loop current: **{'ON' if player.loop else 'OFF'}**")
    elif mode == "all":
        player.loop_queue = not player.loop_queue
        player.loop = False
        await ctx.send(f"🔄 Loop queue: **{'ON' if player.loop_queue else 'OFF'}**")

@bot.command(name='loopall', aliases=['la', 'loopqueue', 'repeatall'])
async def loopall(ctx):
    """Toggle loop queue"""
    player = players.get(ctx.guild.id)
    if not player:
        return
    
    player.loop_queue = not player.loop_queue
    player.loop = False
    await ctx.send(f"🔄 Loop queue: **{'ON' if player.loop_queue else 'OFF'}**")

@bot.command(name='shuffle', aliases=['mix'])
async def shuffle(ctx):
    """Shuffle queue"""
    player = players.get(ctx.guild.id)
    if player and len(player.queue) > 1:
        queue_list = list(player.queue)
        random.shuffle(queue_list)
        player.queue = deque(queue_list)
        await ctx.send(get_text(ctx.guild.id, "shuffled"))
    else:
        await ctx.send(get_text(ctx.guild.id, "not_enough"))

@bot.command(name='volume', aliases=['vol', 'v'])
async def volume(ctx, vol: int):
    """Set volume (0-100)"""
    if vol < 0 or vol > 100:
        await ctx.send(get_text(ctx.guild.id, "invalid_volume"))
        return
    
    player = players.get(ctx.guild.id)
    if player and player.vc and player.vc.source:
        player.volume = vol / 100
        player.vc.source.volume = player.volume
        await ctx.send(get_text(ctx.guild.id, "volume_set", vol=vol))
    else:
        await ctx.send(get_text(ctx.guild.id, "nothing_playing"))

@bot.command(name='clear')
async def clear(ctx):
    """Clear queue"""
    player = players.get(ctx.guild.id)
    if player:
        player.queue.clear()
        await ctx.send("🗑️ **Queue cleared**")
    else:
        await ctx.send(get_text(ctx.guild.id, "queue_empty"))

@bot.command(name='remove')
async def remove(ctx, position: int):
    """Remove song at position"""
    player = players.get(ctx.guild.id)
    if not player or not player.queue:
        await ctx.send(get_text(ctx.guild.id, "queue_empty"))
        return
    
    if position < 1 or position > len(player.queue):
        await ctx.send(get_text(ctx.guild.id, "invalid_position"))
        return
    
    queue_list = list(player.queue)
    removed = queue_list.pop(position - 1)
    player.queue = deque(queue_list)
    
    await ctx.send(get_text(ctx.guild.id, "removed", title=removed['title'][:50]))

@bot.command(name='leave', aliases=['dc', 'disconnect'])
async def leave(ctx):
    """Leave voice channel"""
    player = players.get(ctx.guild.id)
    if player and player.vc:
        player.queue.clear()
        await player.vc.disconnect()
        players.pop(ctx.guild.id, None)
        await ctx.send(get_text(ctx.guild.id, "disconnected"))
    else:
        await ctx.send(get_text(ctx.guild.id, "not_in_voice"))

# ==================== PLAYLIST SYSTEM ====================

@bot.group(name='playlist', invoke_without_command=True)
async def playlist(ctx):
    """Playlist management"""
    await ctx.send("📋 **Playlist Commands:**\n"
                   "`!playlist create [name]` - Create playlist\n"
                   "`!playlist add [name] [url]` - Add song\n"
                   "`!playlist list` - Your playlists\n"
                   "`!playlist load [name]` - Load playlist\n"
                   "`!playlist delete [name]` - Delete playlist")

@playlist.command(name='create')
async def pl_create(ctx, *, name):
    """Create a playlist"""
    await db.create_playlist(ctx.author.id, name)
    await ctx.send(get_text(ctx.guild.id, "playlist_created", name=name))

@playlist.command(name='add')
async def pl_add(ctx, name, *, url):
    """Add song to playlist"""
    await db.add_to_playlist(ctx.author.id, name, url)
    await ctx.send(get_text(ctx.guild.id, "playlist_added", name=name))

@playlist.command(name='list')
async def pl_list(ctx):
    """List your playlists"""
    playlists = await db.get_all_playlists(ctx.author.id)
    if playlists:
        await ctx.send(get_text(ctx.guild.id, "playlists_list", list=", ".join(playlists)))
    else:
        await ctx.send(get_text(ctx.guild.id, "no_playlists"))

@playlist.command(name='load')
async def pl_load(ctx, *, name):
    """Load a playlist into queue"""
    playlist = await db.get_playlist(ctx.author.id, name)
    if not playlist:
        await ctx.send(get_text(ctx.guild.id, "not_found"))
        return
    
    if not ctx.author.voice:
        await ctx.send(get_text(ctx.guild.id, "no_voice"))
        return
    
    # Connect to voice if not connected
    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()
    
    # Get or create player
    if ctx.guild.id not in players:
        players[ctx.guild.id] = MusicPlayer(ctx.guild.id)
    
    player = players[ctx.guild.id]
    player.vc = ctx.voice_client
    player.text_channel = ctx.channel
    
    await ctx.send(f"🔄 Loading playlist **{name}**...")
    
    # Add each song
    added = 0
    for url in playlist:
        audio_url, title, duration, source = await asyncio.get_event_loop().run_in_executor(
            None, extract_audio, url
        )
        
        if audio_url and title:
            song = {
                'url': audio_url,
                'title': title,
                'duration': duration,
                'source': source,
                'requester': ctx.author.name
            }
            player.queue.append(song)
            added += 1
    
    await ctx.send(get_text(ctx.guild.id, "playlist_loaded", name=name) + f" ({added} songs)")
    
    # Start playing
    if not ctx.voice_client.is_playing():
        await play_next(ctx, ctx.guild.id)

@playlist.command(name='delete')
async def pl_delete(ctx, *, name):
    """Delete a playlist"""
    await db.delete_playlist(ctx.author.id, name)
    await ctx.send(get_text(ctx.guild.id, "playlist_deleted", name=name))

# ==================== SETTINGS & PREMIUM ====================

@bot.command(name='setprefix')
@commands.has_permissions(administrator=True)
async def setprefix(ctx, new_prefix):
    """Change server prefix"""
    await db.set_prefix(ctx.guild.id, new_prefix)
    await ctx.send(get_text(ctx.guild.id, "prefix_changed", prefix=new_prefix))

@bot.command(name='setlang')
@commands.has_permissions(administrator=True)
async def setlang(ctx, lang):
    """Change server language (en/es)"""
    if lang in ['en', 'es']:
        await db.set_lang(ctx.guild.id, lang)
        await ctx.send(get_text(ctx.guild.id, "language_changed", lang=lang))
    else:
        await ctx.send("❌ Supported languages: `en`, `es`")

@bot.command(name='247')
async def stay_247(ctx):
    """Enable/disable 24/7 mode (Premium)"""
    if not await db.is_premium(ctx.guild.id):
        await ctx.send(get_text(ctx.guild.id, "premium_only"))
        return
    
    player = players.get(ctx.guild.id)
    if player:
        player._24_7 = not player._24_7
        status = "enabled" if player._24_7 else "disabled"
        await ctx.send(get_text(ctx.guild.id, f"247_{status}"))
    else:
        # Create player even if not playing
        players[ctx.guild.id] = MusicPlayer(ctx.guild.id)
        players[ctx.guild.id]._24_7 = True
        players[ctx.guild.id].text_channel = ctx.channel
        await ctx.send(get_text(ctx.guild.id, "247_enabled"))

@bot.command(name='setup')
async def setup(ctx):
    """Premium setup command"""
    if not await db.is_premium(ctx.guild.id):
        await ctx.send(get_text(ctx.guild.id, "premium_only"))
        return
    
    # This would be where you configure premium features
    await ctx.send(get_text(ctx.guild.id, "setup_complete"))

@bot.command(name='premium')
@commands.is_owner()
async def premium(ctx, guild_id: int, status: bool):
    """Owner-only: Set premium status"""
    await db.set_premium(guild_id, status)
    await ctx.send(f"✅ Premium set to **{status}** for guild `{guild_id}`")

@bot.command(name='filter')
async def filter_cmd(ctx, filter_name=None):
    """Apply audio filters (Premium)"""
    if not await db.is_premium(ctx.guild.id):
        await ctx.send(get_text(ctx.guild.id, "premium_only"))
        return
    
    player = players.get(ctx.guild.id)
    if not player or not player.vc:
        await ctx.send(get_text(ctx.guild.id, "nothing_playing"))
        return
    
    filters = {
        'bass': 'bass=g=10',
        'treble': 'treble=g=10',
        'normalizer': 'dynaudnorm',
        'vaporwave': 'asetrate=44100*0.8,aresample=44100,atempo=1.25',
        'nightcore': 'asetrate=44100*1.25,aresample=44100,atempo=1.0',
        'slow': 'atempo=0.8',
        'fast': 'atempo=1.5',
        'echo': 'aecho=0.8:0.9:1000:0.3',
        'reverb': 'aecho=0.8:0.88:60:0.4',
        'off': None
    }
    
    if filter_name == 'off':
        player.filter = None
        await ctx.send("✅ Filters disabled")
    elif filter_name in filters:
        player.filter = filters[filter_name]
        await ctx.send(f"✅ Filter **{filter_name}** applied")
    else:
        await ctx.send(f"Available filters: {', '.join(filters.keys())}")

@bot.command(name='filters')
async def filters_list(ctx):
    """List available filters"""
    await ctx.send("🎛️ **Available Filters:**\n"
                   "`bass` - Boost bass\n"
                   "`treble` - Boost treble\n"
                   "`normalizer` - Normalize volume\n"
                   "`vaporwave` - Vaporwave effect\n"
                   "`nightcore` - Nightcore effect\n"
                   "`slow` - Slow down\n"
                   "`fast` - Speed up\n"
                   "`echo` - Add echo\n"
                   "`reverb` - Add reverb\n"
                   "`off` - Disable filters")

# ==================== START BOT ====================

keep_alive()

if __name__ == "__main__":
    print("🔄 Starting Ultimate Music Bot...")
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"❌ Error: {e}")
