# /// script
# requires-python = ">=3.12"
# dependencies = ["faster-whisper", "atproto"]
# ///
"""Daily bot: transcribe new Křepice municipal announcements from rozana.cz, post them to Bluesky.

Run:   uv run bot.py          # process + post new announcements
       uv run bot.py --seed   # mark everything currently listed as done, no fetch/post (first-run backfill guard)
       uv run bot.py --loop   # run forever: every hour at :03 between 06:00 and 22:00 local time (docker)
State: out/<post_id>.json exists => post done. audio/ keeps mp3s so nothing is re-fetched.
Auth:  .app-password holds the Bluesky app password (one line). Handle is BSKY_HANDLE below.
"""
import datetime as dt
import html
import json
import pathlib
import re
import sys
import time
import traceback
import urllib.request

BASE = "https://www.rozana.cz"
LIST = f"{BASE}/obec/9LKmaG-2NL1X/hlaseni"
OUT = pathlib.Path("out")
AUDIO = pathlib.Path("audio")
BSKY_HANDLE = "krepicenews.bsky.social"
BSKY_PASSWORD_FILE = pathlib.Path(".app-password")
POST_LIMIT = 300  # Bluesky grapheme limit

# Towns around Křepice (okres Břeclav) so Whisper spells them right.
PROMPT = (
    "Hlášení obecního úřadu Křepice. Křepice, Nikolčice, Velké Němčice, Uherčice, Starovice, "
    "Hustopeče, Šitbořice, Diváky, Boleradice, Kurdějov, Kobylí, Bořetice, Vrbice, Brumovice, "
    "Morkůvky, Klobouky u Brna, Borkovany, Těšany, Moutnice, Měnín, Nosislav, Židlochovice, "
    "Vranovice, Pouzdřany, Popice, Strachotín, Šakvice, Zaječí, Velké Pavlovice, Němčičky, "
    "Horní Bojanovice, Starovičky, Pohořelice, Břeclav, Brno."
)

# Post-transcription fixes: (regex, replacement), applied in order, case-insensitive.
# Add a row whenever Whisper reliably gets something wrong.
FIXES = [
    (r"\s*zavináče?\s*-?\s*", "@"),  # "jan zavináč seznam.cz" -> "jan@seznam.cz"
    (r"(?<=\S)\s+tečka\s+(?=\S)", "."),  # "jan@seznam tečka cz" -> "jan@seznam.cz"
]


def fix(text: str) -> str:
    for pat, repl in FIXES:
        text = re.sub(pat, repl, text, flags=re.I)
    return text


CARD = re.compile(
    r'<span class="date">(?P<date>[\d.]+)</span>\s*<span class="time">(?P<time>[\d:]+).*?'
    r'href="/obec/[\w-]+/hlaseni/(?P<id>[\w-]+)".*?'
    r'<p class="block-2line">(?P<title>.*?)</p>',
    re.S,
)
MP3 = re.compile(r'/data/hlasenie_prilohy/([\w-]+)\.mp3')


TTY = sys.stderr.isatty()


def status(msg: str) -> None:
    """Overwrite a single progress line on stderr. No-op when not interactive (cron)."""
    if TTY:
        print(f"\r\033[K{msg}", end="", file=sys.stderr, flush=True)


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "krepicenews-bot"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def parse_list(page: str) -> list[dict]:
    return [
        {"id": m["id"], "date": m["date"], "time": m["time"], "title": html.unescape(m["title"]).strip()}
        for m in CARD.finditer(page)
    ]


def parse_post(page: str) -> list[str]:
    return list(dict.fromkeys(MP3.findall(page)))  # dedupe, keep order


def chunk(text: str, limit: int = POST_LIMIT) -> list[str]:
    """Split into <=limit chunks at sentence boundaries; number them if more than one."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    parts, cur = [], ""
    for s in sentences:
        if cur and len(cur) + 1 + len(s) > limit - 8:  # leave room for " (12/34)"
            parts.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        parts.append(cur)
    if len(parts) == 1:
        return parts
    return [f"{p} ({i}/{len(parts)})" for i, p in enumerate(parts, 1)]


def bsky_login():
    from atproto import Client

    client = Client()
    client.login(BSKY_HANDLE, BSKY_PASSWORD_FILE.read_text().strip())
    return client


def bsky_thread(client, text: str, audio_url: str, when: str) -> str:
    """Post text as one post, or a thread if it exceeds the limit. Root post carries a link card to the audio. Returns root URI."""
    from atproto import models

    card = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            uri=audio_url, title="▶ Přehrát zvukový záznam", description=f"Hlášení obce Křepice, {when}"
        )
    )
    root = parent = None
    for part in chunk(text):
        reply = None
        if root:
            reply = models.AppBskyFeedPost.ReplyRef(
                parent=models.create_strong_ref(parent), root=models.create_strong_ref(root)
            )
        parent = client.send_post(part, reply_to=reply, langs=["cs"], embed=None if root else card)
        root = root or parent
    return root.uri


def main(argv: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    AUDIO.mkdir(exist_ok=True)
    status("fetching announcement list")
    posts = parse_list(get(LIST).decode())
    todo = [p for p in posts if not (OUT / f"{p['id']}.json").exists()]

    if "--seed" in argv:
        for p in todo:
            (OUT / f"{p['id']}.json").write_text(json.dumps({**p, "seeded": True}, ensure_ascii=False, indent=2))
        status("")
        print(f"seeded {len(todo)} posts")
        return 0
    if not todo:
        status("")
        print("nothing new")
        return 0

    from faster_whisper import WhisperModel  # slow import, only when needed

    status("loading whisper large-v3")
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    status("logging in to bluesky")
    bsky = bsky_login()
    for i, post in enumerate(todo, 1):
        tag = f"[{i}/{len(todo)}] {post['date']} {post['title'][:40]}"
        status(f"{tag}: fetching page")
        post["audio"] = []
        for mp3 in parse_post(get(f"{LIST}/{post['id']}").decode()):
            path = AUDIO / f"{mp3}.mp3"
            url = f"{BASE}/data/hlasenie_prilohy/{mp3}.mp3"
            if not path.exists():
                status(f"{tag}: downloading {mp3}")
                path.write_bytes(get(url))
            segs, info = model.transcribe(
                str(path), language="cs", beam_size=5, vad_filter=True, initial_prompt=PROMPT
            )
            parts = []
            for s in segs:  # generator: segments arrive as they are decoded
                parts.append(s.text.strip())
                status(f"{tag}: transcribing {mp3} {s.end:.0f}/{info.duration:.0f}s")
            text = fix(" ".join(parts))
            status(f"{tag}: posting {mp3}")
            post["audio"].append({"id": mp3, "text": text, "bsky": bsky_thread(bsky, text, url, post['date'])})
        # written last: a failure above leaves no JSON, so the post is retried next run
        (OUT / f"{post['id']}.json").write_text(json.dumps(post, ensure_ascii=False, indent=2))
        status("")
        print(post["date"], post["title"], f"({len(post['audio'])} audio)")
    return 0

def next_run(now: dt.datetime) -> dt.datetime:
    """Next hh:03 with 06 <= hh <= 22, strictly after now."""
    t = now.replace(minute=3, second=0, microsecond=0)
    if t <= now:
        t += dt.timedelta(hours=1)
    if t.hour > 22:
        t = t.replace(hour=6) + dt.timedelta(days=1)
    elif t.hour < 6:
        t = t.replace(hour=6)
    return t


def loop() -> None:
    while True:
        t = next_run(dt.datetime.now())
        print("next run", t, flush=True)
        time.sleep(max(0, (t - dt.datetime.now()).total_seconds()))
        try:
            main([])
        except Exception:
            traceback.print_exc()  # keep the loop alive; the post is retried next tick


if __name__ == "__main__":
    if "--loop" in sys.argv:
        loop()
    sys.exit(main(sys.argv[1:]))
