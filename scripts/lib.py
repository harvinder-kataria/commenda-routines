"""Shared utilities for the Commenda AM Brief bot."""
import os
import re
import time
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

FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]
USER_AGENT = "Mozilla/5.0 (compatible; CommendaAMBot/1.0; +https://github.com/harvinder-kataria/commenda-routines)"


def gemini_chat(prompt: str, with_search: bool = True, model: str = None) -> str:
    config = None
    if with_search:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    models = [model] if model else FALLBACK_MODELS
    last_error = None
    for m in models:
        for attempt in range(3):
            try:
                response = _gemini_client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=config,
                )
                return response.text or ""
            except Exception as e:
                last_error = e
                err_str = str(e)
                is_transient = any(s in err_str for s in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"))
                if not is_transient:
                    raise
                if attempt < 2:
                    wait = 15 * (attempt + 1)
                    print(f"[gemini] {m} transient error (attempt {attempt+1}/3), waiting {wait}s")
                    time.sleep(wait)
                else:
                    print(f"[gemini] {m} exhausted retries, trying next model")
    raise RuntimeError(f"All Gemini models exhausted. Last error: {last_error}")


VERTEX_REDIRECT = "vertexaisearch.cloud.google.com/grounding-api-redirect"


def clean_brief_text(text: str) -> str:
    """Strip Google Search redirect wrappers, convert Markdown links to Slack format."""
    text = re.sub(
        r'\[\[([^\]]+)\]\((https?://[^\)\s]+)\)\]\(https?://' + re.escape(VERTEX_REDIRECT) + r'/[^\)]+\)',
        r'<\2|\1>',
        text,
    )
    text = re.sub(
        r'\[([^\]]+)\]\(https?://' + re.escape(VERTEX_REDIRECT) + r'/[^\)]+\)',
        r'\1',
        text,
    )
    text = re.sub(
        r'\[([^\]\n]+)\]\((https?://[^\)\s]+)\)',
        r'<\2|\1>',
        text,
    )
    text = re.sub(
        r'<https?://' + re.escape(VERTEX_REDIRECT) + r'/[^|\s>]+\|([^>]+)>',
        r'\1',
        text,
    )
    return text


def url_works(url: str, timeout: float = 6.0) -> bool:
    """Return True if the URL responds with a non-error status within timeout."""
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return False
    if VERTEX_REDIRECT in url:
        return False
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        if r.status_code < 400:
            return True
        if r.status_code in (403, 405, 406, 410, 415, 429):
            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
            r.close()
            return r.status_code < 400
        return False
    except requests.RequestException as e:
        print(f"[url-check] {url} -> {type(e).__name__}: {e}")
        return False


def slack_post(text: str, channel: str = CHANNEL_ID) -> dict:
    text = clean_brief_text(text)
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


def slack_read_channel(channel: str = CHANNEL_ID, limit: int = 100, days: int = 14) -> list:
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
KICKER_RE = re.compile(r"▎\s*[^·]+·\s*([A-Z][A-Z0-9 \-&\.]+?)\s*▎")
HEADLINE_RE = re.compile(r"^\*([^*\n]+?)\*\s*$", re.MULTILINE)


def extract_dedup(messages: list) -> dict:
    """Pull URLs, company entities, and headlines from recent channel posts."""
    seen_urls = set()
    seen_entities = []
    seen_headlines = []
    for msg in messages:
        text = msg.get("text", "")
        for m in URL_RE.findall(text):
            url = m.rstrip(">,.;:!?)")
            seen_urls.add(url)
        for ent in KICKER_RE.findall(text):
            e = ent.strip()
            if e and e not in seen_entities:
                seen_entities.append(e)
        for hl in HEADLINE_RE.findall(text):
            h = hl.strip()
            if h and h not in seen_headlines:
                seen_headlines.append(h)
    return {
        "urls": seen_urls,
        "entities": seen_entities[:80],
        "headlines": seen_headlines[:60],
    }


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
