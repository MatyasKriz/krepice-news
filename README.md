# krepice-news

Transcribes new Křepice municipal announcements from rozana.cz with Whisper and posts them to Bluesky.

## Run locally

```sh
uv run bot.py          # process + post new announcements
uv run bot.py --seed   # mark everything currently listed as done
```

## Run from GHCR

```sh
docker run --rm \
  -v "$PWD/out:/app/out" \
  -v "$PWD/audio:/app/audio" \
  -v "$PWD/.app-password:/app/.app-password:ro" \
  -v krepice-hf:/root/.cache/huggingface \
  ghcr.io/matyaskriz/krepice-news:main
```

`.app-password` holds the Bluesky app password (one line). Image is built and pushed by `.github/workflows/docker.yml` on every push to `main` and on `v*` tags.
