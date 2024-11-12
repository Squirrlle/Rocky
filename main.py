import discord
import json
import os
import random
import re
import nltk
import wikipedia
from discord.ext import commands
from nltk.tokenize import sent_tokenize

# region Setup
with open("configuration.json", "r") as config:
    """Load configuration"""
    config_data = json.load(config)
    TOKEN = config_data["token"]
    PREFIX = config_data["prefix"]
    OWNER_ID = config_data["owner_id"]

"""Set up intents"""
intents = discord.Intents.default()
intents.message_content = True

"""Create the bot"""
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

"""Load cogs"""
if __name__ == '__main__':
    for filename in os.listdir("Cogs"):
        if filename.endswith(".py"):
            bot.load_extension(f"Cogs.{filename[:-3]}")

"""Load rock types"""
with open('rocks.json') as f:
    ROCK_TYPES = json.load(f)['Rock Types']
# endregion

# region Helpers
def calculate_sentence_scores(sentences, page_content):
    """Calculate sentence scores"""
    return {sentence: sum(1 for word in nltk.word_tokenize(sentence) if word in page_content) for sentence in sentences}

def get_top_sentences(sentence_scores, n):
    """Get top sentences"""
    return sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:n]

def generate_summary(page, sentences, n):
    """Generate a summary of the Wikipedia page."""
    sentence_scores = calculate_sentence_scores(sentences, page.content)
    top_sentences = get_top_sentences(sentence_scores, n)
    return "\n".join(top_sentences)

def make_message(page, random_rock_type):
    """Generates a message from a wikipedia article"""
    sentences = sent_tokenize(page.content)
    summary = generate_summary(page, sentences, 5)
    message = f"Rock found: [{random_rock_type}]({page.url})\n{summary}"
    if len(message) > 2000:
        message = message[:1997] + '...'
    return message
# endregion 

# region Commands
@bot.command(name='gen_rock', 
             usage="(commandName)", 
             description="Gets a random rock", 
             aliases=['gen_rocks', 'genrock', 'genrocks'])
async def get_rock(ctx):
    """Generate a random rock and send its Wikipedia page and summary"""
    random_rock_type = random.choice(ROCK_TYPES)
    try:
        """Get the Wikipedia page with spicifing rock for clarification"""
        page = wikipedia.page(f"{random_rock_type} rock")
        message = make_message(page, random_rock_type)
        await ctx.send(message)
    except (wikipedia.exceptions.DisambiguationError, wikipedia.exceptions.PageError) as e:
        try:
            """Gets the Wikipedia page without specifying rock"""
            page = wikipedia.page(f"{random_rock_type}")
            message = make_message(page, random_rock_type)
            await ctx.send(message)
        except (wikipedia.exceptions.DisambiguationError, wikipedia.exceptions.PageError) as e:
            print(f"{random_rock_type}")
            await ctx.send(f"Error: {e}")
    except discord.HTTPException as e:
        if e.status == 400 and e.code == 50035:
            await ctx.send("Error: The message is too long. Please try again.")
        else:
            await ctx.send(f"Error: {e}")

@bot.command(
    name='r',
    usage="(commandName) <[x]dy> [ + <z>] [a|d|e] [! <threshold>]",
    description="""Rolls x dice of y sides and adds z to the result,
        dropping the lowest roll if 'a' is specified,
        the highest roll if 'd' is specified,
        or dropping the two lowest rolls if 'e' is specified.
        If 'a', 'd', or 'e' is used, it always rolls 3 dice.
        Additionally, '! <threshold>' drops all rolls less than 
        the specified threshold."""
)
async def roll_dice(ctx, *, command: str):
    """Roll the dice."""
    """Regex is magic"""
    match = re.match(r'(?:(\d*)d(\d+))(?:\s*([+-]?)\s*(\d+))?(?:\s*(a|d|e))?(?:\s*!\s*(\d+))?', command)
    
    if match:
        drop_lowest = match.group(5) == 'a'
        drop_highest = match.group(5) == 'd'
        drop_two_lowest = match.group(5) == 'e'
        threshold = int(match.group(6)) if match.group(6) else None
        
        x = 2 if (drop_lowest or drop_highest) else (int(match.group(1)) if match.group(1) else (3 if drop_two_lowest else 1))
        y = int(match.group(2))
        z = 0
        if match.group(3) and match.group(4):
            z = int(match.group(3) + match.group(4))

        rolls = [random.randint(1, y) for _ in range(x)]
        dropped_rolls = []
        
    rolls = [random.randint(1, y) for _ in range(x)]
    count_of_sixes = rolls.count(6)

    """Drop rolls below the threshold"""
    if threshold is not None:
        for roll in rolls[:]:
            if roll < threshold:
                dropped_rolls.append(roll)
                rolls.remove(roll)

    if drop_lowest and rolls:
        dropped_roll = min(rolls)
        rolls.remove(dropped_roll)
        dropped_rolls.append(dropped_roll)
    elif drop_highest and rolls:
        dropped_roll = max(rolls)
        rolls.remove(dropped_roll)
        dropped_rolls.append(dropped_roll)
    elif drop_two_lowest and len(rolls) > 2:
        for _ in range(2):
            dropped_roll = min(rolls)
            rolls.remove(dropped_roll)
            dropped_rolls.append(dropped_roll)

    total = sum(rolls) + z
    rolls_str = ', '.join(map(str, rolls))
    dropped_str = ', '.join(map(str, dropped_rolls)) if dropped_rolls else None

    """Sends the message"""
    if dropped_str:
        num_dropped = len(dropped_rolls)
        num_remaining = len(rolls)
        sixes_message = ""
        if y == 6:
            sixes_message = f"Dropped: {num_dropped} rolls: {dropped_str}, Remaining: {num_remaining} rolls, Count of 6s: {count_of_sixes}"
        else:
            sixes_message = f"Dropped: {dropped_str}"
        await ctx.send(
            f"Rolled {x}d{y}: [{rolls_str}] + {z} = {total} "
            f"\n({sixes_message})"
            if z else
            f"Rolled {x}d{y}: [{rolls_str}] = {total} "
            f"\n({sixes_message})"
        )
    else:
        await ctx.send(
            f"Rolled {x}d{y}: [{rolls_str}] + {z} = {total}"
            if z else
            f"Rolled {x}d{y}: [{rolls_str}] = {total}"
        )

# Run the bot
bot.run(TOKEN)