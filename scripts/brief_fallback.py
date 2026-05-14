"""Fallback that posts the daily brief at 9 or 11 AM IST if the 8 AM scheduled cron failed."""
from datetime import datetime, timezone, timedelta
from lib import slack_read_channel
from brief import main as brief_main

BOT_USER_ID = "U0B33UL3J05"
BRIEF_MARKER = "COMMENDA · AM BRIEF"


def has_brief_today() -> bool:
    """Check if today's brief is already in the channel."""
    ist_today = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date()
    msgs = slack_read_channel(limit=30, days=2)
    for msg in msgs:
        text = msg.get("text", "")
        if BRIEF_MARKER not in text:
            continue
        if msg.get("user") != BOT_USER_ID and msg.get("bot_id") is None:
            continue
        ts = float(msg.get("ts", 0))
        msg_date = (datetime.fromtimestamp(ts, timezone.utc) + timedelta(hours=5, minutes=30)).date()
        if msg_date == ist_today:
            return True
    return False


def main():
    if has_brief_today():
        print("Today's brief already posted, exiting silently.")
        return
    print("No brief found today, running fallback.")
    brief_main()


if __name__ == "__main__":
    main()
