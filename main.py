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

# ==================== DATABASE SIMULATION ====================
class Database:
    def __init__(self):
        self.prefixes = {}
        self.languages = {}
        self.premium = {}
        self.playlists = {}
        self.settings = {}
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
        # ... (same as before, keep your existing translations)
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

# ==================== IMPROVED YT‑DLP CONFIGURATION ====================

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
    """
    Attempt to extract audio using multiple strategies.
    Returns (audio_url, title, duration, source) or (None, None, None, None)
    """
    # Strategies in order of preference
    strategies = [
        # 1. Normal search with random user agent
        lambda q: _extract_with_opts(q, {'user_agent': random.choice(USER_AGENTS)}),
        # 2. Force android client (often less blocked)
        lambda q: _extract_with_opts(q, {'extractor_args': {'youtube': {'player_client': ['android']}}}),
        # 3. Use different format extraction
        lambda q: _extract_with_opts(q, {'format': 'bestaudio[ext=m4a]'}),
        # 4. Generic extractor fallback
        lambda q: _extract_with_opts(q, {'force_generic_extractor': True}),
    ]

    for strat in strategies:
        try:
            result = strat(query)
            if result and result[0]:  # audio_url exists
                return result
        except Exception as e:
            print(f"Strategy failed: {e}")
            continue
    return None, None, None, None

def _extract_with_opts(query, extra_opts):
    """Helper to run extraction with given options."""
    opts = BASE_YTDL_OPTS.copy()
    opts.update(extra_opts)

    ydl = yt_dlp.YoutubeDL(opts)

    if not query.startswith(('http://', 'https://')):
        # Search – fetch top 3 results and try each until one yields a playable URL
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
        # Direct URL
        info = ydl.extract_info(query, download=False)
        return _extract_from_info(info)

def _extract_from_info(info):
    """Extract audio URL, title, duration, source from an info dict."""
    if not info:
        return None, None, None, None

    # Get audio URL
    audio_url = info.get('url')
    if not audio_url and 'formats' in info:
        # Prefer format with audio only
        for f in info['formats']:
            if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                audio_url = f.get('url')
                break

    title = info.get('title', 'Unknown')
    duration = info.get('duration', 0)
    webpage_url = info.get('webpage_url', '')

    # Identify source
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

    # Reaction controls (optional)
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
    # Reaction control handling (same as before) – keep your existing code
    # ... (omitted for brevity, but include your previous reaction logic)

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user:
        if not after.channel:
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
# (Keep all your existing command definitions: help, ping, play, pause, resume, skip, etc.)
# Only the `play` command is modified below to use the new extract_audio with retries.

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

    # Try up to 3 times with a short delay
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

# ... all other commands remain unchanged (keep them as in your last version)

# ==================== START BOT ====================
keep_alive()

if __name__ == "__main__":
    print("🔄 Starting Ultimate Music Bot...")
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"❌ Error: {e}")
