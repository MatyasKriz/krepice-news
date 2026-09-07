# krepice-news

Transcribes new Křepice municipal announcements from rozana.cz with Whisper and posts them to Bluesky.

## Run locally

```sh
uv run bot.py          # process + post new announcements
uv run bot.py --seed   # mark everything currently listed as done (automatic on first run)
```

## Run from GHCR

Long-running container, checks for new announcements every hour at :03 plus a random 0-10 min offset, between 06:00 and 22:00 Prague time.
All state (done markers, mp3s, whisper model, `.app-password`) lives in one mounted `/data` directory, so the image can be updated freely.
First run with no state seeds the current backlog as done instead of posting it.

```sh
mkdir -p data && cp .app-password data/     # Bluesky app password, one line
docker compose up -d
docker compose logs -f
docker compose pull && docker compose up -d # update to the latest image
```

Image is built and pushed by `.github/workflows/docker.yml` on every push to `main`.
