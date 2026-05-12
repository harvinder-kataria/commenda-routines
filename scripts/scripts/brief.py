"""Daily Commenda AM Brief. Runs M-F 8 AM IST."""
from lib import (
    gemini_chat, slack_post, slack_read_channel, extract_dedup,
    get_today_context, regional_lean_for_day, CHANNEL_ID,
)


def build_prompt(ctx, lean, seen_urls):
    seen_urls_str = "\n".join(f"- {u}" for u in sorted(seen_urls)[:200]) or "(none yet)"
    return f"""You are drafting today's "Commenda AM Brief", a daily operator briefing for Harvinder, a CPA at Commenda focused on US corporate tax service delivery and Commenda's accounting Ops layer.

TODAY: {ctx['date_str']} ({ctx['weekday_name']})
REGIONAL LEAN: {lean}

## Coverage priorities (in order)
1. AI launches in finance/accounting/tax: Anthropic, OpenAI, Google. Big 4 partnerships and AI rollouts (Deloitte, PwC, EY, KPMG). Vendor AI: Intuit, Xero, QuickBooks, Sage, Zoho, Thomson Reuters, Avalara, Wolters Kluwer.
2. Accounting Tools Watch (every brief must include at least one TOOL item). Named watchlist: Rillet, Puzzle, DualEntry, Numeric, Campfire, Inkle, Pilot, Tola, Sage Intacct, Anrok, Zamp, Column Tax, Onshore, Combinely, Black Ore, Aiwyn, Karbon, Brex, Mercury, Ramp, FloQast, BlackLine, Trullion, Vic.ai.
3. Corp tax tech: return automation, e-filing, IRS / HMRC / MCA / SAT / ICAI tech announcements, tax provision tools, AI tax-prep.
4. Service-delivery and ops tech for accounting firms.
5. Commenda-adjacent competitors in multi-entity, global compliance, entity management.

## Geography
US-heavy baseline. Today's regional lean: {lean} Skip pure GAAP/regulatory updates unless tied to tech adoption.

## Freshness and anti-repetition (CRITICAL)
- HARD CUTOFF: only news from the last 36 hours. Monday brief may include Fri-Mon to bridge weekend.
- DO NOT REPEAT anything from the URLs already posted (see below). A story can only resurface if there is a genuinely new development (new partner, new product, new metric, regulatory response, leadership change, lawsuit, GA milestone, customer win).
- Items > 48 hours old need a strong fresh angle.
- Quiet days stay quiet. Post fewer items rather than padding with stale content.

## Recently posted URLs (DO NOT REUSE without a fresh angle)
{seen_urls_str}

## Format (Slack mrkdwn: *bold*, _italic_, `inline code`, > blockquote, fenced code blocks)

### Masthead (one fenced code block at top)
```
COMMENDA · AM BRIEF
─────────────────────────────
DATE   {ctx['date_display']}
ITEMS  <N>
SCOPE  <2-4 category tokens dot-separated>
```

### Story block (repeat N times)
`<NN> ▎ <CATEGORY · ENTITY> ▎ <MON DD>`
*<One-sentence headline. Action verb. Period at end.>*
<Two short sentences of fact. Numbers and proper nouns first. No hedging.>

> _Take:_ <one sentence Commenda-specific implication. Optional second short sentence.>

↳  <[domain/path](full url)>

Separator between stories: a single line of `─────────────────────────────`

### Footer (one fenced code block at bottom)
```
WATCHING  <item> · <item> · <item>
SKIPPED   <category> · <category> · <category>
```

### Taxonomy (kicker tags, pick exactly one per item)
`AI` · `DEAL` · `PRODUCT` · `DISTRIBUTION` · `TAX AUTO` · `BIG 4` · `COMPETITOR` · `REGULATORY` · `TOOL` · `INDIA` · `UK` · `MEXICO` · `EU` · `LATAM`

## Hard rules
- NO em-dashes anywhere. Use colons, periods, commas, parentheses.
- Headline ends with a period. Declarative, never a question.
- Body: exactly two sentences, ≤ 45 words combined.
- Take: blockquote, ≤ 30 words, leads with `_Take:_`.
- Link: `↳` arrow, link text is `domain/path`.
- Item count in masthead must equal stories below.
- Zero emoji in the body.
- Length: 5 typical, 6-7 heavy news days, never 8+. Never pad.
- EVERY brief includes at least one `TOOL` item with explicit maturity and Commenda-fit.

## Process
1. Use Google Search to find news from the last 24-36 hours across the coverage priorities. Run varied queries (Anthropic, Big 4, Intuit/Xero/Sage AI, accounting startup funding, AI ERP multi-entity, named-tool watchlist news, plus today's regional queries based on lean).
2. Verify freshness. Reject older items unless strong fresh angle.
3. Cross-check against the recently-posted URL list. SKIP duplicates.
4. Draft the brief in the format above.
5. Output ONLY the brief text. No preamble, no explanation, no markdown fences wrapping the whole thing.

OUTPUT THE BRIEF NOW.
"""


def main():
    ctx = get_today_context()
    lean = regional_lean_for_day(ctx["weekday"])
    msgs = slack_read_channel(limit=50, days=14)
    dedup = extract_dedup(msgs)
    brief = gemini_chat(build_prompt(ctx, lean, dedup["urls"]), with_search=True)
    result = slack_post(brief)
    print(f"Brief posted: ts={result.get('ts')}, channel={CHANNEL_ID}")


if __name__ == "__main__":
    main()
