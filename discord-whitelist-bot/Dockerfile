# ---------- stage 1: send-command を取得 ----------
FROM itzg/minecraft-bedrock-server AS bedrock
# ---------- stage 2: discord bot ----------
FROM python:3.12-slim
# コンテナ内の作業ディレクトリ
WORKDIR /app
# send-command をコピー
COPY --from=bedrock /usr/local/bin/send-command /usr/local/bin/send-command
# 実行権限を付与
RUN chmod +x /usr/local/bin/send-command
# 依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/
# 非rootユーザーで実行
RUN useradd -m botuser
USER botuser
CMD ["python", "bot-main.py"]
