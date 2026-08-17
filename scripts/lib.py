"""Shared utilities for the Commenda AM Brief bot."""
import os
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

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
VERTEX_REDIRECT = "vertexaisearch.cloud.google.com/grounding-api-redirect"


def _generate(model: str, prompt: str, config):
    return _gemini_client.models.generate_content(
        model=model, contents=prompt, config=config,
    )


def _extract_sources(response) -> list:
    """Pull grounding source URIs from a Gemini response (real URLs from Google Search)."""
    sources = []
    for candidate in (response.candidates or []):
        gm = getattr(candidate, "grounding_metadata", None)
        if not gm:
            continue
        for chunk in (getattr(gm, "grounding_chunks", None) or []):
            web = getattr(chunk, "web", None)
            if web and getattr(web, "uri", None):
                sources.append(web.uri)
    return sources


def gemini_chat_with_sources(prompt: str, with_search: bool = True, model: str = None):
    """Returns (text, grounding_source_uris). Use this when you need to validate URLs."""
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
                response = _generate(m, prompt, config)
                return (response.text or ""), _extract_sources(response)
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


def gemini_chat(prompt: str, with_search: bool = True, model: str = None) -> str:
    """Backward-compatible wrapper that drops the sources list."""
    text, _ = gemini_chat_with_sources(prompt, with_search=with_search, model=model)
    return text


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
    """True if the URL responds with a non-error status within timeout."""
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


def resolve_url(url: str, timeout: float = 6.0) -> str:
    """Follow redirects, return final URL. Returns original on error."""
    if not url or not url.startswith("http"):
        return url
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        return r.url or url
    except requests.RequestException:
        return url


def extract_domain(url: str) -> str:
    """Bare domain, lowercased, no leading www."""
    try:
        host = urllib.parse.urlparse(url).hostname or ""
        host = host.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def resolve_grounding_domains(grounding_uris: list, max_resolve: int = 40) -> set:
    """Follow Vertex redirect URIs in parallel, return set of real publisher domains."""
    domains = set()
    if not grounding_uris:
        return domains
    with ThreadPoolExecutor(max_workers=10) as ex:
        for resolved in ex.map(resolve_url, grounding_uris[:max_resolve]):
            d = extract_domain(resolved)
            if d and "vertexaisearch" not in d and "googleusercontent" not in d:
                domains.add(d)
    return domains


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
