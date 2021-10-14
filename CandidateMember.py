import asyncio
from functools import wraps
import discord
import discord_components
from discord_components import Select, SelectOption, Button, ButtonStyle
from main import HaigChessBot, SERVER_ID, VERIFICATION_CHANNEL_ID
from typing import Callable, Optional, Any
from FileHandling import *
from chesscom import get_player_profile, get_player_stats, ChessComError


def update(method: Callable):

    @wraps(method)
    async def wrapper(*args):
        self = args[0]
        func = getattr(self, method.__name__)
        self.storage["last_func"] = self.get_methods().index(func)
        self.last_func = self.get_methods().index(func)
        self.update_and_store()
        try:
            await method(*args)
        except discord.Forbidden:
            self.forbidden.append(self)
            return

        if not self.alt:
            self.update_and_store()
            await self.get_methods()[self.storage["last_func"] + 1](args[1])

    return wrapper


class CandidateMember:

    forbidden = []

    def __init__(self, member: discord.Member, storage: dict, last_func: int = 0):
        print(self.get_methods())
        self.member: discord.Member = member
        self.storage: dict = storage
        self.last_func = last_func
        self.is_verification_sent: bool = False
        if storage:
            self.alt = storage["alt"]
            self.name = storage["name"]
            self.email = storage["email"]
            self.grade = storage["grade"]
            self.chesscom_username = storage["username"]
            self.stats = storage["stats"]
            self.joined = storage["joined"]
        else:
            self.alt: Optional[int] = None
            self.name: Optional[str] = None
            self.email: Optional[str] = None
            self.grade: Optional[int] = None
            self.chesscom_username: Optional[str] = None
            self.stats: Optional[dict] = None
            self.joined: Optional[int] = None

        self.storage["last_func"] = last_func
        self.update_and_store()

    # VERIFICATION #
    async def is_not_alt_account(self, bot: HaigChessBot) -> bool:
        c_id: str = bot.edit_c_id()[0]
        # noinspection PyArgumentList
        await self.member.send(content="Are you a robot?", components=[
            Select(
                placeholder="Yes or No",
                options=[
                    SelectOption(label="Yes", value="Y"),
                    SelectOption(label="No", value="N")
                ],
                custom_id=c_id
            )
        ])
        interaction: discord_components.Interaction = await bot.wait_for(
            "select_option", check=lambda i: i.custom_id == c_id
        )
        await interaction.respond(content=f"{[a.label for a in interaction.component.options if a.value == interaction.values[0]][0]} selected")
        return interaction.values[0] == "N"

    @update
    async def get_alt_account(self, bot: HaigChessBot):
        if await self.is_not_alt_account(bot):
            print("HERE")
            return

        uid_question_embed = discord.Embed(
            title="User ID",
            description="Please enter the user ID of the account (the one in the server) below.",
        )
        uid_question_embed.set_footer(text="*If you meant to press \"no\", enter \"oops\" below.*")
        while True:

            await self.member.send(embed=uid_question_embed)
            msg = await bot.wait_for("message", check=lambda m: m.channel == self.member.dm_channel and m.author == self.member)

            if msg.content.lower() == "oops":
                return

            try:
                member: Optional[discord.User] = bot.get_user(int(msg.content.strip()))
            except ValueError:
                await self.member.send("That is not a valid ID!")
                continue

            if str(member.id) not in read_from_json("GM.txt").keys():
                await self.member.send("Could not find user with that ID!")
                continue

            break

        # noinspection PyUnboundLocalVariable
        self.alt = member.id
        await self.send_verification(bot, discord.Embed(title="Alt Account").add_field(name="ID", value=str(self.alt)))

    @update
    async def get_name(self, bot: HaigChessBot) -> None:
        await self.member.send(content="What's your name (first and last)?")
        print("NAME")
        msg = await bot.wait_for("message", check=lambda m: m.channel == self.member.dm_channel and m.author == self.member)
        self.name = msg.content

    @update
    async def get_email(self, bot: HaigChessBot) -> None:
        await self.member.send(content="What's your **student** email?")
        msg: discord.Message = await bot.wait_for("message", check=lambda m: m.channel == self.member.dm_channel and m.author == self.member)
        if "@student.tdsb.on.ca" not in msg.content.strip():
            await self.member.send(embed=bot.error_embed_builder("Invalid email! Please try again").set_footer(text="Were you entering your student email?"))
            await self.get_email(bot)
        self.email = msg.content.strip()

    @update
    async def get_grade(self, bot: HaigChessBot) -> None:
        c_id: str = bot.edit_c_id()[0]
        # noinspection PyArgumentList
        await self.member.send(content="What grade are you in?", components=[
            Select(
                placeholder="Select your grade",
                options=[
                    SelectOption(label="Grade 9", value="9"),
                    SelectOption(label="Grade 10", value="10"),
                    SelectOption(label="Grade 11", value="11"),
                    SelectOption(label="Grade 12", value="12")
                ],
                custom_id=c_id
            )
        ])
        interaction: discord_components.Interaction = await bot.wait_for(
            "select_option", check=lambda i: i.custom_id == c_id
        )
        await interaction.respond(content=f"{[a.label for a in interaction.component.options if a.value == interaction.values[0]][0]} selected")
        self.grade = int(interaction.values[0])

    @update
    async def get_chess_account(self, bot: HaigChessBot):
        msg: discord.Message = await self.member.send(
                embed=self.acc_embed_builder(desc=
                                             "We will be using chess.com for any tournaments and leagues. "
                                             "\nPlease enter your chess.com username below:"
                                             ).set_footer(
                                             text=
                                             "If you do not have a chess.com account, "
                                             "please create one at https://chess.com, it takes five seconds"
                                             )
                )
        chesscom_msg: discord.Message = await bot.wait_for("message", check=lambda m: m.channel == self.member.dm_channel and m.author == self.member)
        chesscom_str = chesscom_msg.content.lower().strip()
        try:
            chesscom_account: dict = await get_player_profile(chesscom_str.lower())
            chesscom_stats: dict = await get_player_stats(chesscom_str.lower())
        except ChessComError as e:
            if e.status_code == "429":
                await self.member.send(embed=bot.error_embed_builder(desc="There was a server error. The form will "
                                                                          "continue in 1 minute. Sorry for the "
                                                                          "inconvenience"
                                                                     )
                                       )
                await asyncio.sleep(60)

            else:
                await self.member.send(embed=bot.error_embed_builder(desc="Invalid ID! Please try again"))
                await asyncio.sleep(3)

            # noinspection PyArgumentList
            await self.get_chess_account(bot)
        self.chesscom_username = chesscom_str
        # noinspection PyUnboundLocalVariable
        self.joined = chesscom_account["joined"]
        # noinspection PyUnboundLocalVariable
        self.stats = chesscom_stats

    @update
    async def edit_responses(self, bot: HaigChessBot) -> None:
        c_id: list[str] = bot.edit_c_id(5)
        print(c_id)
        await self.member.send(embed=(embed := discord.Embed(title="Edit/Submit Responses",
                                                             colour=discord.Colour.blurple()).add_field(name="Full Name", value=self.name)
                                                                                             .add_field(name="Email", value=self.email)
                                                                                             .add_field(name="Grade", value=self.grade)
                                                                                             .add_field(name="Chess.com Username", value=self.chesscom_username)
                                      )
                               )
        # noinspection PyArgumentList
        await self.member.send(embed=discord.Embed(description="Choose which response you would like to edit, or choose \"submit\""),
                               components=[[Button(label="Name", custom_id=c_id[0]),
                                            Button(label="Email", custom_id=c_id[1]),
                                            Button(label="Grade", custom_id=c_id[2]),
                                            Button(label="Chess Account", custom_id=c_id[3]),
                                            Button(label="Submit", custom_id=c_id[4], style=ButtonStyle.green)]])
        interaction: discord_components.Interaction = await bot.wait_for(event="button_click", check=lambda i: i.custom_id in c_id)
        if interaction.custom_id != c_id[4]:
            await interaction.respond(content=f"Edit your {interaction.component.label} below:")
            await self.get_methods()[c_id.index(interaction.custom_id) + 1].__wrapped__(self, bot)
            self.update_and_store()
            await self.edit_responses(bot)
        else:
            await interaction.respond(
                content='Your form has been sent and is waiting approval!'
            )

            await self.send_verification(bot, embed)
            self.is_verification_sent = True
            self.update_and_store()

    async def send_verification(self, bot: HaigChessBot, embed: discord.Embed):
        verification_channel: discord.TextChannel = bot.get_channel(VERIFICATION_CHANNEL_ID)
        await verification_channel.send(content=f"{self.member.mention} {bot.get_guild(SERVER_ID).get_member(325713620879147010).mention}", embed=embed)

    @staticmethod
    def acc_embed_builder(desc: str) -> discord.Embed:
        return discord.Embed(
            title="Chess Accounts",
            description=desc,
            colour=discord.Colour.green()
        )

    def update_storage(self) -> None:
        self.storage["alt"] = self.alt
        self.storage["name"] = self.name
        self.storage["email"] = self.email
        self.storage["grade"] = self.grade
        self.storage["username"] = self.chesscom_username
        self.storage["stats"] = self.stats
        self.storage["joined"] = self.joined
        self.storage["is_verification_sent"] = self.is_verification_sent

    def store_everything(self) -> None:
        j_load = read_from_json("CM.txt")
        j_load[str(self.member.id)] = self.storage
        print(self.storage)
        write_to_json(j_load, "CM.txt")

    def update_and_store(self) -> None:
        self.update_storage()
        self.store_everything()

    def get_methods(self) -> list[Any]:
        return [self.get_alt_account, self.get_name, self.get_email,
                self.get_grade, self.get_chess_account, self.edit_responses]
