import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from flask import Flask
from threading import Thread
import random
from collections import deque

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

# ==================== SIMPLE DATABASE (in‑memory) ====================
class Database:
    def __init__(self):
        self.prefixes = {}
        self.languages = {}
        self.premium = {}
        self.playlists = {}
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

# ==================== MULTI‑LANGUAGE ====================
translations = {
    "en": {
        "no_voice": "❌ You need to be in a **voice channel** first!",
        "joined": "✅ Joined **{channel}**",
        "moved": "✅ Moved to **{channel}**",
        "searching": "🔍 **Finding:** `{query}`",
        "not_found": "❌ **Could not find that song. Try a different search or a direct YouTube link.**",
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
        "playlist_created": "✅ ¡Lista **{name}** creada!",
        "playlist_deleted": "✅ ¡Lista **{name}** eliminada!",
        "playlist_added": "✅ Añadido a la lista **{name}**",
        "playlist_loaded": "✅ Lista **{name}** cargada en la cola",
        "no_playlists": "📭 No tienes listas",
        "playlists_list": "📋 Tus listas: {list}",
        "prefix_changed": "✅ Prefijo cambiado a `{prefix}`",
        "language_changed": "✅ Idioma cambiado a **{lang}**",
        "247_enabled": "✅ Modo 24/7 activado",
        "247_disabled": "✅ Modo 24/7 desactivado",
        "setup_complete": "✅ Configuración Premium completada",
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

# ==================== IMPROVED YT‑DLP ====================
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
]

BASE_YTDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'nocheckcertificate': True,
    'extract_flat': False,
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': {
            'skip': ['dash', 'hls', 'webpage'],
        }
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

def extract_audio(query):
    strategies = [
        lambda q: _extract_with_opts(q, {'user_agent': random.choice(USER_AGENTS)}),
        lambda q: _extract_with_opts(q, {'extractor_args': {'youtube': {'player_client': ['android']}}}),
        lambda q: _extract_with_opts(q, {'format': 'bestaudio[ext=m4a]'}),
        lambda q: _extract_with_opts(q, {'force_generic_extractor': True}),
    ]
    for strat in strategies:
        try:
            result = strat(query)
            if result and result[0]:
                return result
        except Exception as e:
            print(f"Strategy failed: {e}")
            continue
    return None, None, None, None

def _extract_with_opts(query, extra_opts):
    opts = BASE_YTDL_OPTS.copy()
    opts.update(extra_opts)
    ydl = yt_dlp.YoutubeDL(opts)

    if not query.startswith(('http://', 'https://')):
        search_query = f"ytsearch3:{query}"
        info = ydl.extract_info(search_query, download=False)
        if info and 'entries' in info:
            for entry in info['entries']:
                if entry:
                    url, title, dur, src = _extract_from_info(entry)
                    if url:
                        return url, title, dur, src
        return None, None, None, None
    else:
        info = ydl.extract_info(query, download=False)
        return _extract_from_info(info)

def _extract_from_info(info):
    if not info:
        return None, None, None, None
    audio_url = info.get('url')
    if not audio_url and 'formats' in info:
        for f in info['formats']:
            if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                audio_url = f.get('url')
                break
    title = info.get('title', 'Unknown')
    duration = info.get('duration', 0)
    webpage_url = info.get('webpage_url', '')
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

async def play_next(ctx, guild_id):
    player = players.get(guild_id)
    if not player or not player.vc:
        return
    if player.loop and player.current:
        player.queue.appendleft(player.current)
    elif player.loop_queue and player.current:
        player.queue.append(player.current)
    if not player.queue:
        player.current = None
        if not player._24_7:
            await player.vc.disconnect()
            players.pop(guild_id, None)
        await player.text_channel.send(get_text(guild_id, "queue_finished"))
        return
    next_song = player.queue.popleft()
    player.current = next_song
    source = discord.FFmpegPCMAudio(next_song['url'], **FFMPEG_OPTIONS)
    source = discord.PCMVolumeTransformer(source, volume=player.volume)
    def after_playing(error):
        if error:
            print(f"Playback error: {error}")
        asyncio.run_coroutine_threadsafe(play_next(ctx, guild_id), bot.loop)
    player.vc.play(source, after=after_playing)
    duration_str = format_duration(next_song['duration'])
    await player.text_channel.send(
        f"🎵 **Now Playing:** `{next_song['title']}` ({duration_str}) | Source: {next_song['source']}"
    )
    # Reaction controls
    try:
        msg = await player.text_channel.send("_ _")
        for emoji in ["⏯️", "⏭️", "⏹️", "🔊", "🔉"]:
            await msg.add_reaction(emoji)
    except:
        pass

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
    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.invoke(ctx)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    # Find which guild this reaction belongs to
    for guild_id, player in players.items():
        if player.text_channel and player.text_channel.id == reaction.message.channel.id:
            if reaction.emoji == "⏯️":
                if player.vc and player.vc.is_playing():
                    player.vc.pause()
                    await reaction.message.channel.send("⏸️ Paused")
                elif player.vc and player.vc.is_paused():
                    player.vc.resume()
                    await reaction.message.channel.send("▶️ Resumed")
            elif reaction.emoji == "⏭️":
                if player.vc and player.vc.is_playing():
                    player.vc.stop()
                    await reaction.message.channel.send("⏭️ Skipped")
            elif reaction.emoji == "⏹️":
                if player.vc:
                    player.queue.clear()
                    player.vc.stop()
                    await reaction.message.channel.send("⏹️ Stopped")
            elif reaction.emoji == "🔊":
                if player.vc and player.vc.source:
                    player.volume = min(1.0, player.volume + 0.1)
                    player.vc.source.volume = player.volume
                    await reaction.message.channel.send(f"🔊 Volume: {int(player.volume*100)}%")
            elif reaction.emoji == "🔉":
                if player.vc and player.vc.source:
                    player.volume = max(0.1, player.volume - 0.1)
                    player.vc.source.volume = player.volume
                    await reaction.message.channel.send(f"🔉 Volume: {int(player.volume*100)}%")
            break

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and not after.channel:
        if member.guild.id in players:
            player = players[member.guild.id]
            if player._24_7:
                await asyncio.sleep(5)
                if member.guild.id in players:
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
    await ctx.send(f"Pong! 🏓 `{round(bot.latency * 1000)}ms`")

@bot.command(name='play', aliases=['p', 'pplay'])
async def play(ctx, *, query):
    if not ctx.author.voice:
        await ctx.send(get_text(ctx.guild.id, "no_voice"))
        return
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
    if ctx.guild.id not in players:
        players[ctx.guild.id] = MusicPlayer(ctx.guild.id)
    player = players[ctx.guild.id]
    player.vc = ctx.voice_client
    player.text_channel = ctx.channel
    await ctx.send(get_text(ctx.guild.id, "searching", query=query))
    audio_url, title, duration, source = None, None, None, None
    for attempt in range(3):
        audio_url, title, duration, source = await asyncio.get_event_loop().run_in_executor(
            None, extract_audio, query
        )
        if audio_url:
            break
        await asyncio.sleep(1)
    if not audio_url:
        await ctx.send(get_text(ctx.guild.id, "not_found"))
        return
    duration_str = format_duration(duration)
    song = {
        'url': audio_url,
        'title': title,
        'duration': duration,
        'source': source,
        'requester': ctx.author.name
    }
    player.queue.append(song)
    await ctx.send(get_text(ctx.guild.id, "added", title=title, duration=duration_str))
    if not ctx.voice_client.is_playing():
        await play_next(ctx, ctx.guild.id)

@bot.command(name='pause', aliases=['pa'])
async def pause(ctx):
    player = players.get(ctx.guild.id)
    if player and player.vc and player.vc.is_playing():
        player.vc.pause()
        await ctx.send(get_text(ctx.guild.id, "paused"))
    else:
        await ctx.send(get_text(ctx.guild.id, "nothing_playing"))

@bot.command(name='resume', aliases=['r'])
async def resume(ctx):
    player = players.get(ctx.guild.id)
    if player and player.vc and player.vc.is_paused():
        player.vc.resume()
        await ctx.send(get_text(ctx.guild.id, "resumed"))
    else:
        await ctx.send(get_text(ctx.guild.id, "nothing_paused"))

@bot.command(name='skip', aliases=['s'])
async def skip(ctx):
    player = players.get(ctx.guild.id)
    if player and player.vc and player.vc.is_playing():
        player.vc.stop()
        await ctx.send(get_text(ctx.guild.id, "skipped"))
    else:
        await ctx.send(get_text(ctx.guild.id, "nothing_to_skip"))

@bot.command(name='skipto', aliases=['st'])
async def skipto(ctx, position: int):
    player = players.get(ctx.guild.id)
    if not player or not player.queue:
        await ctx.send(get_text(ctx.guild.id, "queue_empty"))
        return
    if position < 1 or position > len(player.queue):
        await ctx.send(get_text(ctx.guild.id, "invalid_position"))
        return
    for _ in range(position - 1):
        if player.queue:
            player.queue.popleft()
    if player.vc and player.vc.is_playing():
        player.vc.stop()
    await ctx.send(f"⏭️ Skipped to position **{position}**")

@bot.command(name='stop')
async def stop(ctx):
    player = players.get(ctx.guild.id)
    if player and player.vc:
        player.queue.clear()
        player.vc.stop()
        await ctx.send(get_text(ctx.guild.id, "stopped"))
    else:
        await ctx.send(get_text(ctx.guild.id, "not_in_voice"))

@bot.command(name='loop', aliases=['repeat'])
async def loop(ctx, mode=None):
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
    player = players.get(ctx.guild.id)
    if not player:
        return
    player.loop_queue = not player.loop_queue
    player.loop = False
    await ctx.send(f"🔄 Loop queue: **{'ON' if player.loop_queue else 'OFF'}**")

@bot.command(name='shuffle', aliases=['mix'])
async def shuffle(ctx):
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
    player = players.get(ctx.guild.id)
    if player:
        player.queue.clear()
        await ctx.send("🗑️ **Queue cleared**")
    else:
        await ctx.send(get_text(ctx.guild.id, "queue_empty"))

@bot.command(name='remove')
async def remove(ctx, position: int):
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
    player = players.get(ctx.guild.id)
    if player and player.vc:
        player.queue.clear()
        await player.vc.disconnect()
        players.pop(ctx.guild.id, None)
        await ctx.send(get_text(ctx.guild.id, "disconnected"))
    else:
        await ctx.send(get_text(ctx.guild.id, "not_in_voice"))

# ==================== PLAYLIST COMMANDS ====================
@bot.group(name='playlist', invoke_without_command=True)
async def playlist(ctx):
    await ctx.send("📋 **Playlist Commands:**\n"
                   "`!playlist create [name]` - Create playlist\n"
                   "`!playlist add [name] [url]` - Add song\n"
                   "`!playlist list` - Your playlists\n"
                   "`!playlist load [name]` - Load playlist\n"
                   "`!playlist delete [name]` - Delete playlist")

@playlist.command(name='create')
async def pl_create(ctx, *, name):
    await db.create_playlist(ctx.author.id, name)
    await ctx.send(get_text(ctx.guild.id, "playlist_created", name=name))

@playlist.command(name='add')
async def pl_add(ctx, name, *, url):
    await db.add_to_playlist(ctx.author.id, name, url)
    await ctx.send(get_text(ctx.guild.id, "playlist_added", name=name))

@playlist.command(name='list')
async def pl_list(ctx):
    playlists = await db.get_all_playlists(ctx.author.id)
    if playlists:
        await ctx.send(get_text(ctx.guild.id, "playlists_list", list=", ".join(playlists)))
    else:
        await ctx.send(get_text(ctx.guild.id, "no_playlists"))

@playlist.command(name='load')
async def pl_load(ctx, *, name):
    playlist = await db.get_playlist(ctx.author.id, name)
    if not playlist:
        await ctx.send(get_text(ctx.guild.id, "not_found"))
        return
    if not ctx.author.voice:
        await ctx.send(get_text(ctx.guild.id, "no_voice"))
        return
    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()
    if ctx.guild.id not in players:
        players[ctx.guild.id] = MusicPlayer(ctx.guild.id)
    player = players[ctx.guild.id]
    player.vc = ctx.voice_client
    player.text_channel = ctx.channel
    await ctx.send(f"🔄 Loading playlist **{name}**...")
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
    if not ctx.voice_client.is_playing():
        await play_next(ctx, ctx.guild.id)

@playlist.command(name='delete')
async def pl_delete(ctx, *, name):
    await db.delete_playlist(ctx.author.id, name)
    await ctx.send(get_text(ctx.guild.id, "playlist_deleted", name=name))

# ==================== SETTINGS & PREMIUM ====================
@bot.command(name='setprefix')
@commands.has_permissions(administrator=True)
async def setprefix(ctx, new_prefix):
    await db.set_prefix(ctx.guild.id, new_prefix)
    await ctx.send(get_text(ctx.guild.id, "prefix_changed", prefix=new_prefix))

@bot.command(name='setlang')
@commands.has_permissions(administrator=True)
async def setlang(ctx, lang):
    if lang in ['en', 'es']:
        await db.set_lang(ctx.guild.id, lang)
        await ctx.send(get_text(ctx.guild.id, "language_changed", lang=lang))
    else:
        await ctx.send("❌ Supported languages: `en`, `es`")

@bot.command(name='247')
async def stay_247(ctx):
    if not await db.is_premium(ctx.guild.id):
        await ctx.send(get_text(ctx.guild.id, "premium_only"))
        return
    player = players.get(ctx.guild.id)
    if player:
        player._24_7 = not player._24_7
        status = "enabled" if player._24_7 else "disabled"
        await ctx.send(get_text(ctx.guild.id, f"247_{status}"))
    else:
        players[ctx.guild.id] = MusicPlayer(ctx.guild.id)
        players[ctx.guild.id]._24_7 = True
        players[ctx.guild.id].text_channel = ctx.channel
        await ctx.send(get_text(ctx.guild.id, "247_enabled"))

@bot.command(name='setup')
async def setup(ctx):
    if not await db.is_premium(ctx.guild.id):
        await ctx.send(get_text(ctx.guild.id, "premium_only"))
        return
    await ctx.send(get_text(ctx.guild.id, "setup_complete"))

@bot.command(name='premium')
@commands.is_owner()
async def premium(ctx, guild_id: int, status: bool):
    await db.set_premium(guild_id, status)
    await ctx.send(f"✅ Premium set to **{status}** for guild `{guild_id}`")

@bot.command(name='filter')
async def filter_cmd(ctx, filter_name=None):
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

# ==================== START ====================
keep_alive()

if __name__ == "__main__":
    print("🔄 Starting Ultimate Music Bot...")
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"❌ Error: {e}")
