import discord
import aiohttp
import asyncio
import json
import os
from datetime import datetime
from discord.ext import commands
from redbot.core import Config
from redbot.core import checks
from redbot.core.data_manager import cog_data_path
from pathlib import Path
from bs4 import BeautifulSoup
try:
    import tweepy as tw
    twInstalled = True
except:
    twInstalled = False

numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}
class QPosts:

    def __init__(self, bot):
        self.bot = bot
        default_data = {"twitter":{"access_secret" : "",
        "access_token" : "",
        "consumer_key" : "",
        "consumer_secret" : ""}, "boards":{}, "channels":[]}
        self.config = Config.get_conf(self, 112444567876)
        self.config.register_global(**default_data)
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        # self.settings = dataIO.load_json("data/qposts/settings.json")
        # self.qposts = dataIO.load_json("data/qposts/qposts.json")
        self.url = "https://8ch.net"
        self.boards = ["greatawakening", "qresearch"]
        self.loop = bot.loop.create_task(self.get_q_posts())

    def __unload(self):
        self.session.close()
        self.loop.cancel()

    async def authenticate(self):
        """Authenticate with Twitter's API"""
        auth = tw.OAuthHandler(await self.config.twitter.consumer_key(), await self.config.twitter.consumer_secret())
        auth.set_access_token(await self.config.twitter.access_token(), await self.config.twitter.access_secret())
        return tw.API(auth)

    async def send_tweet(self, message: str, file=None):
        """Sends tweets as the bot owners account"""
        if not twInstalled:
            return
        api = await self.authenticate()
        if file is None:
            api.update_status(message)
        else:
            api.update_with_media(file, status=message)

    @commands.command()
    async def dlq(self, ctx):
        board_posts = await self.config.boards()
        for board in self.boards:
            async with self.session.get("{}/{}/catalog.json".format(self.url, board)) as resp:
                data = await resp.json()
            Q_posts = []
            
            for page in data:
                for thread in page["threads"]:
                    print(thread["no"])
                    async with self.session.get("{}/{}/res/{}.json".format(self.url, board,thread["no"])) as resp:
                        posts = await resp.json()
                    for post in posts["posts"]:
                        if "trip" in post:
                            if post["trip"] in ["!UW.yye1fxo", "!ITPb.qbhqo"]:
                                Q_posts.append(post)
            board_posts[board] = Q_posts
        await self.config.boards.set(board_posts)

    @commands.command(pass_context=True, name="qrole")
    async def qrole(self, ctx):
        """Set your role to a team role"""
        guild = ctx.message.guild
        try:
            role = [role for role in guild.roles if role.name == "QPOSTS"][0]
            await self.bot.add_roles(ctx.message.author, role)
            await self.bot.send_message(ctx.message.channel, "Role applied.")
        except:
            return

    async def get_q_posts(self):
        await self.bot.wait_until_ready()
        while self is self.bot.get_cog("QPosts"):
            board_posts = await self.config.boards()
            for board in self.boards:
                try:
                    async with self.session.get("{}/{}/catalog.json".format(self.url, board)) as resp:
                        data = await resp.json()
                except:
                    print("error grabbing board catalog {}".format(board))
                    continue
                Q_posts = []
                if board not in board_posts:
                    board_posts[board] = []
                for page in data:
                    for thread in page["threads"]:
                        # print(thread["no"])
                        try:
                            async with self.session.get("{}/{}/res/{}.json".format(self.url, board,thread["no"])) as resp:
                                posts = await resp.json()
                        except:
                            print("error grabbing thread {} in board {}".format(thread["no"], board))
                            continue
                        for post in posts["posts"]:
                            if "trip" in post:
                                if post["trip"] in ["!UW.yye1fxo"]:
                                    Q_posts.append(post)
                old_posts = [post_no["no"] for post_no in board_posts[board]]

                for post in Q_posts:
                    if post["no"] not in old_posts:
                        board_posts[board].append(post)
                        # dataIO.save_json("data/qposts/qposts.json", self.qposts)
                        await self.postq(post, "/{}/".format(board))
                    for old_post in board_posts[board]:
                        if old_post["no"] == post["no"] and old_post["com"] != post["com"]:
                            if "edit" not in board_posts:
                                board_posts["edit"] = {}
                            if board not in board_posts["edit"]:
                                board_posts["edit"][board] = []
                            board_posts["edit"][board].append(old_post)
                            board_posts[board].remove(old_post)
                            board_posts[board].append(post)
                            # dataIO.save_json("data/qposts/qposts.json", self.qposts)
                            await self.postq(post, "/{}/ {}".format(board, "EDIT"))
            await self.config.boards.set(board_posts)
            print("checking Q...")
            asyncio.sleep(60)

    async def get_quoted_post(self, qpost):
        html = qpost["com"]
        soup = BeautifulSoup(html, "html.parser")
        reference_post = []
        for a in soup.find_all("a", href=True):
            # print(a)
            url, post_id = a["href"].split("#")[0].replace("html", "json"), int(a["href"].split("#")[1])
            async with self.session.get(self.url + url) as resp:
                data = await resp.json()
            for post in data["posts"]:
                if post["no"] == post_id:
                    reference_post.append(post)
        return reference_post
            
    # @commands.command(pass_context=True)
    async def postq(self, qpost, board):
        name = qpost["name"] if "name" in qpost else "Anonymous"
        url = "{}/{}/res/{}.html#{}".format(self.url, board, qpost["resto"], qpost["no"])
        
        html = qpost["com"]
        soup = BeautifulSoup(html, "html.parser")
        ref_text = ""
        text = ""
        img_url = ""
        reference = await self.get_quoted_post(qpost)
        if qpost["com"] != "<p class=\"body-line empty \"></p>":
            for p in soup.find_all("p"):
                if p.string is None:
                    text += "."
                else:
                    text += p.string + "\n"
        if reference != []:
            for post in reference:
                # print(post)
                ref_html = post["com"]
                soup_ref = BeautifulSoup(ref_html, "html.parser")
                for p in soup_ref.find_all("p"):
                    if p.string is None:
                        ref_text += "."
                    else:
                        ref_text += p.string + "\n"
            if "tim" in reference[0] and "tim" not in qpost:
                file_id = reference[0]["tim"]
                file_ext = reference[0]["ext"]
                img_url = "https://media.8ch.net/file_store/{}{}".format(file_id, file_ext)
                await self.save_q_files(reference[0])
        if "tim" in qpost:
            file_id = qpost["tim"]
            file_ext = qpost["ext"]
            img_url = "https://media.8ch.net/file_store/{}{}".format(file_id, file_ext)
            await self.save_q_files(qpost)

        # print("here")
        em = discord.Embed(colour=discord.Colour.red())
        em.set_author(name=name + qpost["trip"], url=url)
        em.timestamp = datetime.utcfromtimestamp(qpost["time"])
        if text != "":
            if "_" in text or "~" in text or "*" in text:
                em.description = "```\n{}```".format(text[:1993])
            else:
                em.description = text[:2000]
        if ref_text != "":
            if "_" in ref_text or "~" in ref_text or "*" in ref_text:
                em.add_field(name=str(post["no"]), value="```{}```".format(ref_text))
            else:
                em.add_field(name=str(post["no"]), value=ref_text)
        if img_url != "":
            em.set_image(url=img_url)
            try:
                print("sending tweet")
                tw_msg = "{}\n#QAnon\n{}".format(url, text)
                await self.send_tweet(tw_msg[:280], "data/qposts/files/{}{}".format(file_id, file_ext))
            except Exception as e:
                print(e)
                pass
        else:
            try:
                print("sending tweet")
                tw_msg = "{}\n#QAnon\n{}".format(url, text)
                await self.send_tweet(tw_msg[:280])
            except Exception as e:
                print(e)
                pass
        em.set_footer(text=board)
        
        
        for channel_id in await self.config.channels():
            channel = self.bot.get_channel(id=channel_id)
            guild = channel.guild
            try:
                role = [role for role in guild.roles if role.name == "QPOSTS"][0]
                await channel.send("{} <{}>".format(role.mention, url), embed=em)
            except:
                await channel.send("<{}>".format(url), embed=em)

        if len(text) > 1993:
            em = discord.Embed(colour=discord.Colour.red())
            em.set_author(name=name + qpost["trip"], url=url)
            em.timestamp = datetime.utcfromtimestamp(qpost["time"])
            em.description = "```\n{}```".format(text[1993:])
            reference = await self.get_quoted_post(qpost)
            if ref_text != "":
                em.add_field(name=str(post["no"]), value="```{}```".format(ref_text))
            if img_url != "":
                em.set_image(url=img_url)   
            em.set_footer(text=board)
            
            for channel_id in await self.config.channels():
                channel = self.bot.get_channel(id=channel_id)
                if channel is None:
                    continue
                guild = channel.guild
                try:
                    role = [role for role in guild.roles if role.name == "QPOSTS"][0]
                    await self.bot.send_message(channel, "{} <{}>".format(role.mention, url), embed=em)
                except:
                    await self.bot.send_message(channel, "<{}>".format(url), embed=em)

    async def q_menu(self, ctx, post_list: list, board,
                         message: discord.Message=None,
                         page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""

        qpost = post_list[page]
        em = discord.Embed(colour=discord.Colour.red())
        name = qpost["name"] if "name" in qpost else "Anonymous"
        url = "{}/{}/res/{}.html#{}".format(self.url, board, qpost["resto"], qpost["no"])
        em.set_author(name=name + qpost["trip"], url=url)
        em.timestamp = datetime.utcfromtimestamp(qpost["time"])
        html = qpost["com"]
        soup = BeautifulSoup(html, "html.parser")
        text = ""
        for p in soup.find_all("p"):
            if p.string is None:
                text += "."
            else:
                text += p.string + "\n"
        em.description = "```{}```".format(text[:1800])
        reference = await self.get_quoted_post(qpost)
        if reference != []:
            for post in reference:
                # print(post)
                ref_html = post["com"]
                soup_ref = BeautifulSoup(ref_html, "html.parser")
                ref_text = ""
                for p in soup_ref.find_all("p"):
                    if p.string is None:
                        ref_text += "."
                    else:
                        ref_text += p.string + "\n"
                em.add_field(name=str(post["no"]), value="```{}```".format(ref_text))
            if "tim" in post and "tim" not in qpost:
                file_id = post["tim"]
                file_ext = post["ext"]
                img_url = "https://media.8ch.net/file_store/{}{}".format(file_id, file_ext)
                if file_ext in [".png", ".jpg", ".jpeg"]:
                    em.set_image(url=img_url)
        em.set_footer(text="/{}/".format(board))
        if "tim" in qpost:
            file_id = qpost["tim"]
            file_ext = qpost["ext"]
            img_url = "https://media.8ch.net/file_store/{}{}".format(file_id, file_ext)
            if file_ext in [".png", ".jpg", ".jpeg"]:
                em.set_image(url=img_url)
        if not message:
            message = await ctx.send(embed=em)
            await message.add_reaction("⬅")
            await message.add_reaction("❌")
            await message.add_reaction("➡")
        else:
            # message edits don't return the message object anymore lol
            await message.edit(embed=em)
        check = lambda react, user:user == ctx.message.author and react.emoji in ["➡", "⬅", "❌"]
        try:
            react, user = await self.bot.wait_for("reaction_add", check=check, timeout=timeout)
        except asyncio.TimeoutError:
            await message.remove_reaction("⬅", self.bot.user)
            await message.remove_reaction("❌", self.bot.user)
            await message.remove_reaction("➡", self.bot.user)
            return None
        else:
            reacts = {v: k for k, v in numbs.items()}
            react = reacts[react.emoji]
            if react == "next":
                next_page = 0
                if page == len(post_list) - 1:
                    next_page = 0  # Loop around to the first item
                else:
                    next_page = page + 1
                try:
                    await message.remove_reaction("➡", ctx.message.author)
                except:
                    pass
                return await self.q_menu(ctx, post_list, board, message=message,
                                             page=next_page, timeout=timeout)
            elif react == "back":
                next_page = 0
                if page == 0:
                    next_page = len(post_list) - 1  # Loop around to the last item
                else:
                    next_page = page - 1
                try:
                    await message.remove_reaction("⬅", ctx.message.author)
                except:
                    pass
                return await self.q_menu(ctx, post_list, board, message=message,
                                             page=next_page, timeout=timeout)
            else:
                return await message.delete()

    @commands.command(pass_context=True, aliases=["postq"])
    async def qpost(self, ctx, board="greatawakening"):
        if board not in await self.config.boards():
            await ctx.send("{} is not an available board!")
            return
        qposts = await self.config.boards()
        qposts = list(reversed(qposts[board]))
        await self.q_menu(ctx, qposts, board)

    async def save_q_files(self, post):
        file_id = post["tim"]
        file_ext = post["ext"]
        file_path =  cog_data_path(self) /"files"
        file_path.mkdir(exist_ok=True, parents=True)
        url = "https://media.8ch.net/file_store/{}{}".format(file_id, file_ext)
        async with self.session.get(url) as resp:
            image = await resp.read()
        with open(str(file_path) + "/{}{}".format(file_id, file_ext), "wb") as out:
            out.write(image)
        if "extra_files" in post:
            for file in post["extra_files"]:
                file_id = file["tim"]
                file_ext = file["ext"]
                url = "https://media.8ch.net/file_store/{}{}".format(file_id, file_ext)
                async with self.session.get(url) as resp:
                    image = await resp.read()
                with open(str(file_path) + "/{}{}".format(file_id, file_ext), "wb") as out:
                    out.write(image)

    @commands.command(pass_context=True)
    async def qchannel(self, ctx, channel:discord.TextChannel=None):
        if channel is None:
            channel = ctx.message.channel
        guild = ctx.message.guild
        cur_chans = await self.config.channels()
        if channel.id in cur_chans:
            await ctx.send("{} is already posting new Q posts!".format(channel.mention))
            return
        else:
            cur_chans.append(channel.id)
        await self.config.channels.set(cur_chans)
        await ctx.send("{} set for qposts!".format(channel.mention))

    @commands.command(pass_context=True)
    async def remqchannel(self, ctx, channel:discord.TextChannel=None):
        if channel is None:
            channel = ctx.message.channel
        guild = ctx.message.guild
        cur_chans = await self.config.channels()
        if channel.id not in cur_chans:
            await ctx.send("{} is not posting new Q posts!".format(channel.mention))
            return
        else:
            cur_chans.remove(channel.id)
        await self.config.channels.set(cur_chans)
        await ctx.send("{} set for qposts!".format(channel.mention))

    @commands.command(name='qtwitterset')
    @checks.is_owner()
    async def set_creds(self, ctx, consumer_key: str, consumer_secret: str, access_token: str, access_secret: str):
        """[p]tweetset """
        api = {'consumer_key': consumer_key, 'consumer_secret': consumer_secret,
            'access_token': access_token, 'access_secret': access_secret}
        await self.config.twitter.set(api)
        await ctx.send('Set the access credentials!')
