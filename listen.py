#!/usr/bin/env python3
"""Listen to Star 95.9 for the hourly code word and enter automatically.

Usage:
    .venv/bin/python listen.py              # run forever on the contest schedule
    .venv/bin/python listen.py --now        # listen right now (sends if heard)
    .venv/bin/python listen.py --now --dry-run --minutes 3   # test, never sends
"""

import argparse
import re
import subprocess
import sys
import tempfile
import time
import wave
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

import radiowin

STREAM_URL = (
    "https://rogers-hls.leanstream.co/rogers/cal959.stream/playlist.m3u8"
    "?environment=web&args=app_03"
)

# Hours (24h clock) at which a listening session starts. Monday is 0.
WEEKDAY_HOURS = range(8, 20)   # 8am through the 7pm hour
WEEKEND_HOURS = range(12, 19)  # noon through the 6pm hour
LISTEN_MINUTES = 12
START_EARLY_SECONDS = 60       # tune in a minute before the hour

SEGMENT_SECONDS = 20
MODEL_NAME = "small.en"
LOG_FILE = radiowin.DATA_DIR / "listen.log"
TRANSCRIPT_DIR = radiowin.DATA_DIR / "transcripts"

# Words that follow "code word is ..." but aren't the code word itself.
NOT_A_WORD = {
    "the", "a", "an", "is", "was", "coming", "up", "next", "soon", "after",
    "this", "that", "right", "here", "now", "going", "gonna", "about", "to",
    "be", "and", "so", "in", "on", "at", "for", "you", "your", "it", "of",
    "today", "hour", "out", "still", "just", "again", "us", "me", "text", "texting", "texted", "coming",
}

# The text always goes to 959959, so these only look for the word itself.
PATTERNS = [
    # "the keyword is sunshine", "code word of the hour: sunshine"
    re.compile(r"(?:code|key|secret|magic|keyword)\s*-?\s*word"
               r"(?:\s+(?:of the hour|this hour|for this hour|today))?"
               r"(?:\s+(?:is|was|it's|its|will be)|\s*:)[\s:,.\"']+([a-z]+)"),
    # "text the word sunshine", "text in sunshine"
    re.compile(r"\btext\s+(?:in\s+)?the\s+word\s+([a-z]+)"),
    re.compile(r"\btext\s+in\s+([a-z]+)"),
]

# Letters read out one at a time: "f-u-t-u-r-e", "F.U.T. U.R.E.", "s u n n y"
SPELLED = re.compile(r"\b(?:[a-z][-.\s]\s?){2,}[a-z]\b\.?")

# Spelled-out things that aren't the keyword (call letters etc.)
NOT_SPELLED = {"chfm", "fm"}


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    radiowin.DATA_DIR.mkdir(exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")


def notify(title, message):
    script = 'on run argv\ndisplay notification (item 2 of argv) with title (item 1 of argv)\nend run'
    subprocess.run(["osascript", "-e", script, title, message], capture_output=True)


def find_code_word(text):
    text = text.lower()
    # A word spelled out letter by letter is the strongest sign: hosts spell
    # the keyword so people can text it. Accept it when it's also said as a
    # normal word ("future, f-u-t-u-r-e") or the host is talking about texting.
    plain = SPELLED.sub(" ", text)
    for match in SPELLED.finditer(text):
        word = re.sub(r"[^a-z]", "", match.group())
        if len(word) < 3 or word in NOT_SPELLED or word in NOT_A_WORD:
            continue
        if re.search(rf"\b{word}\b", plain) or "text" in text:
            return word
    # Otherwise listen for the phrasing, with any spelling joined back up.
    text = SPELLED.sub(lambda m: re.sub(r"[^a-z]", "", m.group()) + " ", text)
    for pattern in PATTERNS:
        for match in pattern.finditer(text):
            word = match.group(1)
            if word not in NOT_A_WORD and len(word) > 1:
                return word
    return None


def next_session_start(now):
    """Datetime when the next listening session should begin."""
    hour = now.replace(minute=0, second=0, microsecond=0)
    for _ in range(24 * 8):
        hours = WEEKDAY_HOURS if hour.weekday() < 5 else WEEKEND_HOURS
        start = hour - timedelta(seconds=START_EARLY_SECONDS)
        # Still worth joining if we're within the listening window.
        if hour.hour in hours and now < hour + timedelta(minutes=LISTEN_MINUTES):
            return max(start, now)
        hour += timedelta(hours=1)
    raise RuntimeError("schedule is empty")


def read_wav(path):
    with wave.open(str(path)) as w:
        frames = w.readframes(w.getnframes())
    return np.frombuffer(frames, np.int16).astype(np.float32) / 32768.0


def listen(model, minutes, dry_run, source=STREAM_URL):
    """Record the stream and transcribe as it goes. Returns the word or None."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        reconnect = (["-reconnect", "1", "-reconnect_streamed", "1"]
                     if source.startswith("http") else [])
        ffmpeg = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", *reconnect, "-i", source,
             "-t", str(minutes * 60), "-ac", "1", "-ar", "16000",
             "-f", "segment", "-segment_time", str(SEGMENT_SECONDS),
             str(tmp / "seg%04d.wav")],
            stdin=subprocess.DEVNULL,
        )
        caffeinate = subprocess.Popen(["caffeinate", "-i", "-w", str(ffmpeg.pid)])
        transcript = TRANSCRIPT_DIR / f"{datetime.now():%Y-%m-%d_%H%M}.txt"
        TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        done, previous = 0, np.zeros(0, np.float32)
        try:
            while True:
                finished = ffmpeg.poll() is not None
                segments = sorted(tmp.glob("seg*.wav"))
                # The newest segment is still being written unless ffmpeg is done.
                ready = segments if finished else segments[:-1]
                for seg in ready[done:]:
                    audio = read_wav(seg)
                    # Include the previous segment so words split across
                    # the boundary still get caught.
                    parts, _ = model.transcribe(
                        np.concatenate([previous[-5 * 16000:], audio]),
                        language="en", vad_filter=True)
                    text = " ".join(p.text.strip() for p in parts)
                    previous = audio
                    done += 1
                    with transcript.open("a") as f:
                        f.write(f"[{datetime.now():%H:%M:%S}] {text}\n")
                    if dry_run:
                        print(f"  heard: {text}")
                    word = find_code_word(text)
                    if word:
                        log(f"Code word heard: {word!r} in: {text}")
                        return word
                if finished:
                    if ffmpeg.returncode:
                        log(f"ffmpeg exited with code {ffmpeg.returncode}")
                    return None
                time.sleep(2)
        finally:
            ffmpeg.terminate()
            ffmpeg.wait()
            caffeinate.terminate()


def enter(word, dry_run, to=radiowin.SHORT_CODE):
    first, last = radiowin.get_name()
    message = radiowin.build_message(word, first, last)
    entries = radiowin.load_json(radiowin.ENTRIES_FILE, [])
    testing = to != radiowin.SHORT_CODE
    if not testing and any(e["message"] == message for e in entries):
        log(f"Already entered with {word!r}, skipping")
        return
    if dry_run:
        log(f"(dry run) would send: {message}")
        notify("radiowin (dry run)", f"Heard code word: {word.upper()}")
        return
    sent = radiowin.send_sms(to, message)
    if not testing:  # test sends shouldn't block the real entry later
        entries.append({"time": f"{datetime.now():%Y-%m-%d %H:%M}",
                        "message": message, "sent": sent})
        radiowin.save_json(radiowin.ENTRIES_FILE, entries)
    log(f"{'Sent' if sent else 'Opened draft'} to {to}: {message}")
    notify("radiowin", f"Entered with {word.upper()}"
           if sent else f"Press Send in Messages: {word.upper()}")


def load_model():
    from faster_whisper import WhisperModel
    log(f"Loading speech model {MODEL_NAME}...")
    return WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")


PLIST = Path.home() / "Library/LaunchAgents/com.radiowin.listen.plist"


def install():
    """Run the listener in the background at login, restarting if it stops."""
    here = Path(__file__).resolve().parent
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.radiowin.listen</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{here / "listen.py"}</string>
    </array>
    <key>WorkingDirectory</key><string>{here}</string>
    <key>EnvironmentVariables</key>
    <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin</string></dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardErrorPath</key><string>{radiowin.DATA_DIR / "listen.err"}</string>
</dict>
</plist>
""")
    subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    subprocess.run(["launchctl", "load", str(PLIST)], check=True)
    print(f"Installed. Log: {LOG_FILE}")


def uninstall():
    subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    PLIST.unlink(missing_ok=True)
    print("Uninstalled.")


def main():
    parser = argparse.ArgumentParser(description="Listen to Star 95.9 for the code word.")
    parser.add_argument("--now", action="store_true", help="listen immediately, once")
    parser.add_argument("--dry-run", action="store_true", help="never send a text")
    parser.add_argument("--minutes", type=float, default=LISTEN_MINUTES)
    parser.add_argument("--file", help="read a recording instead of the stream (implies --now)")
    parser.add_argument("--to", default=radiowin.SHORT_CODE, help="number to text (for testing)")
    parser.add_argument("--install", action="store_true", help="run in the background")
    parser.add_argument("--uninstall", action="store_true", help="stop background running")
    args = parser.parse_args()

    if args.uninstall:
        uninstall()
        return
    if not sys.stdin.isatty() and not radiowin.load_json(radiowin.CONFIG_FILE, {}).get("first"):
        sys.exit("No name saved. Run: python3 radiowin.py --set-name")
    radiowin.get_name()  # make sure a name is saved before going unattended
    if args.install:
        install()
        return
    model = load_model()

    if args.now or args.file:
        word = listen(model, args.minutes, args.dry_run, args.file or STREAM_URL)
        if word:
            enter(word, args.dry_run, args.to)
        else:
            log("No code word heard.")
        return

    log("Waiting for the next contest hour.")
    while True:
        start = next_session_start(datetime.now())
        log(f"Next listen: {start:%a %H:%M}")
        # Short sleeps so a laptop waking from sleep doesn't oversleep.
        while datetime.now() < start:
            time.sleep(min(30, max(1, (start - datetime.now()).total_seconds())))
        top_of_hour = (start + timedelta(seconds=START_EARLY_SECONDS)).replace(
            minute=0, second=0, microsecond=0)
        remaining = top_of_hour + timedelta(minutes=LISTEN_MINUTES) - datetime.now()
        log(f"Listening for {remaining.total_seconds() / 60:.0f} minutes")
        try:
            word = listen(model, remaining.total_seconds() / 60, args.dry_run)
            if word:
                enter(word, args.dry_run)
            else:
                log("No code word heard this hour.")
        except Exception as e:  # keep running next hour no matter what
            log(f"Error: {e}")
        # Don't restart the same hour's session.
        while datetime.now() < top_of_hour + timedelta(minutes=LISTEN_MINUTES):
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
