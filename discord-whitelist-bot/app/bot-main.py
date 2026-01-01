import discord
from discord.ext import commands
import json
import aiohttp
import subprocess
import os
import time
import re

# =====================
# 変数
# =====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
APPLY_CHANNEL = int(os.environ.get("APPLY_CHANNEL", 0))
APPROVE_CHANNEL = int(os.environ.get("APPROVE_CHANNEL", 0))
ADMIN_ROLE = int(os.environ.get("ADMIN_ROLE", 0))
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
apply_rate_limit = {}  # discord_id -> last_apply_time

# =====================
# JSON ユーティリティ（Stale handle 回避）
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
    # ファイル新規作成
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(default, f, indent=2)
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # NFS の Stale handle 回避のため直接上書き
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
# Bedrock コマンド送信（kubectl exec + send-command）
# =====================
def bedrock_cmd(*args) -> bool:
    """
    Bedrock サーバにコマンドを送信する
    例: bedrock_cmd("allowlist", "reload")
    """
    try:
        cmd = [
            "kubectl", "exec", "-n", "mc-haramis", "mc-bedrock-0",
            "--", "send-command", *args
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode == 0:
            return True
        return False
    except Exception as e:
        print(f"[ERROR] Bedrock command failed: {e}")
        return False

# =====================
# ユーティリティ
# =====================
def is_valid_gamertag(name):
    if not (3 <= len(name) <= 16):
        return False
    return bool(re.match(r"^[A-Za-z0-9 ]+$", name))

# =====================
# チャンネル・権限ユーティリティ
# =====================
def is_admin(member):
    return any(role.id == ADMIN_ROLE for role in member.roles)

def check_channel(ctx, command_type):
    if command_type == "apply":
        return ctx.channel.id == APPLY_CHANNEL
    if command_type in ("approve", "revoke", "wl_list_approved"):
        return ctx.channel.id == APPROVE_CHANNEL
    if command_type == "wl_list_pending":
        return ctx.channel.id in (APPLY_CHANNEL, APPROVE_CHANNEL)
    return False

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
            "ホワイトリスト削除します",
            "",
            "`/wl_list approved`",
            "承認済み一覧を表示します",
            "",
            "`/reload`",
            "Bedrock allowlist を再読み込みします",
        ]

    await ctx.send("\n".join(lines))

# =====================
# 申請
# =====================
@bot.command()
async def apply(ctx, *, gamertag):
    if not check_channel(ctx, "apply"):
        await ctx.send("❌ 申請用チャンネルで実行してください")
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
    if not check_channel(ctx, "approve"):
        await ctx.send("❌ 承認用チャンネルで実行してください")
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
        async with session.get(f"https://playerdb.co/api/player/xbox/{gamertag}") as resp:
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
    if not check_channel(ctx, "revoke"):
        await ctx.send("❌ 承認用チャンネルで実行してください")
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

    if status == "pending" and not check_channel(ctx, "wl_list_pending"):
        await ctx.send("❌ このチャンネルでは実行できません")
        return

    if status == "approved" and not check_channel(ctx, "wl_list_approved"):
        if not is_admin(ctx.author):
            await ctx.send("❌ 権限がありません")
            return
        await ctx.send("❌ このチャンネルでは実行できません")
        return

    items = [name for name, data in whitelist.items() if data.get("status") == status]

    if not items:
        await ctx.send(f"📭 {status} はありません")
        return

    msg = f"📋 **{status.upper()} 一覧**\n" + "\n".join(f"- {i}" for i in items)
    await ctx.send(msg)

# =====================
# allowlist reload
# =====================
@bot.command()
async def reload(ctx):
    if not check_channel(ctx, "approve"):
        await ctx.send("❌ 管理用チャンネルで実行してください")
        return

    if not is_admin(ctx.author):
        await ctx.send("❌ 権限がありません")
        return

    ok = bedrock_cmd("allowlist reload")

    if ok:
        await ctx.send("🔄 allowlist reload を実行しました")
    else:
        await ctx.send("❌ Bedrock へのコマンド送信に失敗しました")

# =====================
# 起動
# =====================
bot.run(BOT_TOKEN)
