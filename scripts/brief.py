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
- DO NOT REPEAT anything from the URLs already posted (see below). A story can only resurface if there is a genuinely new development.
- Items > 48 hours old need a strong fresh angle.
- Quiet days stay quiet. Post fewer items rather than padding with stale content.

## Recently posted URLs (DO NOT REUSE without a fresh angle)
{seen_urls_str}

## Format: SLACK MRKDWN (NOT GitHub Markdown)

Slack mrkdwn tokens:
- *bold* (single asterisks, not double)
- _italic_ (single underscores)
- `inline code` (backticks)
- ```fenced code blocks``` (triple backticks)
- > blockquote (greater-than at start of line)
- Slack-native link: <https://full.url|display text>

CRITICAL link rule: use ONLY Slack format <url|text>. NEVER use Markdown [text](url). NEVER include grounding redirect URLs from vertexaisearch.cloud.google.com. Always cite the original publisher URL.

### Masthead (fenced code block at top of brief)
```
COMMENDA · AM BRIEF
─────────────────────────────
DATE   {ctx['date_display']}
ITEMS  <N>
SCOPE  <2-4 category tokens, dot-separated, all caps>
```

### Story block: EACH ELEMENT ON ITS OWN LINE WITH REAL NEWLINES

The kicker, headline, body, take, and link are SEPARATE LINES. Use real \\n between them. Do NOT collapse onto one line.

Pattern (one story):

`NN ▎ CATEGORY · ENTITY ▎ MON DD`
*Bold one-sentence headline ending with a period.*
Two short sentences of fact. Numbers and proper nouns first. No hedging.

> _Take:_ One sentence Commenda-specific implication. Optional second short sentence.
↳ <https://full-url.com|domain.com/path>

After each story, a separator line of box-drawing characters:
─────────────────────────────

### Complete worked example (follow EXACTLY, including all newlines, bold, blockquote, italic)

`01 ▎ AI · ANTHROPIC ▎ MAY 11`
*Anthropic ships ten finance agent templates and Claude Opus 4.7.*
Pre-built agents cover GL reconciler, month-end closer, statement auditor, and KYC screener. Customers include Citadel, FIS, BNY, Mizuho, and Travelers.

> _Take:_ Two templates land directly on Commenda's ops layer. Worth pressure-testing whether to wrap or extend.
↳ <https://www.anthropic.com/news/finance-agents|anthropic.com/news/finance-agents>

─────────────────────────────

### Footer (fenced code block at bottom of brief)
```
WATCHING  <item> · <item> · <item>
SKIPPED   <category> · <category> · <category>
```

### Taxonomy (pick exactly one kicker tag per item)
`AI` · `DEAL` · `PRODUCT` · `DISTRIBUTION` · `TAX AUTO` · `BIG 4` · `COMPETITOR` · `REGULATORY` · `TOOL` · `INDIA` · `UK` · `MEXICO` · `EU` · `LATAM`

## Hard rules
- NO em-dashes anywhere. Use colons, periods, commas, parentheses.
- Headline: single asterisks for bold, period at end, declarative.
- Body: exactly two sentences, ≤ 45 words combined.
- Take: blockquote starting with `>`, italic `_Take:_` prefix, ≤ 30 words total.
- Link: Slack native `<url|display>` format ONLY. No Markdown. No grounding redirects. Use the original publisher URL.
- Every line of a story is its OWN LINE. No concatenation.
- Item count in masthead equals stories below.
- Zero emoji in the body. The kicker tag handles categorization.
- Length: 5 typical, 6-7 heavy news days, never 8+. Never pad.
- EVERY brief includes at least one `TOOL` item with maturity and Commenda-fit explicit.

## Process
1. Use Google Search to find news from the last 24-36 hours across the coverage priorities. Run varied queries (Anthropic, Big 4, Intuit/Xero/Sage AI, accounting startup funding, AI ERP multi-entity, named-tool watchlist, plus today's regional queries based on lean).
2. Verify freshness. Reject older items unless strong fresh angle.
3. Cross-check against recently-posted URLs. SKIP duplicates.
4. Draft the brief in the exact format shown in the worked example. Pay extreme attention to: line breaks between every story element, bold asterisks on headline, blockquote on Take, italic on _Take:_ prefix, Slack-native link format with original publisher URL.
5. Output ONLY the brief text. No preamble, no explanation, no outer code fences wrapping the whole brief.

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
