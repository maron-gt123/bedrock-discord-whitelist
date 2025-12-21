import discord
from discord.ext import commands
import json
import aiohttp
import os
import yaml
import time
import re

# =====================
# config 読み込み
# =====================
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

BOT_TOKEN = config['bot']['token']
server = config['server']

APPLY_CHANNEL = server['apply_channel']
APPROVE_CHANNEL = server['approve_channel']
ADMIN_ROLE = server['admin_role']
WHITELIST_FILE = server['whitelist_file']
ALLOWLIST_FILE = server['allowlist_file']

# =====================
# Discord Bot 初期化
# =====================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# =====================
# 内部状態
# =====================
apply_rate_limit = {}   # discord_id -> last_apply_time

# =====================
# ユーティリティ
# =====================
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)  # 原子的に置き換え

def is_valid_gamertag(name):
    # Xbox Gamertag想定
    # 3〜16文字 / 英数字 + スペース
    if not (3 <= len(name) <= 16):
        return False
    if not re.match(r'^[A-Za-z0-9 ]+$', name):
        return False
    return True

def is_admin(member):
    return any(role.name == ADMIN_ROLE for role in member.roles)

# =====================
# データ読み込み
# =====================
whitelist = load_json(WHITELIST_FILE, {})
allowlist = load_json(ALLOWLIST_FILE, [])

# =====================
# 申請コマンド
# =====================
@bot.command()
async def apply(ctx, *, gamertag):
    # チャンネル制限
    if ctx.channel.id != APPLY_CHANNEL:
        return

    now = time.time()

    # レート制限（60秒）
    last = apply_rate_limit.get(ctx.author.id, 0)
    if now - last < 60:
        await ctx.send("⏳ 申請は60秒に1回までです")
        return
    apply_rate_limit[ctx.author.id] = now

    # Gamertag検証
    if not is_valid_gamertag(gamertag):
        await ctx.send("❌ Gamertag形式が不正です（3〜16文字、英数字とスペースのみ）")
        return

    # 既存申請チェック（1人1件）
    for entry in whitelist.values():
        if entry["discordId"] == str(ctx.author.id) and entry["status"] == "pending":
            await ctx.send("❌ すでに申請中です")
            return

    # 同名申請チェック
    if gamertag in whitelist:
        await ctx.send("❌ このGamertagはすでに申請されています")
        return

    whitelist[gamertag] = {
        "discordId": str(ctx.author.id),
        "status": "pending"
    }
    save_json(WHITELIST_FILE, whitelist)

    await ctx.send(f"📩 申請受付: **{gamertag}**\n承認をお待ちください")

# =====================
# 承認コマンド
# =====================
@bot.command()
async def approve(ctx, *, gamertag):
    if ctx.channel.id != APPROVE_CHANNEL:
        return
    if not is_admin(ctx.author):
        await ctx.send("❌ 権限がありません")
        return
    if gamertag not in whitelist:
        await ctx.send("❌ 申請が見つかりません")
        return

    # XUID取得
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://playerdb.co/api/player/xbox/{gamertag}") as resp:
            try:
                data = await resp.json()
                xuid = data["data"]["player"]["id"]
            except Exception:
                await ctx.send(f"❌ XUID取得失敗: {gamertag}")
                return

    # allowlist 重複防止
    if any(e["xuid"] == xuid for e in allowlist):
        await ctx.send("⚠️ すでに登録済みのXUIDです")
        return

    allowlist.append({
        "name": gamertag,
        "xuid": xuid
    })
    save_json(ALLOWLIST_FILE, allowlist)

    whitelist[gamertag]["status"] = "approved"
    save_json(WHITELIST_FILE, whitelist)

    await ctx.send(f"✅ 承認完了: **{gamertag}**")

# =====================
# 削除コマンド
# =====================
@bot.command()
async def revoke(ctx, *, gamertag):
    if ctx.channel.id != APPROVE_CHANNEL:
        return
    if not is_admin(ctx.author):
        await ctx.send("❌ 権限がありません")
        return

    whitelist.pop(gamertag, None)
    save_json(WHITELIST_FILE, whitelist)

    global allowlist
    allowlist = [e for e in allowlist if e["name"] != gamertag]
    save_json(ALLOWLIST_FILE, allowlist)

    await ctx.send(f"🗑️ 削除完了: **{gamertag}**")

# =====================
# 起動
# =====================
bot.run(BOT_TOKEN)
