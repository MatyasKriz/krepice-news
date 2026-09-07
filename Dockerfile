FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Deps mirror the PEP 723 block at the top of bot.py.
RUN uv pip install --system --no-cache faster-whisper atproto
COPY bot.py /app/bot.py

# All state lives under /data: out/ (done markers), audio/ (mp3s), hf/ (whisper model), .app-password.
# Mount it, and the image can be replaced freely.
WORKDIR /data
VOLUME /data
ENV TZ=Europe/Prague PYTHONUNBUFFERED=1 HF_HOME=/data/hf
CMD ["python", "/app/bot.py", "--loop"]
