"""Gamechanger Drops checker. Runs M-F at 10/13/16/19 IST. Silent unless material news."""
from lib import (
    gemini_chat, slack_post, slack_read_channel, extract_dedup,
    get_today_context, CHANNEL_ID,
)


def main():
    ctx = get_today_context()
    msgs = slack_read_channel(limit=50, days=14)
    dedup = extract_dedup(msgs)
    seen_urls_str = "\n".join(f"- {u}" for u in sorted(dedup["urls"])[:200]) or "(none)"

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
- Listicles
- "Trend pieces" without product news
- Stories that are <3 hours old but already covered today

## Already posted URLs (do not repeat)
{seen_urls_str}

## Decision logic
1. Search Google for fresh news (last 3 hours). Run 5-6 queries.
2. Verify nothing is in the dedup list.
3. Score: would Harvinder need to know about this today to do his job better?
4. If yes for AT LEAST ONE candidate: produce a post in the format below.
5. If no candidates pass: output exactly the single token `QUIET` and nothing else.

## Post format (Slack mrkdwn)
```
DROP · GAMECHANGER · <MON DD HH:MM IST>
─────────────────────────────
```
*<Bold one-sentence headline. Period at end.>*
<Two sentences of fact. Numbers and proper nouns. No hedging.>

> _Take:_ <one sentence Commenda-specific implication.>

↳ <[domain/path](url)>

## Hard rules
- NO em-dashes.
- Output EITHER the post (format above) OR exactly `QUIET`. Nothing else, no preamble.

OUTPUT NOW.
"""
    resp = gemini_chat(prompt, with_search=True).strip()
    if resp.upper().startswith("QUIET") or len(resp) < 50:
        print("No gamechanger; staying silent.")
        return
    result = slack_post(resp)
    print(f"Drop posted: ts={result.get('ts')}")


if __name__ == "__main__":
    main()
