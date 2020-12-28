import asyncio
import json
import socket
import subprocess

from discord.ext import commands


class MyContext(commands.Context):
    async def start_server(self):
        # if we've already started the server, tell the player
        if self.bot.minecraft_task is not None:
            await self.message.channel.send("Server is already running")
        else:
            await self.message.channel.send("Starting server...")
            self.bot.minecraft_task = self.bot.loop.create_task(
                self.bot.start_mc(self.message.channel)
            )

    async def stop_server(self):
        # if the server hasn't started, tell the player
        if self.bot.minecraft_task is None:
            await self.message.channel.send("Server is not running")
        else:
            await self.message.channel.send("Stopping server...")
            await self.bot.stop_mc(self.message.channel)


class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.minecraft_task = None
        self.minecraft_process = None

        with open(r".\secrets.json") as f:
            secrets = json.load(f)
        self.api_token = secrets["api_token"]
        self.minecraft_dir = secrets["minecraft_directory"]

    async def get_context(self, message, *, cls=MyContext):
        return await super().get_context(message, cls=cls)

    async def start_mc(self, channel):
        self.minecraft_process = await asyncio.create_subprocess_exec(
            "java",
            "-Xms512M",
            "-Xmx2G",
            "-jar",
            f"{self.minecraft_dir}\forge-1.16.4-35.1.13.jar",
            "--nogui",
            cwd=self.minecraft_dir,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            while s.connect_ex(("98.216.48.19", 25565)):
                await asyncio.sleep(1)
            await channel.send("Server running!")

    async def stop_mc(self, channel):
        try:
            await asyncio.wait_for(
                self.minecraft_process.communicate(input=b"/stop"),
                timeout=30.0,
                loop=self.loop,
            )
            await asyncio.wait_for(
                self.minecraft_process.wait(), timeout=30.0, loop=self.loop
            )
        except asyncio.TimeoutError:
            print("Failed to gracefully stop server. Terminating...")
            self.minecraft_process.kill()
        self.minecraft_process = None
        self.minecraft_task = None
        await channel.send("Server stopped!")


bot = MyBot(command_prefix=commands.when_mentioned)


@bot.event
async def on_ready():
    print("Logged in as")
    print(bot.user.name)
    print(bot.user.id)
    print("------")


@bot.command()
async def start(ctx):
    """Start the minecraft server."""
    await ctx.start_server()


@bot.command()
async def stop(ctx):
    """Stop the minecraft server."""
    await ctx.stop_server()


bot.run(bot.api_token)
