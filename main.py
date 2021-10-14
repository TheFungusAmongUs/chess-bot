import asyncio

import discord_components
from boto3 import Session
import discord
from discord.ext import commands
from FileHandling import *
from discord_components import ComponentsBot, Button
import CandidateMember
import GeneralMember
from MyChecks import is_me
from typing import Optional

#  <<<<<<<<< WIP >>>>>>>>>

"""
The following three lists include strings for chess.com's game results codes,
as defined in https://www.chess.com/news/view/published-data-api#game-results
"""
WIN_RESULTS = ["win"]
DRAW_RESULTS = ["insufficient", "50move", "timevsinsufficient", "stalemate", "agreed", "repetition"]
LOSS_RESULTS = ["checkmated", "lose", "resigned", "timeout", "abandoned"]
SERVER_ID = 854509117765976074
VERIFICATION_CHANNEL_ID = 896229535513706516
GM_ID = 854511830767894558
EXEC_ID = 854509645385302046
NM_ID = 896229932554932295
CHESS_COM_CHANNEL_ID = 896230298642178089
EVERYONE_ID = 854509117765976074

SPEAKERS = {
    "Arabic": ["Zeina"], "Chinese": ["Zhiyu"], "Danish": ["Naja", "Mads"], "Dutch": ["Lotte", "Ruben"],
    "English-AU": ["Nicole", "Olivia", "Russell"], "English-EN": ["Amy", "Emma", "Brian"],
    "English-IN": ["Aditi", "Raveena"],
    "English-US": ["Ivy", "Joanna", "Kendra", "Kimberley", "Salli", "Joey", "Justin", "Kevin", "Matthew"],
    "English-WLS": ["Geraint"], "French-FR": ["Céline", "Celine", "Léa", "Mathieu"],
    "French-CA": ["Chantal", "Gabrielle"], "German": ["Marlene", "Vicki", "Hans"], "Hindi": ["Aditi"],
    "Icelandic": ["Dora", "Karl"], "Italian": ["Carla", "Bianca", "Giorgio"],
    "Japanese": ["Mizuki", "Takumi"], "Korean": ["Seoyeon"], "Norwegian": ["Liv"],
    "Polish": ["Ewa", "Maja", "Jacek", "Jan"], "Portuguese-BR": ["Camila", "Vitoria", "Ricardo"],
    "Portuguese-PT": ["Ines", "Cristiano"], "Romanian": ["Carmen"], "Russian": ["Tatyana", "Maxim"],
    "Spanish_ES": ["Conchita", "Lucia", "Enrique"], "Spanish-MX": ["Mia"],
    "Spanish_US": ["Lupe", "Penelope", "Miguel"], "Swedish": ["Astrid"], "Turkish": ["Filiz"],
    "Welsh": ["Gwyneth"]
}
"""
Speakers for Amazon Polly, as listed in https://docs.aws.amazon.com/polly/latest/dg/voicelist.html
"""

LETTER_EMOTES = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯", "🇰", "🇱", "🇲",
                 "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹", "🇺", "🇻", "🇼", "🇽", "🇾", "🇿"]


class HaigChessBot(ComponentsBot):

    def __init__(self, command_prefix: str):
        ComponentsBot.__init__(self, command_prefix=command_prefix, help_command=None, intents=discord.Intents.all())
        self.ready_message = "Bot is now ready"
        self.add_commands()
        self.polly_client = self.get_polly()
        self.custom_id = 0
        self.candidate_members: list[CandidateMember.CandidateMember] = []
        self.general_members: list[GeneralMember.GeneralMember] = []
        self.other_members: list[int] = []

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return
        await self.process_commands(message=message)

    async def on_ready(self):
        global SERVER
        print(self.ready_message)
        print(f"Running discord v{discord.__version__}!")
        SERVER = self.get_guild(SERVER_ID)
        await self.load_cms()
        await self.load_gms()
        self.other_members = read_from_json("OM.txt")["OMs"]
        verifications = [a.get_methods()[a.last_func](self) for a in self.candidate_members]
        await asyncio.gather(*verifications, return_exceptions=True)

    async def on_button_click(self, interaction: discord_components.Interaction):
        if interaction.custom_id != "VERIFICATION":
            return

        for cm in self.candidate_members:
            if (
                cm.member.id == interaction.user.id
                and cm in CandidateMember.CandidateMember.forbidden
            ):
                await cm.get_methods()[cm.last_func](self)
                break

    async def on_member_join(self, member: discord.Member):
        if str(member.id) in (j_load := read_from_json("GM.txt")).keys():
            await member.add_roles(SERVER.get_role(GM_ID))
            g = GeneralMember.GeneralMember(member, j_load[str(member.id)])
            self.general_members.append(g)
            await self.update_accounts()
            return
        if member.id in self.other_members:
            await member.add_roles(SERVER.get_role(NM_ID))
            return
        if member.bot:
            return

        c = CandidateMember.CandidateMember(member, {})
        try:
            await member.send(
                embed=discord.Embed(
                    title="Welcome!",
                    description="Welcome to the Earl Haig Chess Club's official Discord server! Please fill out the GM form below.\n\n"
                                "If you have any trouble, or if you are not a student at Earl Haig, "
                                "please contact TheFungusAmongUs#1111\nChess Club Meetings are hosted every Friday from 3:45 to 4:45 starting next week October 15th.\nThank you, and have fun!",
                    colour=discord.Colour.blurple(),
                )
            )

        except discord.Forbidden:
            CandidateMember.CandidateMember.forbidden.append(c)
        await c.get_alt_account(self)

    def add_commands(self):

        @self.command(name="help")
        @is_me
        async def _help(ctx: commands.Context):
            pass

        @self.command()
        @commands.has_permissions(deafen_members=True)
        async def deafen(ctx: commands.Context, member: discord.Member):
            await member.edit(mute=not member.voice.deafen)

        @self.command()
        @commands.has_permissions(ban_members=True)
        async def ban(ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
            await member.ban(reason=reason)

        @self.command()
        @commands.has_permissions(kick_members=True)
        async def kick(ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
            await member.kick(reason=reason)

        @self.command()
        @commands.has_permissions(manage_messages=True)
        async def clear(ctx: commands.Context, count: int, member: Optional[discord.Member] = None):
            await ctx.channel.purge(limit=count, check=lambda m: (not member or m.author == member))

        @self.command()
        @commands.has_permissions(administrator=True)
        async def confirm(ctx: commands.Context, member_id: str):
            j_load = read_from_json("CM.txt")
            if member_id not in j_load.keys():
                await ctx.send(embed=self.error_embed_builder("User not found!"))
                return
            member: discord.Member = await SERVER.fetch_member(int(member_id))
            gm = GeneralMember.GeneralMember(member, j_load[member_id])
            await member.add_roles(SERVER.get_role(GM_ID))
            del j_load[member_id]
            write_to_json(j_load, "CM.txt")
            self.general_members.append(gm)
            for m in self.candidate_members:
                if m.member.id == int(member_id):
                    self.candidate_members.remove(m)
                    break
            await self.update_accounts()

        @self.command()
        @is_me
        async def send_welcome(ctx: commands.Context):
            txt_channel: discord.TextChannel = self.get_channel(779078485829353503)
            await txt_channel.send(embed=discord.Embed(title="Welcome!", description="You have probably received a DM from our bot to fill out our GM form."
                                                                                     "If you have not, please check your privacy settings to ensure that you are accepting DMs from this server, then click the button below.\n\n",
                                                       colour=discord.Colour.blurple()).set_footer(text="To change privacy settings, right click the server icon and go to Privacy Settings "),
                                   components=[Button(label="Only click me if you have not received a DM", custom_id="VERIFICATION")]
                                   )

        @self.command()
        @is_me
        async def verify_all_members(ctx: commands.Context):
            coros = []
            for member in SERVER.members:
                if member.id in self.other_members or member.bot:
                    continue
                remove_roles: Optional[list[discord.Role]] = []
                for role in member.roles:
                    if role.id in (EXEC_ID, EVERYONE_ID):
                        continue
                    remove_roles.append(role)
                if remove_roles:
                    await member.remove_roles(*remove_roles, reason="Verification")
                cm = CandidateMember.CandidateMember(member, {})
                coros.append(cm.get_methods()[cm.last_func](self))
            await asyncio.gather(*coros)

        @self.command()
        async def get_stats(ctx: commands.Context, member: discord.Member):
            for gm in self.general_members:
                if gm.alt:
                    gm = self.get_alt_with_id(gm.alt)
                if gm.member == member:
                    async with ctx.typing():
                        await gm.update_stats()
                        await ctx.send(embed=await gm.generate_stats())
                        return

    def edit_c_id(self, count: int = 1) -> list[str]:
        self.custom_id += count
        return [str(c) for c in range(self.custom_id - count, self.custom_id)]

    def get_alt_with_id(self, id_: int) -> GeneralMember.GeneralMember:
        for gm in self.general_members:
            if gm.member.id == id_:
                return gm

    async def update_accounts(self):
        embed = discord.Embed(title="CHESS.COM ACCOUNTS", colour=discord.Colour.blurple())
        for member in self.general_members:
            embed.add_field(name=member.username, value=member.member.mention)
        if len(await (ch := self.get_channel(CHESS_COM_CHANNEL_ID)).history().flatten()) == 0:
            await ch.send(embed=embed)
            return
        async for message in ch.history():
            if message.author == self.user:
                await message.edit(embed=embed)

    async def load_cms(self):
        j_load = read_from_json("CM.txt")
        for key in j_load.keys():
            if not (member := SERVER.get_member(int(key))) or j_load[key]["is_verification_sent"]:
                continue
            self.candidate_members.append(
                (a := CandidateMember.CandidateMember(member, j_load[key], j_load[key]["last_func"])))
            try:
                await a.member.send(embed=self.error_embed_builder(
                    desc="Sorry, it looks like the bot went offline. The form will now continue (sry for spam, if you complete the form it'll stop though - Nathan)")
                )
            except discord.Forbidden:
                CandidateMember.CandidateMember.forbidden.append(a)

    async def load_gms(self):
        j_load = read_from_json("GM.txt")
        for key in j_load.keys():
            if not (member := SERVER.get_member(int(key))):
                continue
            self.general_members.append(
                (GeneralMember.GeneralMember(member, j_load[key]))
            )
        await self.update_accounts()

    @staticmethod
    def get_polly():
        keys = read_from_json("AWS_STUFF.json")
        return Session(aws_access_key_id=keys["aws_access_key_id"],
                       aws_secret_access_key=keys["aws_secret_access_key"],
                       region_name=keys["region_name"]).client("polly")

    @staticmethod
    def error_embed_builder(desc: str) -> discord.Embed:
        return discord.Embed(
            title="ERROR",
            description=desc,
            colour=discord.Colour.red()
        )


def main():
    bot = HaigChessBot(command_prefix='$')
    with open("token.txt") as token:
        bot.run(token.read())


if __name__ == "__main__":
    main()
