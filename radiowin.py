#!/usr/bin/env python3
"""radiowin - enter radio contests by texting a code word to the station.

Usage:
    python3 radiowin.py WORD            # text "WORD First Last" to 959959
    python3 radiowin.py WORD --dry-run  # show the message without sending
    python3 radiowin.py --set-name      # change the saved name
    python3 radiowin.py --history       # list past entries
"""

import argparse
import json
import subprocess
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

SHORT_CODE = "959959"
DATA_DIR = Path.home() / ".radiowin"
CONFIG_FILE = DATA_DIR / "config.json"
ENTRIES_FILE = DATA_DIR / "entries.json"

# Sends an SMS through Messages.app (needs iPhone Text Message Forwarding).
# The number and message are passed as arguments so no quoting is needed.
SEND_SCRIPT = """
on run argv
    set targetNumber to item 1 of argv
    set messageText to item 2 of argv
    tell application "Messages"
        set smsService to 1st account whose service type = SMS
        set targetBuddy to participant targetNumber of smsService
        send messageText to targetBuddy
    end tell
end run
"""


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def ask_name():
    while True:
        first = input("First name: ").strip()
        last = input("Last name: ").strip()
        if first and last:
            save_json(CONFIG_FILE, {"first": first, "last": last})
            print(f"Saved name: {first} {last}")
            return first, last
        print("Both first and last name are required.")


def get_name():
    config = load_json(CONFIG_FILE, {})
    if config.get("first") and config.get("last"):
        return config["first"], config["last"]
    print("No name saved yet - let's set it up.")
    return ask_name()


def build_message(word, first, last):
    return f"{word.strip().upper()} {first} {last}"


def send_sms(number, message):
    """Send via Messages.app; fall back to opening a prefilled draft."""
    result = subprocess.run(
        ["osascript", "-e", SEND_SCRIPT, number, message],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    print("Couldn't send automatically:", result.stderr.strip() or "unknown error")
    print("Opening a prefilled draft in Messages instead - just press Send.")
    url = f"sms:{number}&body={urllib.parse.quote(message)}"
    subprocess.run(["open", url])
    return False


def show_history():
    entries = load_json(ENTRIES_FILE, [])
    if not entries:
        print("No entries yet.")
        return
    for entry in entries:
        status = "sent" if entry["sent"] else "draft opened"
        print(f"{entry['time']}  {entry['message']}  ({status})")


def main():
    parser = argparse.ArgumentParser(
        description=f"Text a radio contest code word to {SHORT_CODE}."
    )
    parser.add_argument("word", nargs="?", help="the code word from the radio")
    parser.add_argument("--dry-run", action="store_true", help="show the message only")
    parser.add_argument("--set-name", action="store_true", help="change the saved name")
    parser.add_argument("--history", action="store_true", help="list past entries")
    parser.add_argument("-y", "--yes", action="store_true", help="skip the confirmation")
    args = parser.parse_args()

    if args.set_name:
        ask_name()
        return
    if args.history:
        show_history()
        return

    word = args.word or input("Code word: ")
    if not word.strip() or len(word.split()) != 1:
        sys.exit("The code word should be a single word.")

    first, last = get_name()
    message = build_message(word, first, last)
    print(f"To: {SHORT_CODE}\nMessage: {message}")

    entries = load_json(ENTRIES_FILE, [])
    if any(e["message"] == message for e in entries):
        print("Heads up: you've already entered with this code word.")
        if not args.dry_run and input("Send again anyway? [y/N] ").lower() != "y":
            return

    if args.dry_run:
        print("(dry run - nothing sent)")
        return
    if not args.yes and input("Send it? [Y/n] ").lower() not in ("", "y", "yes"):
        print("Cancelled.")
        return

    sent = send_sms(SHORT_CODE, message)
    entries.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "message": message,
        "sent": sent,
    })
    save_json(ENTRIES_FILE, entries)
    if sent:
        print("Sent! Good luck.")


if __name__ == "__main__":
    main()
