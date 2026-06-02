"""Daily Commenda AM Brief. Runs M-F 8 AM IST."""
import json
import re
from lib import (
    gemini_chat, slack_post, slack_read_channel, extract_dedup,
    get_today_context, regional_lean_for_day, url_works, CHANNEL_ID,
)


def build_prompt(ctx, lean, dedup):
    seen_urls_str = "\n".join(f"- {u}" for u in sorted(dedup["urls"])[:150]) or "(none yet)"
    seen_entities_str = ", ".join(dedup["entities"][:60]) or "(none yet)"
    seen_headlines_str = "\n".join(f"- {h}" for h in dedup["headlines"][:40]) or "(none yet)"
    return f"""You are researching today's "Commenda AM Brief" for Harvinder, a CPA at Commenda focused on US corporate tax service delivery and Commenda's accounting Ops layer.

TODAY: {ctx['date_str']} ({ctx['weekday_name']})
REGIONAL LEAN: {lean}

Use Google Search to find FRESH news. Return findings as a single JSON object. Python will format the brief, you only provide the data.

## ABSOLUTE ACCURACY RULES (CRITICAL)
- NEVER fabricate URLs. The "url" field MUST be a URL that appeared in your Google Search results. If you cannot cite a real URL from your search results for an item, OMIT THAT ITEM.
- NEVER invent product names, company names, funding amounts, customer lists, or partnerships. If you are not certain something exists, leave it out.
- NEVER cite a URL just because it "looks plausible." A made-up URL is worse than missing news.
- If you cannot find at least 3 verifiable items today, return fewer items. Quiet days stay quiet.

## Coverage priorities (in order)
1. AI launches in finance/accounting/tax: Anthropic, OpenAI, Google. Big 4 partnerships and AI rollouts (Deloitte, PwC, EY, KPMG). Vendor AI: Intuit, Xero, QuickBooks, Sage, Zoho, Thomson Reuters, Avalara, Wolters Kluwer.
2. Accounting Tools Watch (every brief must include at least one item with category "TOOL"). Watchlist: Rillet, Puzzle, DualEntry, Numeric, Campfire, Inkle, Pilot, Tola, Sage Intacct, Anrok, Zamp, Column Tax, Onshore, Combinely, Black Ore, Aiwyn, Karbon, Brex, Mercury, Ramp, FloQast, BlackLine, Trullion, Vic.ai.
3. Corp tax tech: return automation, e-filing, IRS / HMRC / MCA / SAT / ICAI tech announcements, tax provision tools, AI tax-prep.
4. Service-delivery and ops tech for accounting firms.
5. Commenda-adjacent competitors in multi-entity, global compliance, entity management.

## Geography
US-heavy baseline. Today's regional lean: {lean} Skip pure GAAP/regulatory updates unless tied to tech adoption.

## Freshness and anti-repetition (CRITICAL)
- HARD CUTOFF: only news from the last 36 hours. Monday brief may include Fri-Mon to bridge weekend.
- Already covered companies in the last 14 days are listed below. Do NOT cover a listed company unless you have a GENUINELY NEW development to cite (new partner, new product feature, new funding round, regulatory response, leadership change, customer win). "The company is still relevant" is NOT enough.
- Do NOT include URLs from the recently-posted list.
- Items > 48 hours old need a strong fresh angle.
- Quiet days stay quiet. Output 3-4 items if needed. Never pad with stale content.

## Recently covered companies (DO NOT REPEAT unless new development)
{seen_entities_str}

## Recently posted headlines (avoid near-duplicates)
{seen_headlines_str}

## Recently posted URLs (DO NOT REUSE)
{seen_urls_str}

## OUTPUT: JSON ONLY

Return EXACTLY this JSON structure. No prose before or after, no code fences, no explanation.

{{
  "items": [
    {{
      "category": "AI",
      "entity": "ANTHROPIC",
      "date": "MAY 11",
      "headline": "Anthropic ships ten finance agent templates and Claude Opus 4.7.",
      "body": "Pre-built agents cover GL reconciler, month-end closer, statement auditor, and KYC screener. Customers include Citadel, FIS, BNY, Mizuho, and Travelers.",
      "take": "Two templates land directly on Commenda's ops layer. Worth pressure-testing whether to wrap or extend.",
      "url": "https://www.anthropic.com/news/finance-agents",
      "url_display": "anthropic.com/news/finance-agents"
    }}
  ],
  "watching": ["Anthropic finance-agents cookbook", "KPMG Tax AI Accelerator", "Sage Finance Intelligence Agent"],
  "skipped": ["Generic AI tax tools listicles", "Routine IRS season-prep posts", "Recycled Big 4 trend pieces"]
}}

## Field rules
- "category": exactly ONE of: AI, DEAL, PRODUCT, DISTRIBUTION, TAX AUTO, BIG 4, COMPETITOR, REGULATORY, TOOL, INDIA, UK, MEXICO, EU, LATAM.
- "entity": uppercase COMPANY name (ANTHROPIC, INTUIT, EY, RILLET, ZAMP). Never a category, never a region.
- "date": "MON DD" (e.g., "MAY 11"). Must be the actual date of the news.
- "headline": one sentence, declarative, ends with a period, plain text only (no asterisks, no formatting).
- "body": exactly two sentences, ≤ 45 words combined, factual.
- "take": one sentence, ≤ 30 words, Commenda implication. No "Take:" prefix.
- "url": ORIGINAL publisher URL, FROM YOUR SEARCH RESULTS. NEVER fabricated. NEVER a Google Search redirect. Verify it appears in your grounding search results before including.
- "url_display": short readable form, "domain/path".
- "watching": 3-4 short tags of ongoing storylines.
- "skipped": 3-5 categories of noise filtered out.

## Length
- "items": 5 typical, 6-7 on heavy news days, 3-4 on quiet days. Never 8 or more. Never pad.
- Every brief must include at least one item with category "TOOL".

NO em-dashes (`—`) anywhere in any field.

## Process
1. Run multiple Google Search queries for the last 36 hours of news across coverage priorities.
2. For each candidate item: confirm the URL exists in your search results. Discard if you can't confirm.
3. Confirm the item is NOT in the recently posted/covered lists (unless new development).
4. Construct the JSON object.
5. Output ONLY the JSON.

OUTPUT JSON NOW.
"""


def format_brief(data, ctx):
    raw_items = data.get("items", [])
    items = []
    for it in raw_items:
        url = (it.get("url") or "").strip()
        if not url_works(url):
            print(f"[url-check] DROPPING item, URL not reachable: {url} (headline: {it.get('headline', '')[:60]})")
            continue
        items.append(it)

    n = len(items)
    if n == 0:
        return None

    scope_seen = []
    for it in items:
        cat = (it.get("category") or "MISC").strip().upper()
        if cat and cat not in scope_seen:
            scope_seen.append(cat)
    scope = " · ".join(scope_seen[:5])

    masthead = (
        "```\n"
        "COMMENDA · AM BRIEF\n"
        "─────────────────────────────\n"
        f"DATE   {ctx['date_display']}\n"
        f"ITEMS  {n}\n"
        f"SCOPE  {scope}\n"
        "```"
    )

    blocks = []
    for i, it in enumerate(items, 1):
        cat = (it.get("category") or "MISC").strip().upper()
        ent = (it.get("entity") or "UNKNOWN").strip().upper()
        date = (it.get("date") or "").strip().upper()
        headline = (it.get("headline") or "").strip()
        body = (it.get("body") or "").strip()
        take = (it.get("take") or "").strip()
        url = (it.get("url") or "").strip()
        url_display = (it.get("url_display") or url).strip()
        block = (
            f"`{i:02d} ▎ {cat} · {ent} ▎ {date}`\n"
            f"*{headline}*\n"
            f"{body}\n"
            f"\n"
            f"> _Take:_ {take}\n"
            f"↳ <{url}|{url_display}>"
        )
        blocks.append(block)

    separator = "\n\n─────────────────────────────\n\n"
    stories = separator.join(blocks)

    watching = " · ".join(data.get("watching", [])) or "(quiet)"
    skipped = " · ".join(data.get("skipped", [])) or "(none)"
    footer = (
        "```\n"
        f"WATCHING  {watching}\n"
        f"SKIPPED   {skipped}\n"
        "```"
    )

    return f"{masthead}\n\n{stories}\n\n{footer}"


def parse_gemini_json(raw):
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
    raw = re.sub(r'\n?```\s*$', '', raw)
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


def main():
    ctx = get_today_context()
    lean = regional_lean_for_day(ctx["weekday"])
    msgs = slack_read_channel(limit=100, days=14)
    dedup = extract_dedup(msgs)
    raw = gemini_chat(build_prompt(ctx, lean, dedup), with_search=True)
    try:
        data = parse_gemini_json(raw)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw Gemini output:\n{raw[:2000]}")
        raise
    brief_text = format_brief(data, ctx)
    if brief_text is None:
        print("No items survived URL validation; not posting today.")
        return
    result = slack_post(brief_text)
    print(f"Brief posted: ts={result.get('ts')}, channel={CHANNEL_ID}")


if __name__ == "__main__":
    main()
