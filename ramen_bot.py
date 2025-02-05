import discord
from discord.ext import commands
import sqlite3
import os
import re
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# データベースの初期設定
def init_db():
    with sqlite3.connect("ramen.db") as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS ramen_log (user TEXT, count INTEGER)''')
        conn.commit()

init_db()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # 自分のメッセージは無視

    user = message.author.name  
    user_mention = message.author.mention  

    # 🔹「さん下げて」コマンドの処理
    match = re.match(r"^(.+?)さん下げて$", message.content)
    if match:
        target_user = match.group(1).strip()
        with sqlite3.connect("ramen.db") as conn:
            c = conn.cursor()
            c.execute("SELECT count FROM ramen_log WHERE user = ?", (target_user,))
            row = c.fetchone()

            if row and row[0] > 0:
                new_count = row[0] - 1
                c.execute("UPDATE ramen_log SET count = ? WHERE user = ?", (new_count, target_user))
                conn.commit()
                await message.channel.send(f"📉 {target_user} さんのラーメンカウントを 1 減らしました！（現在 {new_count} 杯）")
            else:
                await message.channel.send(f"⚠️ {target_user} さんのカウントはすでに 0 です！")
        return

    # 🏷️ ラーメン投稿の処理（フォーマット外は無視）
    if message.channel.name == "🍜｜ラーメン投稿":
        content = message.content

        # **フォーマットチェック**
        if not re.search(r"📍 店舗名:", content) or not re.search(r"🍜 ラーメン名:", content):
            return  # **フォーマットが違うメッセージは無視！**

        match = re.search(
            r"📍 店舗名:\s*(.*?)\n?"
            r"(?:🍜 ラーメン名:\s*(.*?)\n?)?"
            r"(?:🏠 場所:\s*(.*?)\n?)?"
            r"(?:🍳 カスタマイズ:\s*(.*?)\n?)?"
            r"(?:📝 感想:\s*\n?(.*?))?"
            r"(?:⭐ 評価:\s*(.*?))?",
            content,
            re.DOTALL
        )

        if not match:
            return  # **フォーマットが崩れている場合は無視！**

        # **各項目を取得**
        store_name = match.group(1).strip() if match.group(1) else "不明"
        ramen_name = match.group(2).strip() if match.group(2) else "不明"
        location = match.group(3).strip() if match.group(3) else "不明"
        customization = match.group(4).strip() if match.group(4) else "なし"
        review = match.group(5).strip() if match.group(5) else "なし"
        rating_text = match.group(6).strip() if match.group(6) else None

        # **評価のチェック**
        if rating_text and rating_text.isdigit():
            rating = int(rating_text)
            if rating < 1 or rating > 5:
                await message.channel.send(f"⚠️ {user} さん、評価は 1 〜 5 の間で入力してください！")
                return
        else:
            rating = None

        # **画像チェック**
        image_url = message.attachments[0].url if message.attachments else None
        if not image_url:
            await message.delete()
            try:
                await message.author.send(f"⚠️ {user} さん、店舗名と画像が必要です！投稿が削除されました。")
            except discord.errors.Forbidden:
                print(f"DMが送れませんでした: {user}")
            return

        # **データベースに記録**
        with sqlite3.connect("ramen.db") as conn:
            c = conn.cursor()
            c.execute("SELECT count FROM ramen_log WHERE user = ?", (user,))
            row = c.fetchone()
            new_count = row[0] + 1 if row else 1
            if row:
                c.execute("UPDATE ramen_log SET count = ? WHERE user = ?", (new_count, user))
            else:
                c.execute("INSERT INTO ramen_log (user, count) VALUES (?, ?)", (user, new_count))
            conn.commit()

        # **フォーマットを整形**
        store_name = f"📍 店舗名: {store_name}\n"
        ramen_name = f"🍜 ラーメン名: {ramen_name}\n"
        location = f"🏠 場所: {location}\n"
        customization = f"🍳 カスタマイズ: {customization}\n"
        review = f"📝 感想: {review}\n"
        rating_text = f"⭐ 評価: {'⭐️' * rating}\n" if rating else "⭐ 評価: なし\n"
        footer_text = f"投稿者: {user_mention} | 累計 {new_count} 杯目"

        embed_description = f"{store_name}\n{ramen_name}\n{location}\n{customization}\n{review}\n{rating_text}\n{footer_text}"
        embed = discord.Embed(description=embed_description, color=discord.Color.gold())

        if image_url:
            embed.set_image(url=image_url)

        # **ラーメン一覧チャンネルへ送信**
        channel = discord.utils.get(message.guild.text_channels, name="📜｜ラーメン一覧")
        if channel:
            await channel.send(embed=embed)

    # **他のコマンドを正しく処理するための記述**
    await bot.process_commands(message)

bot.run(TOKEN)
