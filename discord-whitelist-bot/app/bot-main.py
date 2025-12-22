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
apply_rate_limit = {}  # discord_id -> last_apply_time

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
    os.replace(tmp, path)

def is_valid_gamertag(name):
    # Xbox Gamertag 想定
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
    if ctx.channel.id != APPLY_CHANNEL:
        return

    now = time.time()
    last = apply_rate_limit.get(ctx.author.id, 0)
    if now - last < 60:
        await ctx.send("⏳ 申請は60秒に1回までです")
        return
    apply_rate_limit[ctx.author.id] = now

    if not is_valid_gamertag(gamertag):
        await ctx.send("❌ Gamertag形式が不正です（3〜16文字、英数字とスペースのみ）")
        return

    for entry in whitelist.values():
        if entry["discordId"] == str(ctx.author.id) and entry["status"] == "pending":
            await ctx.send("❌ すでに申請中です")
            return

    if gamertag in whitelist:
        await ctx.send("❌ このGamertagはすでに申請されています")
        return

    whitelist[gamertag] = {
        "discordId": str(ctx.author.id),
        "status": "pending"
    }
    save_json(WHITELIST_FILE, whitelist)

    await ctx.send(f"✅ 申請受付: **{gamertag}**\n承認をお待ちください")

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

    # XUID を取得
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://playerdb.co/api/player/xbox/{gamertag}") as resp:
            try:
                data = await resp.json()
                xuid = data["data"]["player"]["id"]
            except Exception:
                await ctx.send(f"❌ XUID取得失敗: {gamertag}")
                return

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
# 一覧表示コマンド
# =====================
@bot.command()
async def list(ctx, status: str):
    if status not in ["pending", "approved"]:
        await ctx.send("❌ 使い方: `/list pending` または `/list approved`")
        return

    if status == "pending" and ctx.channel.id != APPLY_CHANNEL:
        return

    if status == "approved":
        if ctx.channel.id != APPROVE_CHANNEL:
            return
        if not is_admin(ctx.author):
            await ctx.send("❌ 権限がありません")
            return

    items = []
    for gamertag, data in whitelist.items():
        if data.get("status") == status:
            items.append(gamertag)

    if not items:
        await ctx.send(f"📭 {status} の申請はありません")
        return

    message = f"📋 **{status.upper()} 一覧**\n"
    for name in items:
        message += f"- {name}\n"

    await ctx.send(message)

# =====================
# 起動
# =====================
bot.run(BOT_TOKEN)
