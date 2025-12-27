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
def load_config(path="config.yaml"):
    with open(path, "r") as f:
        config = yaml.safe_load(f)

    for env_key, env_val in os.environ.items():
        if not env_key.startswith("CFG_"):
            continue

        keys = env_key[4:].lower().split("_")
        ref = config
        for k in keys[:-1]:
            if k not in ref or not isinstance(ref[k], dict):
                ref[k] = {}
            ref = ref[k]

        if env_val.lower() in ("true", "false"):
            env_val = env_val.lower() == "true"
        elif env_val.isdigit():
            env_val = int(env_val)

        ref[keys[-1]] = env_val

    return config


config = load_config()

BOT_TOKEN = config["bot"]["token"]

server = config["server"]
APPLY_CHANNEL = server["apply_channel"]
APPROVE_CHANNEL = server["approve_channel"]
ADMIN_ROLE = server["admin_role"]

mc = config["minecraft"]
WHITELIST_FILE = mc["whitelist_file"]
ALLOWLIST_FILE = mc["allowlist_file"]

# =====================
# Discord Bot 初期化
# =====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # ★重要
bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)

# =====================
# 内部状態
# =====================
apply_rate_limit = {}  # discord_id -> last_apply_time

# =====================
# JSON ユーティリティ
# =====================
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def load_whitelist():
    return load_json(WHITELIST_FILE, {})


def save_whitelist(data):
    save_json(WHITELIST_FILE, data)


def load_allowlist():
    return load_json(ALLOWLIST_FILE, [])


def save_allowlist(data):
    save_json(ALLOWLIST_FILE, data)


# =====================
# ユーティリティ
# =====================
def is_valid_gamertag(name):
    if not (3 <= len(name) <= 16):
        return False
    return bool(re.match(r"^[A-Za-z0-9 ]+$", name))


def is_admin(member):
    if not isinstance(member, discord.Member):
        return False
    return any(role.name == ADMIN_ROLE for role in member.roles)


# =====================
# help コマンド
# =====================
@bot.command()
async def help(ctx):
    if ctx.guild is None:
        await ctx.send("❌ サーバー内で実行してください")
        return

    lines = [
        "📖 **コマンド一覧**",
        "",
        "👤 **一般ユーザー**",
        "`/apply <Gamertag>`",
        "ホワイトリスト申請を行います",
        "",
        "`/wl_list pending`",
        "申請中の一覧を表示します",
    ]

    if is_admin(ctx.author):
        lines += [
            "",
            "🛠️ **管理者**",
            "`/approve <Gamertag>`",
            "申請を承認します",
            "",
            "`/revoke <Gamertag>`",
            "ホワイトリスト削除",
            "",
            "`/wl_list approved`",
            "承認済み一覧",
        ]

    await ctx.send("\n".join(lines))


# =====================
# 申請
# =====================
@bot.command()
async def apply(ctx, *, gamertag):
    if ctx.channel.id != APPLY_CHANNEL:
        return

    whitelist = load_whitelist()

    now = time.time()
    last = apply_rate_limit.get(ctx.author.id, 0)
    if now - last < 60:
        await ctx.send("⏳ 申請は60秒に1回までです")
        return
    apply_rate_limit[ctx.author.id] = now

    if not is_valid_gamertag(gamertag):
        await ctx.send("❌ Gamertag形式が不正です")
        return

    if gamertag in whitelist:
        await ctx.send("❌ このGamertagはすでに申請されています")
        return

    for entry in whitelist.values():
        if entry["discordId"] == str(ctx.author.id) and entry["status"] == "pending":
            await ctx.send("❌ すでに申請中です")
            return

    whitelist[gamertag] = {
        "discordId": str(ctx.author.id),
        "status": "pending",
    }

    save_whitelist(whitelist)
    await ctx.send(f"✅ 申請受付: **{gamertag}**")


# =====================
# 承認
# =====================
@bot.command()
async def approve(ctx, *, gamertag):
    if ctx.channel.id != APPROVE_CHANNEL:
        return
    if not is_admin(ctx.author):
        await ctx.send("❌ 権限がありません")
        return

    whitelist = load_whitelist()
    allowlist = load_allowlist()

    if gamertag not in whitelist:
        await ctx.send("❌ 申請が見つかりません")
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://playerdb.co/api/player/xbox/{gamertag}"
        ) as resp:
            try:
                data = await resp.json()
                xuid = data["data"]["player"]["id"]
            except Exception:
                await ctx.send("❌ XUID取得失敗")
                return

    if any(e["xuid"] == xuid for e in allowlist):
        await ctx.send("⚠️ すでに登録済みです")
        return

    allowlist.append({"name": gamertag, "xuid": xuid})
    whitelist[gamertag]["status"] = "approved"

    save_allowlist(allowlist)
    save_whitelist(whitelist)

    await ctx.send(f"✅ 承認完了: **{gamertag}**")


# =====================
# 削除
# =====================
@bot.command()
async def revoke(ctx, *, gamertag):
    if ctx.channel.id != APPROVE_CHANNEL:
        return
    if not is_admin(ctx.author):
        await ctx.send("❌ 権限がありません")
        return

    whitelist = load_whitelist()
    allowlist = load_allowlist()

    whitelist.pop(gamertag, None)
    allowlist = [e for e in allowlist if e["name"] != gamertag]

    save_whitelist(whitelist)
    save_allowlist(allowlist)

    await ctx.send(f"🗑️ 削除完了: **{gamertag}**")


# =====================
# 一覧
# =====================
@bot.command(name="wl_list")
async def wl_list(ctx, status: str):
    whitelist = load_whitelist()

    if status not in ("pending", "approved"):
        await ctx.send("❌ `/wl_list pending | approved`")
        return

    if status == "pending" and ctx.channel.id != APPLY_CHANNEL:
        return

    if status == "approved":
        if ctx.channel.id != APPROVE_CHANNEL:
            return
        if not is_admin(ctx.author):
            await ctx.send("❌ 権限がありません")
            return

    items = [
        name for name, data in whitelist.items()
        if data.get("status") == status
    ]

    if not items:
        await ctx.send(f"📭 {status} はありません")
        return

    msg = f"📋 **{status.upper()} 一覧**\n" + "\n".join(f"- {i}" for i in items)
    await ctx.send(msg)


# =====================
# 起動
# =====================
bot.run(BOT_TOKEN)
