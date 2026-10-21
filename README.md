# radiowin

Enter radio contests from your Mac. When the station gives out a code word,
run:

```sh
python3 radiowin.py WORD
```

It texts `WORD First Last` to **959959** using the Messages app.

## Setup

- macOS with Python 3 (no extra packages needed).
- To send automatically, your iPhone needs **Settings → Messages → Text
  Message Forwarding** turned on for this Mac. Without it, radiowin opens a
  prefilled draft in Messages so you just press Send.
- The first run asks for your first and last name and saves it to
  `~/.radiowin/config.json`.

## Commands

| Command | What it does |
| --- | --- |
| `python3 radiowin.py WORD` | Send an entry (asks to confirm) |
| `python3 radiowin.py WORD -y` | Send without confirming |
| `python3 radiowin.py WORD --dry-run` | Show the message, don't send |
| `python3 radiowin.py --set-name` | Change your saved name |
| `python3 radiowin.py --history` | List past entries |

It warns you if you've already entered with the same code word.

## Automatic listening

`listen.py` listens to the Star 95.9 (CHFM Calgary) online stream for the first
12 minutes of every contest hour, transcribes it with Whisper on your Mac, and
texts the entry as soon as it hears "the keyword is ...".

Schedule: weekdays from the 8am hour to the 7pm hour, weekends from the noon
hour to the 6pm hour. You can change it at the top of `listen.py`.

One-time setup:

```sh
brew install ffmpeg
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 radiowin.py --set-name
```

| Command | What it does |
| --- | --- |
| `.venv/bin/python listen.py --now --dry-run --minutes 3` | Test: listen now and print what it hears, never sends |
| `.venv/bin/python listen.py` | Run on the schedule in this terminal |
| `.venv/bin/python listen.py --install` | Run in the background, starting at login |
| `.venv/bin/python listen.py --uninstall` | Stop the background listener |

Activity is logged to `~/.radiowin/listen.log`, and each hour's transcript is
saved in `~/.radiowin/transcripts/` so you can see exactly what it heard.
The Mac needs to be on and awake at the top of the hour. It stays awake by
itself while it's listening.
