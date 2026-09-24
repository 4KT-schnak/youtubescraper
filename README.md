# yt-transcripts

Turn YouTube videos, playlists, or entire channels into transcript files.

Uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to list a channel's or playlist's videos and
[youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) to fetch captions
(manual or auto-generated). It doesn't download any video or audio.

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
# single video (URL or bare ID)
python -m yt_transcripts https://www.youtube.com/watch?v=VIDEO_ID

# whole channel (Videos tab), newest first
python -m yt_transcripts https://www.youtube.com/@somechannel

# latest 20 videos, with timestamps, plus one combined file
python -m yt_transcripts https://www.youtube.com/@somechannel -n 20 -t --combine

# playlist as SRT, prefer Spanish then English
python -m yt_transcripts "https://www.youtube.com/playlist?list=PL..." -f srt -l es -l en
```

| Option | Meaning |
|---|---|
| `-o DIR` | Output directory (default `transcripts/`) |
| `-f txt\|srt\|json` | Output format (default `txt`) |
| `-l CODE` | Preferred language(s), in order (default `en`) |
| `-n N` | Max videos per channel/playlist |
| `-t` | Add `[hh:mm:ss]` timestamps to txt output |
| `--combine` | Also write every transcript into a single `_combined` file |
| `--overwrite` | Fetch again even if the file already exists (by default existing files are skipped, so you can re-run it to resume) |

Files are saved as `Title [VIDEO_ID].ext`. Videos without captions are reported and skipped.

**Note:** YouTube rate-limits and sometimes blocks cloud/datacenter IPs. Run this from a home
connection, or add delays and fewer videos per run if you start seeing errors.
