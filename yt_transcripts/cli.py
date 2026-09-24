"""Turn YouTube videos, playlists, or whole channels into transcript files."""

import argparse
import json
import re
import sys
from pathlib import Path

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})")


def video_id_from(url: str) -> str | None:
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url
    m = VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


def expand(url: str, limit: int | None) -> list[dict]:
    """Return [{id, title}] for a video, playlist, or channel URL."""
    vid = video_id_from(url)
    if vid and "list=" not in url:
        return [{"id": vid, "title": None}]
    # Channel root URLs list tabs (Videos/Shorts/Live); default to the Videos tab.
    if re.search(r"youtube\.com/(@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)/?$", url):
        url = url.rstrip("/") + "/videos"
    opts = {"extract_flat": True, "quiet": True, "skip_download": True}
    if limit:
        opts["playlistend"] = limit
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = info.get("entries") or [info]
    out = []
    for e in entries:
        if e.get("entries"):  # nested tab
            out.extend({"id": x["id"], "title": x.get("title")} for x in e["entries"] if x.get("id"))
        elif e.get("id"):
            out.append({"id": e["id"], "title": e.get("title")})
    return out[:limit] if limit else out


def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def safe_name(s: str) -> str:
    return re.sub(r"[^\w\- ]+", "", s).strip()[:80] or "untitled"


def render(snippets, fmt: str, timestamps: bool) -> str:
    if fmt == "json":
        return json.dumps(
            [{"text": s.text, "start": s.start, "duration": s.duration} for s in snippets],
            ensure_ascii=False, indent=2,
        )
    if fmt == "srt":
        blocks = []
        for i, s in enumerate(snippets, 1):
            def t(x):
                ms = int(round(x * 1000))
                return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
            blocks.append(f"{i}\n{t(s.start)} --> {t(s.start + s.duration)}\n{s.text}\n")
        return "\n".join(blocks)
    if timestamps:
        return "\n".join(f"[{fmt_ts(s.start)}] {s.text}" for s in snippets)
    return " ".join(s.text.replace("\n", " ") for s in snippets)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="yt-transcripts", description=__doc__)
    p.add_argument("urls", nargs="+", help="video, playlist, or channel URLs (or video IDs)")
    p.add_argument("-o", "--out", default="transcripts", help="output directory (default: transcripts)")
    p.add_argument("-f", "--format", choices=["txt", "srt", "json"], default="txt")
    p.add_argument("-l", "--lang", action="append", help="preferred language code(s), e.g. -l en -l es")
    p.add_argument("-n", "--limit", type=int, help="max videos per channel/playlist")
    p.add_argument("-t", "--timestamps", action="store_true", help="include timestamps in txt output")
    p.add_argument("--combine", action="store_true", help="also write all transcripts into one file")
    p.add_argument("--overwrite", action="store_true", help="re-fetch transcripts that already exist")
    args = p.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    api = YouTubeTranscriptApi()
    langs = args.lang or ["en"]
    ok = failed = skipped = 0
    combined = []

    for url in args.urls:
        try:
            videos = expand(url, args.limit)
        except Exception as e:
            print(f"! could not read {url}: {e}", file=sys.stderr)
            continue
        print(f"{url}: {len(videos)} video(s)")
        for v in videos:
            name = f"{safe_name(v['title'])} [{v['id']}]" if v["title"] else v["id"]
            path = out_dir / f"{name}.{args.format}"
            if path.exists() and not args.overwrite:
                skipped += 1
                if args.combine:
                    combined.append((name, path.read_text(encoding="utf-8")))
                continue
            try:
                fetched = api.fetch(v["id"], languages=langs)
            except Exception as e:
                failed += 1
                reason = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
                print(f"  x {v['id']}: {type(e).__name__}: {reason}", file=sys.stderr)
                continue
            text = render(fetched.snippets, args.format, args.timestamps)
            path.write_text(text, encoding="utf-8")
            combined.append((name, text))
            ok += 1
            print(f"  ✓ {path.name}")

    if args.combine and combined:
        cpath = out_dir / f"_combined.{'txt' if args.format != 'json' else 'json'}"
        if args.format == "json":
            cpath.write_text(json.dumps({n: json.loads(t) for n, t in combined}, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            cpath.write_text("\n\n".join(f"===== {n} =====\n{t}" for n, t in combined), encoding="utf-8")
        print(f"combined -> {cpath}")

    print(f"done: {ok} saved, {skipped} skipped (already existed), {failed} failed")


if __name__ == "__main__":
    main()
