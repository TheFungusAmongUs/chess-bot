import discord
import asyncio
from chesscom import get_player_profile, get_player_stats, ChessComError
from FileHandling import read_from_json, write_to_json


class GeneralMember:

    def __init__(self, member: discord.Member, storage: dict):
        self.member = member
        self.storage = storage
        self.name = storage["name"]
        self.email = storage["email"]
        self.grade = storage["grade"]
        self.username = storage["username"]
        self.alt = storage["alt"]
        self.stats = storage["stats"]
        self.joined = storage["joined"]
        self.update_and_store()

    async def modify_username(self, new_username: str) -> bool:
        new_username = new_username.strip().lower()
        try:
            stats: dict = await get_player_stats(new_username)
            account: dict = await get_player_profile(new_username)
        except ChessComError:
            return False

        self.username = new_username
        self.stats = stats
        self.joined = account["joined"]
        self.update_and_store()

    async def update_stats(self):
        await asyncio.sleep(2)
        self.stats: dict = await get_player_stats(self.username)
        self.storage["stats"] = self.stats
        self.update_and_store()

    async def generate_stats(self) -> discord.Embed:
        user = await get_player_profile(self.username)
        try:
            image_url = user["avatar"]
        except KeyError:
            image_url = "https://www.chess.com/bundles/web/images/user-image.007dad08.svg"
        embed = discord.Embed(title=f"{self.member.nick if self.member.nick is not None else self.member.name}'s Chess.com Stats", colour=discord.Colour.green()).set_thumbnail(url=image_url)
        for stats in self.stats.keys():
            if stats.startswith("chess_"):
                embed.add_field(name=stats.strip("chess_").capitalize(), value=self.stats[stats]["last"]["rating"])
        return embed

    def update_storage(self) -> None:
        self.storage["name"] = self.name
        self.storage["email"] = self.email
        self.storage["grade"] = self.grade
        self.storage["username"] = self.username
        self.storage["stats"] = self.stats
        self.storage["joined"] = self.joined
        self.storage["alt"] = self.alt

    def store_everything(self) -> None:
        j_load = read_from_json("GeneralMembers.txt")
        j_load[str(self.member.id)] = self.storage
        write_to_json(j_load, "GeneralMembers.txt")

    def update_and_store(self) -> None:
        self.update_storage()
        self.store_everything()
