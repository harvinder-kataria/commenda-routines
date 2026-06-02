"""Gamechanger Drops checker. Runs M-F at 10/13/16/19 IST. Silent unless material news."""
import re
from lib import (
    gemini_chat, slack_post, slack_read_channel, extract_dedup,
    get_today_context, url_works, CHANNEL_ID, URL_RE,
)


def main():
    ctx = get_today_context()
    msgs = slack_read_channel(limit=100, days=14)
    dedup = extract_dedup(msgs)
    seen_urls_str = "\n".join(f"- {u}" for u in sorted(dedup["urls"])[:150]) or "(none)"
    seen_entities_str = ", ".join(dedup["entities"][:60]) or "(none)"

    prompt = f"""You are checking for "gamechanger" news drops in accounting/finance/tax tech IN THE LAST 3 HOURS only. Use Google Search.

TODAY: {ctx['date_str']}

A "gamechanger" materially shifts Commenda's competitive position. Examples:
- Anthropic / OpenAI / Google major launch
- Big 4 plus AI partnership announcement
- Intuit / Xero / Sage / Avalara major product
- M&A in accounting tools space
- Rillet / Puzzle / DualEntry / Numeric significant news
- Major regulator tech announcement
- Multi-entity / global compliance tooling launch or shutdown

DO NOT post for:
- Routine vendor PR
- Listicles or trend pieces without product news
- Stories already covered today
- Anything where you cannot cite a verifiable URL from Google Search results

## ABSOLUTE ACCURACY RULES
- NEVER fabricate a URL. If you cannot cite a real URL from search results, output `QUIET`.
- NEVER invent products, partnerships, or funding rounds.

## Already covered (do not repeat)
{seen_entities_str}

## Already posted URLs (do not repeat)
{seen_urls_str}

## Decision logic
1. Search Google for fresh news (last 3 hours).
2. Verify URL exists in your search results.
3. Score: would Harvinder need to know this today?
4. If yes for AT LEAST ONE candidate: produce the post below.
5. If no: output exactly the single token `QUIET`.

## Post format (Slack mrkdwn)
```
DROP · GAMECHANGER · <MON DD HH:MM IST>
─────────────────────────────
```
*<Bold one-sentence headline. Period at end.>*
<Two sentences of fact. Numbers and proper nouns. No hedging.>

> _Take:_ <one sentence Commenda-specific implication.>

↳ <https://full-url|domain/path>

## Hard rules
- NO em-dashes.
- Output EITHER the post OR `QUIET`. Nothing else.

OUTPUT NOW.
"""
    resp = gemini_chat(prompt, with_search=True).strip()
    if resp.upper().startswith("QUIET") or len(resp) < 50:
        print("No gamechanger; staying silent.")
        return

    # URL validation: extract URLs from the post, drop the post if any are broken
    urls = URL_RE.findall(resp)
    bad = [u for u in urls if not url_works(u.rstrip(">,.;:!?)"))]
    if bad:
        print(f"Dropping post, broken URLs: {bad}")
        return

    result = slack_post(resp)
    print(f"Drop posted: ts={result.get('ts')}")


if __name__ == "__main__":
    main()
