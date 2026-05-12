"""Shared utilities for the Commenda AM Brief bot."""
import os
import re
import requests
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import types

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CHANNEL_ID = "C0B34GAUH0Q"
CANVAS_ID = "F0B34R53F7Y"
USER_ID = "U09SB67C13P"

_gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def gemini_chat(prompt: str, with_search: bool = True, model: str = "gemini-2.5-flash") -> str:
    config = None
    if with_search:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    response = _gemini_client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    return response.text or ""


def slack_post(text: str, channel: str = CHANNEL_ID) -> dict:
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {"channel": channel, "text": text, "mrkdwn": True, "unfurl_links": False}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(f"Slack chat.postMessage failed: {body}")
    return body


def slack_read_channel(channel: str = CHANNEL_ID, limit: int = 50, days: int = 14) -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    url = "https://slack.com/api/conversations.history"
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    params = {"channel": channel, "limit": limit, "oldest": str(cutoff)}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(f"Slack conversations.history failed: {body}")
    return body.get("messages", [])


URL_RE = re.compile(r"https?://[^\s<>|]+")


def extract_dedup(messages: list) -> dict:
    seen_urls = set()
    for msg in messages:
        text = msg.get("text", "")
        for m in URL_RE.findall(text):
            url = m.rstrip(">,.;:!?)")
            seen_urls.add(url)
    return {"urls": seen_urls}


def get_today_context() -> dict:
    ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    return {
        "date_str": ist.strftime("%a, %b %d %Y"),
        "date_display": ist.strftime("%a · %b %d · %Y").upper(),
        "weekday": ist.weekday(),
        "weekday_name": ist.strftime("%A"),
        "iso_date": ist.strftime("%Y-%m-%d"),
    }


def regional_lean_for_day(weekday: int) -> str:
    return {
        0: "US-heavy, week opener.",
        1: "India focus (1-2 India items on top of US baseline).",
        2: "LatAm focus (1-2 LatAm items: Mexico CFDI, Brazil NF-e, regional fintech).",
        3: "Europe focus (1-2 EU/UK items: MTD, e-invoicing, DORA).",
        4: "Global synthesis (cross-region patterns, week in review).",
        5: "Global synthesis.",
        6: "Global synthesis.",
    }.get(weekday, "Global synthesis.")
