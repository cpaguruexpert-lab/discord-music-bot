import discord
from discord.ext import commands
import asyncio
import motor.motor_asyncio
from config import BOT_TOKEN, MONGO_URI, PREFIX
from web import keep_alive
import yt_dlp
import re
import random

# Database setup
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["music_bot"]

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.reactions = True

# Bot class
class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=self.get_prefix, intents=intents)
    
    async def get_prefix(self, message):
        if not message.guild:
            return PREFIX
        doc = await db.prefixes.find_one({"_id": message.guild.id})
        return doc["prefix"] if doc else PREFIX
    
    async def setup_hook(self):
        await self.add_cog(MusicCog(self))
        await self.add_cog(SettingsCog(self))
        print("Bot ready!")

bot = MusicBot()

# Music Player
players = {}

class MusicPlayer:
    def __init__(self, guild_id, voice_client):
        self.guild_id = guild_id
        self.vc = voice_client
        self.queue = asyncio.Queue()
        self.current = None
        self.loop = False
        self.volume = 0.5
        self.always_connected = False
    
    async def play_next(self):
        if self.loop and self.current:
            await self.queue.put(self.current)
        if self.queue.empty():
            self.vc.stop()
            self.current = None
            return
        self.current = await self.queue.get()
        ytdl_opts = {'format': 'bestaudio', 'quiet': True}
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            info = ydl.extract_info(self.current, download=False)
            url = info['url']
        source = discord.FFmpegPCMAudio(url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5')
        self.vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), bot.loop))

# Music Commands
class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def get_player(self, ctx):
        if ctx.guild.id not in players:
            if not ctx.voice_client:
                await ctx.author.voice.channel.connect()
            players[ctx.guild.id] = MusicPlayer(ctx.guild.id, ctx.voice_client)
        return players[ctx.guild.id]
    
    @commands.command(name="play", aliases=["p", "pplay"])
    async def play(self, ctx, *, query):
        if not ctx.author.voice:
            return await ctx.send("Join a voice channel first!")
        player = await self.get_player(ctx)
        await player.add_to_queue(query)
        await ctx.send(f"✅ Added to queue: **{query[:50]}**")
        if not player.vc.is_playing():
            await player.play_next()
    
    @commands.command(name="np", aliases=["nowplaying", "now"])
    async def nowplaying(self, ctx):
        player = players.get(ctx.guild.id)
        if not player or not player.current:
            await ctx.send("Nothing playing")
        else:
            await ctx.send(f"🎵 Now playing: **{player.current}**")
    
    @commands.command(name="queue")
    async def queue(self, ctx):
        player = players.get(ctx.guild.id)
        if not player or player.queue.empty():
            await ctx.send("Queue empty")
        else:
            qlist = list(player.queue._queue)
            text = "\n".join([f"{i+1}. {s}" for i,s in enumerate(qlist[:10])])
            await ctx.send(f"**Queue:**\n{text}")
    
    @commands.command(name="loop", aliases=["repeat"])
    async def loop(self, ctx):
        player = players.get(ctx.guild.id)
        if player:
            player.loop = not player.loop
            await ctx.send(f"Loop: {'ON' if player.loop else 'OFF'}")
    
    @commands.command(name="shuffle", aliases=["mix"])
    async def shuffle(self, ctx):
        player = players.get(ctx.guild.id)
        if player and not player.queue.empty():
            items = list(player.queue._queue)
            random.shuffle(items)
            player.queue._queue.clear()
            for i in items:
                await player.queue.put(i)
            await ctx.send("🔀 Queue shuffled")
    
    @commands.command(name="volume", aliases=["vol", "v"])
    async def volume(self, ctx, vol: int):
        if 0 <= vol <= 100:
            player = players.get(ctx.guild.id)
            if player:
                player.volume = vol/100
                await ctx.send(f"Volume: {vol}%")
    
    @commands.command(name="pause", aliases=["pa"])
    async def pause(self, ctx):
        player = players.get(ctx.guild.id)
        if player and player.vc.is_playing():
            player.vc.pause()
            await ctx.send("⏸️ Paused")
    
    @commands.command(name="resume", aliases=["r"])
    async def resume(self, ctx):
        player = players.get(ctx.guild.id)
        if player and player.vc.is_paused():
            player.vc.resume()
            await ctx.send("▶️ Resumed")
    
    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx):
        player = players.get(ctx.guild.id)
        if player:
            player.vc.stop()
            await ctx.send("⏭️ Skipped")
    
    @commands.command(name="247")
    async def stay_247(self, ctx):
        doc = await db.premium.find_one({"_id": ctx.guild.id})
        if not doc or not doc.get("active"):
            await ctx.send("Premium required for 24/7 mode")
            return
        player = players.get(ctx.guild.id)
        if player:
            player.always_connected = True
            await ctx.send("24/7 mode enabled")

# Settings Commands
class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="setprefix")
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx, new_prefix):
        await db.prefixes.update_one({"_id": ctx.guild.id}, {"$set": {"prefix": new_prefix}}, upsert=True)
        await ctx.send(f"Prefix changed to `{new_prefix}`")
    
    @commands.command(name="setlang")
    @commands.has_permissions(administrator=True)
    async def setlang(self, ctx, lang):
        if lang in ["en", "es"]:
            await db.languages.update_one({"_id": ctx.guild.id}, {"$set": {"lang": lang}}, upsert=True)
            await ctx.send(f"Language set to {lang}")
    
    @commands.command(name="premium")
    @commands.is_owner()
    async def premium(self, ctx, guild_id: int, active: bool):
        await db.premium.update_one({"_id": guild_id}, {"$set": {"active": active}}, upsert=True)
        await ctx.send(f"Premium set to {active} for {guild_id}")

# Playlist Commands
@bot.group(name="playlist", invoke_without_command=True)
async def playlist(self, ctx):
    await ctx.send("Commands: create, add, list, load, delete")

@playlist.command(name="create")
async def pl_create(self, ctx, name):
    await db.playlists.insert_one({"user": ctx.author.id, "name": name, "songs": []})
    await ctx.send(f"Playlist '{name}' created")

@playlist.command(name="add")
async def pl_add(self, ctx, name, url):
    await db.playlists.update_one({"user": ctx.author.id, "name": name}, {"$push": {"songs": url}})
    await ctx.send(f"Added to '{name}'")

@playlist.command(name="list")
async def pl_list(self, ctx):
    playlists = await db.playlists.find({"user": ctx.author.id}).to_list(100)
    names = [p["name"] for p in playlists]
    await ctx.send(f"Your playlists: {', '.join(names)}")

@playlist.command(name="load")
async def pl_load(self, ctx, name):
    pl = await db.playlists.find_one({"user": ctx.author.id, "name": name})
    if pl:
        music_cog = bot.get_cog("MusicCog")
        for url in pl["songs"]:
            await music_cog.play(ctx, query=url)
        await ctx.send(f"Loaded '{name}'")

@playlist.command(name="delete")
async def pl_delete(self, ctx, name):
    await db.playlists.delete_one({"user": ctx.author.id, "name": name})
    await ctx.send(f"Deleted '{name}'")

# Events
@bot.event
async def on_ready():
    print(f"{bot.user} is online!")

@bot.event
async def on_voice_state_update(member, before, after):
    if member.guild.voice_client and len(member.guild.voice_client.channel.members) == 1:
        player = players.get(member.guild.id)
        if player and player.always_connected:
            return
        await member.guild.voice_client.disconnect()
        if member.guild.id in players:
            del players[member.guild.id]

# Start bot
async def main():
    keep_alive()
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
