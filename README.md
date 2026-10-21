# radiowin

Automatically enters the **Star 95.9 (CHFM Calgary) cash call keyword** contest
from your Mac.

Near the top of each contest hour, the station announces a keyword. To enter,
you text `KEYWORD First Last` to **959959**. radiowin listens to the station's
online stream, picks out the keyword, and sends that text for you through the
Messages app.

## How it works

1. A background listener tunes in to the Star 95.9 stream one minute before
   each contest hour and listens for 12 minutes.
2. It turns the audio into text on your Mac using
   [faster-whisper](https://github.com/SYSTRAN/faster-whisper). No accounts or
   API keys are needed.
3. It looks for the keyword in the transcript:
   - a word spelled out letter by letter ("future, f-u-t-u-r-e")
   - "the keyword is ..." or "code word is ..."
   - "text the word ..." or "text in ..."
4. When it finds one, it texts `KEYWORD First Last` to 959959, shows a Mac
   notification, and skips any keyword you've already entered with.

**Schedule**

| Days | Hours |
| --- | --- |
| Monday–Friday | 8am hour to 7pm hour |
| Saturday–Sunday | noon hour to 6pm hour |

You can change the schedule at the top of `listen.py`.

## Requirements

- A Mac with Python 3 and [Homebrew](https://brew.sh)
- An iPhone with **Settings → Messages → Text Message Forwarding** turned on
  for the Mac, so the Mac can send SMS
- The Mac has to be on and awake at the top of each hour. It keeps itself
  awake while it's listening.

## Setup

```sh
brew install ffmpeg
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 radiowin.py --set-name               # saves your first and last name
.venv/bin/python listen.py --install         # runs in the background from now on
```

The first time it sends a text, macOS asks whether it can control Messages.
Click **Allow**.

## Commands

### Automatic listener (`listen.py`)

| Command | What it does |
| --- | --- |
| `.venv/bin/python listen.py --install` | Run in the background, starting at login |
| `.venv/bin/python listen.py --uninstall` | Stop the background listener |
| `.venv/bin/python listen.py` | Run on the schedule in this terminal |
| `.venv/bin/python listen.py --now` | Listen to the stream right now |
| `.venv/bin/python listen.py --now --dry-run --minutes 3` | Listen now and print what it hears, never sends |
| `.venv/bin/python listen.py --file clip.m4a --dry-run` | Find the keyword in a recording |
| `.venv/bin/python listen.py --file clip.m4a --to 4035551234` | Test: send the entry to your own phone instead of 959959 |

### Manual entry (`radiowin.py`)

If you heard the keyword yourself:

| Command | What it does |
| --- | --- |
| `python3 radiowin.py WORD` | Text `WORD First Last` to 959959 (asks to confirm) |
| `python3 radiowin.py WORD -y` | Send without confirming |
| `python3 radiowin.py WORD --dry-run` | Show the message, don't send |
| `python3 radiowin.py --set-name` | Change your saved name |
| `python3 radiowin.py --history` | List past entries |

## Files

Everything personal stays on your Mac in `~/.radiowin/`, not in this repo:

| File | Contents |
| --- | --- |
| `config.json` | Your name |
| `entries.json` | Entries sent so far |
| `listen.log` | What the listener did each hour |
| `transcripts/` | What it heard each hour, useful if it misses a keyword |

If sending through Messages fails, radiowin opens a draft with the text filled
in, so you just press Send.
