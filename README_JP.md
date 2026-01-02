# 📝 Bedrock Discord Whitelist Bot

この Bot は **Minecraft Bedrock Edition** サーバーのホワイトリスト管理を **Discord を通じて簡単に行うため**のものです。  
ユーザーは Discord 上で申請を行い、管理者が承認することでサーバーに参加可能になります。

> ⚠️ 本 Bot は **Kubernetes 上で Bedrock サーバーを運用している環境を前提** に作られています。  
> Bedrock サーバーへのコマンド送信は `kubectl exec` を直接使用します。

---

## 🌟 特徴

- Discord でホワイトリストの申請・承認・削除・一覧確認が可能  
- 申請は **60 秒に 1 回の制限付き**  
- Minecraft Bedrock サーバーへのコマンド送信は **Kubernetes exec 直経由**  
- **PlayerDB API** を使用して Gamertag から XUID を自動取得  
- 管理者は `/approve` `/revoke` `/reload` コマンドで簡単操作  
- Docker イメージとしても提供されており、簡単にデプロイ可能 

---

## 🖥 動作環境

- Python 3.10 以上（Docker イメージ利用時は不要）  
- Discord Bot Token  
- Kubernetes 上の Bedrock サーバー  

必要な環境変数:

| 環境変数 | 説明 |
|-----------|------|
| `BOT_TOKEN` | Discord Bot Token |
| `APPLY_CHANNEL` | 申請用チャンネルID |
| `APPROVE_CHANNEL` | 承認用チャンネルID |
| `ADMIN_ROLE` | 管理者ロールID |
| `BEDROCK_NAMESPACE` | Bedrock Pod が存在する Kubernetes Namespace |
| `BEDROCK_POD` | Bedrock Pod 名 |
| `BEDROCK_CONTAINER` | （必要な場合）コンテナ名 |

---

## ⚙️ インストール / デプロイ

### Docker Hub を利用する場合

Docker Hub に公開されているイメージを利用すれば、環境構築や pip インストールは不要です。  
環境変数を設定してコンテナを起動するだけで動作します。

```bash
docker run -d \
  -e BOT_TOKEN="your_token" \
  -e APPLY_CHANNEL=1234567890 \
  -e APPROVE_CHANNEL=1234567890 \
  -e ADMIN_ROLE=1234567890 \
  -e BEDROCK_NAMESPACE="minecraft" \
  -e BEDROCK_POD="bedrock-server" \
  maron/bedrock-discord-whitelist:latest
```

### ローカルでソースを使う場合

```bash
git clone https://github.com/maron-gt123/bedrock-discord-whitelist.git
cd bedrock-discord-whitelist
pip install -r requirements.txt
python bot.py
```

## 💬 コマンド一覧

### 👤 一般ユーザー

| コマンド | 説明 |
|-----------|------|
| `/apply <Gamertag>` | ホワイトリスト申請 |
| `/wl_list pending` | 申請中の一覧を表示 |

### 🛠 管理者

| コマンド | 説明 |
|-----------|------|
| `/approve <Gamertag>` | 申請を承認 |
| `/revoke <Gamertag>` | ホワイトリスト削除 |
| `/wl_list approved` | 承認済み一覧を表示 |
| `/reload` | Bedrock allowlist を再読み込み |

---

## ⚠️ 注意点

- Gamertag は **3〜16 文字、英数字とスペースのみ**  
- 申請は **1 分に 1 回まで**  
- 管理者権限のないユーザーは `/approve` や `/revoke` を使用できません  
- Kubernetes exec が失敗すると Bedrock へのコマンド送信はできません  

---

## 📌 参考

- Kubernetes exec を使って Bedrock コマンド送信  
- Discord Bot の権限管理（チャンネル・ロール）に対応
- Docker Hub イメージ: [Docker Hub](https://hub.docker.com/r/marongt123/bedrock-discord-whitelist)
