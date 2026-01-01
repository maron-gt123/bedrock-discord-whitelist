FROM python:3.12-slim
# コンテナ内の作業ディレクトリ
WORKDIR /app

# kubectl install（root 権限で）
RUN apt-get update && apt-get install -y curl ca-certificates \
 && curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl \
 && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
 && rm kubectl \
 && apt-get clean

# stage1 から send-command をコピー
COPY --from=bedrock /usr/local/bin/send-command /usr/local/bin/send-command
RUN chmod +x /usr/local/bin/send-command

# 依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/
# 非rootユーザーで実行
RUN useradd -m botuser
USER botuser
CMD ["python", "bot-main.py"]
