FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot-main.py .
COPY config.yaml .
COPY whitelist.json .
COPY allowlist.json .

RUN useradd -m botuser
USER botuser

CMD ["python", "bot-main.py"]
