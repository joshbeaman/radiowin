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
