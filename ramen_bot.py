import discord
from discord.ext import commands
import sqlite3
import os
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# データベース接続
conn = sqlite3.connect("ramen.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS ramen_log (user TEXT, count INTEGER)''')
conn.commit()

# メッセージを監視
@bot.event
async def on_message(message):
    if message.channel.name == "🍜｜ラーメン投稿":
        if message.attachments:
            user = message.author.name
            c.execute("SELECT count FROM ramen_log WHERE user = ?", (user,))
            row = c.fetchone()

            if row:
                new_count = row[0] + 1
                c.execute("UPDATE ramen_log SET count = ? WHERE user = ?", (new_count, user))
            else:
                new_count = 1
                c.execute("INSERT INTO ramen_log (user, count) VALUES (?, ?)", (user, new_count))

            conn.commit()

            # `#📜｜ラーメン一覧` に投稿を転送
            channel = discord.utils.get(message.guild.text_channels, name="📜｜ラーメン一覧")
            if channel:
                await channel.send(f"🍜 {user} さんがラーメンを食べました！ 累計 {new_count} 杯目！")

bot.run(TOKEN)
