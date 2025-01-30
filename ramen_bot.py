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

# データベース接続
conn = sqlite3.connect("ramen.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS ramen_log (user TEXT, count INTEGER)''')
conn.commit()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user = message.author.name  # 発言者の名前

    # 🔍 デバッグ用ログ
    print(f"受信メッセージ: {message.content}")

    # 🏷️ **「{ユーザー名} さん下げて」の処理**
    match = re.match(r"^([\w\.-]+)さん下げて$", message.content)
    if match:
        target_user = match.group(1).strip()  # 指定されたユーザー名
        print(f"ターゲットユーザー（指定）: {target_user}")  # デバッグ用出力

        c.execute("SELECT count FROM ramen_log WHERE user = ?", (target_user,))
        row = c.fetchone()

        if row and row[0] > 0:
            new_count = row[0] - 1
            c.execute("UPDATE ramen_log SET count = ? WHERE user = ?", (new_count, target_user))
            conn.commit()
            await message.channel.send(f"📉 {target_user} さんのラーメンカウントを 1 減らしました！（現在 {new_count} 杯）")
        else:
            await message.channel.send(f"⚠️ {target_user} さんのカウントはすでに 0 です！")

    # 🏷️ **ラーメン投稿の処理**
    if message.channel.name == "🍜｜ラーメン投稿":
        content = message.content.split("\n")

        store_name, ramen_name, location, customization, review, rating = None, "不明", "不明", "なし", "なし", None
        for line in content:
            if line.startswith("📍 店舗名:"):
                store_name = line.replace("📍 店舗名:", "").strip()
            elif line.startswith("🍜 ラーメン名:"):
                ramen_name = line.replace("🍜 ラーメン名:", "").strip()
            elif line.startswith("🏠 場所:"):
                location = line.replace("🏠 場所:", "").strip()
            elif line.startswith("🍳 カスタマイズ:"):
                customization = line.replace("🍳 カスタマイズ:", "").strip()
            elif line.startswith("📝 感想:"):
                review = line.replace("📝 感想:", "").strip()
            elif line.startswith("⭐ 評価:"):
                rating_text = line.replace("⭐ 評価:", "").strip()
                if rating_text.isdigit():
                    rating = int(rating_text)
                    if rating < 1 or rating > 5:
                        await message.channel.send(f"⚠️ {user} さん、評価は 1 〜 5 の間で入力してください！")
                        return
                else:
                    await message.channel.send(f"⚠️ {user} さん、評価は 1 〜 5 の数字で入力してください！")
                    return

        image_url = None
        if message.attachments:
            image_url = message.attachments[0].url  # 投稿された画像のURLをそのまま取得

        # 🔴 **画像と店舗名がない場合、カウント & 転送しない**
        if not store_name or not image_url:
            await message.channel.send(f"⚠️ {user} さん、店舗名と画像が必要です！投稿がカウントされません。")
            return

        # 星の表示（⭐️ の数を調整）
        star_rating = "⭐️" * rating if rating else "評価なし"

        # データベースに投稿数を記録
        c.execute("SELECT count FROM ramen_log WHERE user = ?", (user,))
        row = c.fetchone()

        new_count = row[0] + 1 if row else 1
        if row:
            c.execute("UPDATE ramen_log SET count = ? WHERE user = ?", (new_count, user))
        else:
            c.execute("INSERT INTO ramen_log (user, count) VALUES (?, ?)", (user, new_count))
        conn.commit()

        # `#📜｜ラーメン一覧` に投稿
        channel = discord.utils.get(message.guild.text_channels, name="📜｜ラーメン一覧")
        if channel:
            embed = discord.Embed(title="🍜 新しいラーメン投稿！", color=discord.Color.gold())
            embed.add_field(name="📍 店舗名", value=store_name, inline=True)
            embed.add_field(name="🍜 ラーメン名", value=ramen_name, inline=True)
            embed.add_field(name="🏠 場所", value=location, inline=False)
            embed.add_field(name="🍳 カスタマイズ", value=customization, inline=False)
            embed.add_field(name="📝 感想", value=review, inline=False)
            embed.add_field(name="⭐ 評価", value=star_rating, inline=True)
            embed.set_footer(text=f"投稿者: {user} | 累計 {new_count} 杯目")

            # **画像がある場合、そのまま Discord に送信**
            if image_url:
                embed.set_image(url=image_url)
            
            await channel.send(embed=embed)

bot.run(TOKEN)
