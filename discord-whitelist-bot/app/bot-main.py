import discord
from discord.ext import commands
import json
import aiohttp
import subprocess
import os
import time
import re

# =====================
# 言語ロード
# =====================
BOT_LANG = os.environ.get("BOT_LANG", "ja")
with open(f"./lang/{BOT_LANG}.json", "r", encoding="utf-8") as f:
    MESSAGES = json.load(f)

# =====================
# 環境変数・設定
# =====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
APPLY_CHANNEL = int(os.environ.get("APPLY_CHANNEL", 0))
APPROVE_CHANNEL = int(os.environ.get("APPROVE_CHANNEL", 0))
ADMIN_ROLE = int(os.environ.get("ADMIN_ROLE", 0))
BEDROCK_NAMESPACE = os.environ.get("BEDROCK_NAMESPACE")
BEDROCK_POD = os.environ.get("BEDROCK_POD")
BEDROCK_CONTAINER = os.environ.get("BEDROCK_CONTAINER", "")
WHITELIST_FILE = "/app/data/whitelist.json"
ALLOWLIST_FILE = "/app/data/allowlist.json"

# =====================
# Discord Bot 初期化
# =====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)

# =====================
# 内部状態
# =====================
apply_rate_limit = {}

# =====================
# JSON ユーティリティ
# =====================
def safe_load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                if isinstance(default, list) and not isinstance(data, list):
                    data = []
                elif isinstance(default, dict) and not isinstance(data, dict):
                    data = {}
                return data
    except (OSError, json.JSONDecodeError):
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(default, f, indent=2)
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_whitelist():
    return safe_load_json(WHITELIST_FILE, {})

def save_whitelist(data):
    save_json(WHITELIST_FILE, data)

def load_allowlist():
    return safe_load_json(ALLOWLIST_FILE, [])

def save_allowlist(data):
    save_json(ALLOWLIST_FILE, data)

# =====================
# Bedrock コマンド送信
# =====================
def bedrock_cmd(*args) -> bool:
    if not BEDROCK_POD:
        print("[ERROR] BEDROCK_POD is not set")
        return False

    exec_cmd = [
        "kubectl", "exec",
        "-n", BEDROCK_NAMESPACE,
        BEDROCK_POD,
    ]
    if BEDROCK_CONTAINER:
        exec_cmd += ["-c", BEDROCK_CONTAINER]

    exec_cmd += ["--", "send-command", *args]

    result = subprocess.run(exec_cmd, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    return result.returncode == 0

# =====================
# ユーティリティ
# =====================
def is_valid_gamertag(name):
    return bool(re.match(r"^[A-Za-z0-9 ]{3,16}$", name))

def is_admin(member):
    return any(role.id == ADMIN_ROLE for role in member.roles)

def check_channel(ctx, command_type):
    if command_type in ("apply", "wl_list_pending"):
        return ctx.channel.id == APPLY_CHANNEL
    if command_type in ("approve", "revoke", "wl_list_approved", "reload"):
        return ctx.channel.id == APPROVE_CHANNEL
    return False

# =====================
# /wl help
# =====================
@bot.command(name="wl_help")
async def wl_help(ctx):
    """
    /wl help でコマンド一覧表示
    """
    lines = [
        MESSAGES["user_section"],
        MESSAGES["help_apply"],
        MESSAGES["help_pending"],
    ]

    if is_admin(ctx.author):
        lines += [
            "",
            MESSAGES["admin_section"],
            MESSAGES["help_approve"],
            MESSAGES["help_revoke"],
            MESSAGES["help_list_approved"],
            MESSAGES["help_reload"],
        ]

    await ctx.send("\n".join(lines))

# =====================
# /apply <Gamertag>
# =====================
@bot.command()
async def apply(ctx, *, gamertag):
    if not check_channel(ctx, "apply"):
        await ctx.send(MESSAGES["apply_channel_error"])
        return

    # 形式チェック
    if not is_valid_gamertag(gamertag):
        await ctx.send(MESSAGES["invalid_gamertag"])
        return

    # PlayerDB で存在確認
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://playerdb.co/api/player/xbox/{gamertag}") as resp:
                data = await resp.json()
                if not data.get("data") or not data["data"].get("player"):
                    await ctx.send(MESSAGES["gamertag_not_found"].format(gamertag=gamertag))
                    return
        except Exception:
            await ctx.send(MESSAGES["xuid_fail"])
            return

    # レート制限・重複申請
    whitelist = load_whitelist()
    now = time.time()
    last = apply_rate_limit.get(ctx.author.id, 0)
    if now - last < 60:
        await ctx.send(MESSAGES["rate_limit"])
        return
    apply_rate_limit[ctx.author.id] = now

    if gamertag in whitelist:
        await ctx.send(MESSAGES["already_applied"])
        return

    for entry in whitelist.values():
        if entry["discordId"] == str(ctx.author.id) and entry["status"] == "pending":
            await ctx.send(MESSAGES["already_pending"])
            return

    # 申請登録
    whitelist[gamertag] = {"discordId": str(ctx.author.id), "status": "pending"}
    save_whitelist(whitelist)
    await ctx.send(MESSAGES["apply_success"].format(gamertag=gamertag))

# =====================
# /approve <Gamertag>
# =====================
@bot.command()
async def approve(ctx, *, gamertag):
    if not check_channel(ctx, "approve"):
        await ctx.send(MESSAGES["approve_channel_error"])
        return
    if not is_admin(ctx.author):
        await ctx.send(MESSAGES["no_permission"])
        return

    whitelist = load_whitelist()
    allowlist = load_allowlist()

    if gamertag not in whitelist:
        await ctx.send(MESSAGES["not_found"])
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://playerdb.co/api/player/xbox/{gamertag}") as resp:
            try:
                data = await resp.json()
                xuid = data["data"]["player"]["id"]
            except Exception:
                await ctx.send(MESSAGES["xuid_fail"])
                return

    if any(e["xuid"] == xuid for e in allowlist):
        await ctx.send(MESSAGES["already_registered"])
        return

    allowlist.append({"name": gamertag, "xuid": xuid})
    whitelist[gamertag]["status"] = "approved"

    save_allowlist(allowlist)
    save_whitelist(whitelist)
    await ctx.send(MESSAGES["approve_success"].format(gamertag=gamertag))

# =====================
# /revoke <Gamertag>
# =====================
@bot.command()
async def revoke(ctx, *, gamertag):
    if not check_channel(ctx, "revoke"):
        await ctx.send(MESSAGES["approve_channel_error"])
        return
    if not is_admin(ctx.author):
        await ctx.send(MESSAGES["no_permission"])
        return

    whitelist = load_whitelist()
    allowlist = load_allowlist()

    whitelist.pop(gamertag, None)
    allowlist = [e for e in allowlist if e["name"] != gamertag]

    save_whitelist(whitelist)
    save_allowlist(allowlist)
    await ctx.send(MESSAGES["revoke_success"].format(gamertag=gamertag))

# =====================
# /wl_list pending | approved
# =====================
@bot.command(name="wl_list")
async def wl_list(ctx, status: str):
    whitelist = load_whitelist()
    if status not in ("pending", "approved"):
        await ctx.send(f"❌ `/wl_list pending | approved`")
        return

    if status == "pending" and not check_channel(ctx, "wl_list_pending"):
        await ctx.send(MESSAGES["apply_channel_error"])
        return

    if status == "approved" and not check_channel(ctx, "wl_list_approved"):
        if not is_admin(ctx.author):
            await ctx.send(MESSAGES["no_permission"])
            return
        await ctx.send(MESSAGES["approve_channel_error"])
        return

    items = [name for name, data in whitelist.items() if data.get("status") == status]
    if not items:
        await ctx.send(MESSAGES["list_empty"].format(status=status))
        return

    msg = f"📋 **{status.upper()} List**\n" + "\n".join(f"- {i}" for i in items)
    await ctx.send(msg)

# =====================
# /reload
# =====================
@bot.command()
async def reload(ctx):
    if not check_channel(ctx, "reload"):
        await ctx.send(MESSAGES["approve_channel_error"])
        return
    if not is_admin(ctx.author):
        await ctx.send(MESSAGES["no_permission"])
        return

    ok = bedrock_cmd("allowlist reload")
    if ok:
        await ctx.send(MESSAGES["reload_success"])
    else:
        await ctx.send(MESSAGES["reload_fail"])

# =====================
# 起動
# =====================
bot.run(BOT_TOKEN)
