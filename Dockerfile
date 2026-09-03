FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
# Deps mirror the PEP 723 block at the top of bot.py.
RUN uv pip install --system --no-cache faster-whisper atproto
COPY bot.py .

# State (out/, audio/, whisper model cache) lives in the container: run without --rm, restart instead of recreate.
ENV TZ=Europe/Prague PYTHONUNBUFFERED=1
CMD ["python", "bot.py", "--loop"]
