# bedrock-discord-whitelist

Minecraft 統合版（Bedrock Dedicated Server）向けの  
**Discord ベース・ホワイトリスト管理 Bot** です。

Discord 上で申請 → 管理者承認 → `allowlist.json` 反映  
という流れを **安全に・シンプルに** 運用できます。

---

## 特徴

- 🧾 Discord からホワイトリスト申請
- ✅ 管理者による承認 / 削除
- 🔐 攻撃・誤操作を考慮した安全設計
- 🧠 JSON ベース（DB 不要）
- 🐍 Python 製（discord.py）
- ☸ Kubernetes / 自宅サーバー運用と相性◎

---

## 想定ユースケース

- 自宅運用の Bedrock Dedicated Server
- 身内・小〜中規模コミュニティ
- Geyser 未使用（統合版専用）
- Discord を入口にした参加管理

---

## 全体フロー

```text
[参加者]
  ↓ Discord
/apply Gamertag
  ↓
[Bot]
  - 形式チェック
  - レート制限
  - pending 登録
  ↓
[管理者]
/approve Gamertag
  ↓
[Bot]
  - XUID取得
  - allowlist.json 更新
