import random
import json
from twitchio.ext import commands
from datetime import datetime, timedelta

class BugCollectorBot(commands.Bot):
    def __init__(self):
        super().__init__(token='ACCESS_TOKEN', prefix='+', initial_channels=['twitch_channel'])
        self.bugs_collected = self.load_user_data()
        self.bug_names = self.load_bug_names()
        self.cooldowns = {}
        self.levels = self.load_levels()
        self.load_xp_data()

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

    def load_xp_data(self):
        try:
            with open('xp.txt', 'r') as f:
                self.xp_data = json.load(f)
        except FileNotFoundError:
            self.xp_data = {}

    def load_bug_names(self):
        with open('bugs.txt', 'r') as f:
            bug_names = [line.strip() for line in f]
        return {bug: f'🐛{bug[0].upper()}{bug[1:]}' for bug in bug_names}

    def load_user_data(self):
        try:
            with open('users.txt', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_user_data(self):
        with open('users.txt', 'w') as f:
            json.dump(self.bugs_collected, f)

    def load_levels(self):
        try:
            with open('lvl.txt', 'r') as f:
                data = f.read()
                if data:
                    return json.loads(data)
                else:
                    return {}
        except FileNotFoundError:
            return {}

    def save_levels(self):
        with open('lvl.txt', 'w') as f:
            json.dump(self.levels, f)

    async def check_cooldown(self, ctx):
        if ctx.author.name.lower() in self.cooldowns:
            remaining = self.cooldowns[ctx.author.name.lower()] - datetime.utcnow()
            if remaining.total_seconds() > 0:
                await ctx.send(f'{ctx.author.name}, please wait {int(remaining.total_seconds())} seconds before using this command again.')
                return True
        return False

    @commands.command()
    async def catch(self, ctx: commands.Context):
        if await self.check_cooldown(ctx):
            return

        self.cooldowns[ctx.author.name.lower()] = datetime.utcnow() + timedelta(seconds=10)

        catch_chance = random.random()
        if catch_chance < 0.4:
            await ctx.send(f'{ctx.author.name} tried to catch a bug but missed!')
        elif catch_chance < 0.001:  # 1 in 1000 chance
            bug_name = "Stag Beetle 🦌"
            user_data = self.bugs_collected.get(ctx.author.name.lower(), {})
            if bug_name.lower() in user_data:
                user_data[bug_name.lower()] += 1
            else:
                user_data[bug_name.lower()] = 1

            self.bugs_collected[ctx.author.name.lower()] = user_data
            self.save_user_data()

            await ctx.send(f'{ctx.author.name} caught {bug_name}! 🎉 Total {bug_name}s collected: {user_data[bug_name.lower()]}')
        else:
            bug_name = random.choice(list(self.bug_names.keys()))
            emoji = self.bug_names[bug_name]

            user_data = self.bugs_collected.get(ctx.author.name.lower(), {})
            if bug_name.lower() in user_data:
                user_data[bug_name.lower()] += 1
            else:
                user_data[bug_name.lower()] = 1

            self.bugs_collected[ctx.author.name.lower()] = user_data
            self.save_user_data()

            await ctx.send(f'{ctx.author.name} collected {bug_name}! Total {bug_name}s collected: {user_data[bug_name.lower()]}')

            # Check if user leveled up
            if sum(user_data.values()) % 15 == 0:
                level = self.levels.get(ctx.author.name.lower(), 0) + 1
                self.levels[ctx.author.name.lower()] = level
                self.save_levels()
                await ctx.send(f'Congratulations, {ctx.author.name}! You leveled up to level {level}!')

    @commands.command(name='bugs')
    async def bugs(self, ctx: commands.Context):
        author_name = ctx.author.name.lower()
        user_data = self.bugs_collected.get(author_name, {})
        if user_data:
            bug_list = '\n'.join([f' Total {bug}s collected: {count} ' for bug, count in user_data.items()])
            await ctx.send(f'{ctx.author.name}, you have collected the following bugs:\n{bug_list} ')
        else:
            await ctx.send('No bugs have been collected yet!')

    @commands.command()
    async def release(self, ctx: commands.Context):
        author_name = ctx.author.name.lower()
        if author_name in self.bugs_collected:
            del self.bugs_collected[author_name]
            self.save_user_data()
            await ctx.send(f'{ctx.author.name}, all of your bugs have been released.')
        else:
            await ctx.send('No bugs to release.')

    @commands.command()
    async def bugtop(self, ctx: commands.Context):
        sorted_users = sorted(self.bugs_collected.items(), key=lambda x: sum(x[1].values()), reverse=True)[:5]
        leaderboard_text = '\n'.join([f'{user[0]}: {sum(user[1].values())} bugs ' for user in sorted_users])
        await ctx.send(f'Leaderboard - Top 5 Bug Collectors:\n{leaderboard_text}')

    @commands.command()
    async def eat(self, ctx: commands.Context):
        author_name = ctx.author.name.lower()
        user_data = self.bugs_collected.get(author_name, {})
        total_bugs = sum(user_data.values())

        if total_bugs == 0:
            await ctx.send(f'{ctx.author.name}, you don\'t have any bugs to eat!')
            return

        # Calculate XP gain based on bugs eaten
        xp_gain = total_bugs * 0.0666666

        with open('xp.txt', 'r') as f:
            xp_data = json.load(f)

        if author_name in xp_data:
            current_xp = xp_data[author_name]
        else:
            current_xp = 0

        new_xp = current_xp + xp_gain
        xp_data[author_name] = new_xp

        with open('xp.txt', 'w') as f:
            json.dump(xp_data, f)

        if new_xp >= 1:
            level = self.levels.get(author_name, 0) + int(new_xp)
            self.levels[author_name] = level
            self.save_levels()
            await ctx.send(f'{ctx.author.name} ate {total_bugs} bugs and gained {xp_gain:.2f} XP, leveling up to level {level}!')
            user_data.clear()  # Clear bugs after level up
            self.save_user_data()

            # Reset XP back to 0
            xp_data[author_name] = 0
            with open('xp.txt', 'w') as f:
                json.dump(xp_data, f)
        else:
            # Remove all bugs that were eaten
            user_data.clear()
            self.save_user_data()

            await ctx.send(f'{ctx.author.name} ate {total_bugs} bugs and gained {xp_gain:.2f} XP!')

            # Update user data after eating bugs
            self.bugs_collected[author_name] = user_data

    @commands.command()
    async def level(self, ctx: commands.Context):
        author_name = ctx.author.name.lower()
        level = self.levels.get(author_name, 0)
        await ctx.send(f'{ctx.author.name}, your current level is {level}!')

    @commands.command()
    async def leaderboard(self, ctx: commands.Context):
        sorted_users = sorted(self.levels.items(), key=lambda x: x[1], reverse=True)[:5]
        leaderboard_text = '\n'.join([f'{user[0]}: Level {user[1]} ' for user in sorted_users])
        await ctx.send(f'Top 5 Players by Level:\n{leaderboard_text}')


bot = BugCollectorBot()
bot.run()
