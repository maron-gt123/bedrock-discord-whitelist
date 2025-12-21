FROM python:3.12-slim
# コンテナ内の作業ディレクトリ
WORKDIR /app
# 依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/
# 非rootユーザーで実行
RUN useradd -m botuser
USER botuser
CMD ["python", "bot-main.py"]
