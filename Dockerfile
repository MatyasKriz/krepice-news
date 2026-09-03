FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
# Deps mirror the PEP 723 block at the top of bot.py.
RUN uv pip install --system --no-cache faster-whisper atproto
COPY bot.py .

# Persist across runs: out/ (done markers), audio/ (mp3s), .app-password, whisper model cache.
VOLUME ["/app/out", "/app/audio", "/root/.cache/huggingface"]

CMD ["python", "bot.py"]
