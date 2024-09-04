import os
import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
from unidecode import unidecode

# Function to get season average stats
def get_season_player_stats(player_name):
    url = f"https://www.basketball-reference.com/leagues/NBA_2024_per_game.html"
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'per_game_stats'})
    df = pd.read_html(str(table))[0]
    player_stats = df.to_dict(orient='records')

    for player in player_stats:
        player_name_clean = unidecode(player['Player']).lower()
        if player_name_clean == unidecode(player_name).lower():
            return player
    return None

# Function to get last n days stats
def get_last_n_days_player_stats(player_name, days):
    if days < 1 or days > 60:
        return None
    url = f"https://www.basketball-reference.com/friv/last_n_days.fcgi?n={days}&type=per_game"
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'players'})
    df = pd.read_html(str(table))[0]
    player_stats = df.to_dict(orient='records')

    for player in player_stats:
        player_name_clean = unidecode(player['Player']).lower()
        if player_name_clean == unidecode(player_name).lower():
            return player
    return None

# Function to fetch last updated information from HTML
def get_last_updated():
    url = 'https://www.basketball-reference.com/?__hstc=213859787.e84c4289f076be841ec545dabc5aaf91.1718911207589.1719521959607.1719530388192.7&__hssc=213859787.3.1719530388192&__hsfp=1399665375'
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        last_updated_paragraph = soup.find('strong', string='Site Last Updated:')

        if last_updated_paragraph:
            last_updated_info = last_updated_paragraph.find_next_sibling(text=True).strip()
            return last_updated_info
        else:
            return None
    else:
        return None

# Discord bot setup
my_secret = os.getenv('TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')

# Function to create stat commands
def create_stat_command(stat_key):
    async def stat_command(ctx, *, args):
        try:
            player_name, days = args.rsplit(maxsplit=1)
            days = int(days)
        except ValueError:
            await ctx.send("Invalid number of days. Please enter a valid number.")
            return

        if days < 1 or days > 60:
            await ctx.send("Number of days must be between 1 and 60.")
            return

        stats = get_last_n_days_player_stats(player_name, days)
        if stats:
            stat_key_upper = stat_key.upper()
            if stat_key_upper in stats:
                stat_message = f"{stat_key_upper} over the last {days} days for {stats['Player']}: {stats[stat_key_upper]}"
                await ctx.send(stat_message)
            else:
                await ctx.send(f"Stat {stat_key_upper} not found for {player_name}.")
        else:
            await ctx.send(f"No stats found for {player_name}.")
    return stat_command

# Add commands for last n days stats
stat_keys = ['fg', '3p', 'pts', 'trb', 'ast', 'stl', 'blk', 'tov']
for stat_key in stat_keys:
    bot_command = create_stat_command(stat_key)
    bot.command(name=f"last_{stat_key}")(bot_command)

# Add commands for season average stats
def create_season_stat_command(stat_key):
    async def stat_command(ctx, *, player_name: str):
        stats = get_season_player_stats(player_name)
        if stats:
            stat_key_upper = stat_key.upper()
            if stat_key_upper in stats:
                stat_message = f"{stat_key_upper} for {stats['Player']}: {stats[stat_key_upper]}"
                await ctx.send(stat_message)
            else:
                await ctx.send(f"Stat {stat_key_upper} not found for {player_name}.")
        else:
            await ctx.send(f"No stats found for {player_name}.")
    return stat_command

# Add commands for season average stats
for stat_key in stat_keys:
    bot_command = create_season_stat_command(stat_key)
    bot.command(name=f"season_{stat_key}")(bot_command)

# Command for comparing season average with last n days stats
@bot.command(name='comparison')
async def comparison(ctx, *, args):
    try:
        player_name, days = args.rsplit(maxsplit=1)
        days = int(days)
    except ValueError:
        await ctx.send("Invalid number of days. Please enter a valid number.")
        return

    if days < 1 or days > 60:
        await ctx.send("Number of days must be between 1 and 60.")
        return

    season_stats = get_season_player_stats(player_name)
    last_n_days_stats = get_last_n_days_player_stats(player_name, days)

    if not season_stats or not last_n_days_stats:
        await ctx.send(f"Stats not found for {player_name}.")
        return

    # Prepare data for plotting
    stats_to_compare = ['PTS', 'AST', 'TRB', 'FG', '3P', 'STL', 'BLK', 'TOV']
    season_values = [float(season_stats.get(stat, 0)) for stat in stats_to_compare]
    last_n_days_values = [float(last_n_days_stats.get(stat, 0)) for stat in stats_to_compare]

    # Create comparison plot with custom colors
    fig, ax = plt.subplots(figsize=(14, 7), facecolor='#313338')
    ax.set_facecolor('#313338')
    x = range(len(stats_to_compare))
    bars_season = ax.bar(x, season_values, width=0.4, label='Season Avg', align='center', color='blue')
    bars_last_n_days = ax.bar([i + 0.4 for i in x], last_n_days_values, width=0.4, label=f'Last {days} Days', align='center', color='green')
    ax.set_xlabel('Statistics', color='white')
    ax.set_ylabel('Values', color='white')
    ax.set_title(f'Comparison of {player_name} Season Avg vs Last {days} Days', color='white')
    ax.set_xticks([i + 0.2 for i in x])
    ax.set_xticklabels(stats_to_compare, color='white')
    ax.tick_params(axis='y', colors='white')
    ax.legend(facecolor='#313338', frameon=False, fontsize='large')
    for text in ax.legend().get_texts():
        text.set_color('black')
    plt.box(False)
    plt.tight_layout()

    # Save plot to a file and send it to Discord
    plt_file = 'comparison_plot.png'
    plt.savefig(plt_file, facecolor='#313338')
    plt.close()

    await ctx.send(file=discord.File(plt_file))

# Command to fetch and display last updated info
@bot.command(name='last_updated')
async def last_updated(ctx):
    last_updated_info = get_last_updated()

    if last_updated_info:
        await ctx.send(f"Stats Last Updated: {last_updated_info}")
    else:
        await ctx.send("Failed to retrieve last updated information.")

# Run the bot
bot.run(my_secret)