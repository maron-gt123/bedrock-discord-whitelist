# 📝 Bedrock Discord Whitelist Bot

この Bot は **Minecraft Bedrock Edition** サーバーのホワイトリスト管理を **Discord を通じて簡単に行うため**のものです。  
ユーザーは Discord 上で申請を行い、管理者が承認することでサーバーに参加可能になります。

---

## 🌟 特徴

- Discord でホワイトリストの申請・承認・削除・一覧確認が可能  
- 申請は **60 秒に 1 回の制限付き**  
- Minecraft Bedrock サーバーへのコマンド送信は **Kubernetes exec 経由**  
- **PlayerDB API** を使用して Gamertag から XUID を自動取得  
- 管理者は `/approve` `/revoke` `/reload` コマンドで簡単操作  

---

## 🖥 動作環境

- Python 3.10 以上  
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

## ⚙️ インストール

```bash
git clone https://github.com/maron-gt123/bedrock-discord-whitelist.git
cd bedrock-discord-whitelist
pip install -r requirements.txt
