# krepice-news

Transcribes new Křepice municipal announcements from rozana.cz with Whisper and posts them to Bluesky.

## Run locally

```sh
uv run bot.py          # process + post new announcements
uv run bot.py --seed   # mark everything currently listed as done (automatic on first run)
```

## Run from GHCR

Long-running container, checks for new announcements every hour at :03 plus a random 0-10 min offset, between 06:00 and 22:00 Prague time.
State (done markers, mp3s, whisper model) stays inside the container, so `docker restart` it, do not recreate it.
First run with no state seeds the current backlog as done instead of posting it.

```sh
docker run -d --name krepice-news --restart unless-stopped \
  -v "$PWD/.app-password:/app/.app-password:ro" \
  ghcr.io/matyaskriz/krepice-news:main
docker logs -f krepice-news
```

`.app-password` holds the Bluesky app password (one line). Image is built and pushed by `.github/workflows/docker.yml` on every push to `main`.
