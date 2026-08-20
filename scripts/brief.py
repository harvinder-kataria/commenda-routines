"""Daily Commenda AM Brief. Runs M-F 8 AM IST."""
import json
import re
from lib import (
    gemini_chat_with_sources, slack_post, slack_read_channel, extract_dedup,
    get_today_context, regional_lean_for_day, url_works, extract_domain,
    resolve_grounding_domains, resolve_url, CHANNEL_ID, VERTEX_REDIRECT,
)


def build_prompt(ctx, lean, dedup):
    seen_urls_str = "\n".join(f"- {u}" for u in sorted(dedup["urls"])[:150]) or "(none yet)"
    seen_entities_str = ", ".join(dedup["entities"][:60]) or "(none yet)"
    seen_headlines_str = "\n".join(f"- {h}" for h in dedup["headlines"][:40]) or "(none yet)"
    return f"""You are researching today's "Commenda AM Brief" for Harvinder, a CPA at Commenda focused on US corporate tax service delivery (1120, 1120-F, K-2/K-3) and Commenda's accounting Ops layer.

TODAY: {ctx['date_str']} ({ctx['weekday_name']})
REGIONAL LEAN: {lean}

Use Google Search to find FRESH news. Return findings as a single JSON object. Python formats the brief, you only provide the data.

## ABSOLUTE ACCURACY RULES (CRITICAL)
- NEVER fabricate URLs. The "url" field MUST be a URL that appeared in your Google Search results.
- The system rejects any item whose URL domain is not in the list of domains Google Search actually visited.
- NEVER invent product names, company names, funding amounts, customer lists, or partnerships.
- If you cannot find at least 3 verifiable items, return fewer items.

## RELEVANCE GATE (CRITICAL: filters what publishes)

Every item in "items" MUST have a concrete Commenda hook. The "commenda_hook" field, one sentence, must name ONE of:
- A Commenda service line affected (1120 prep, 1120-F, K-2/K-3, multi-entity consolidation, intercompany eliminations, month-end close, transfer pricing, indirect tax, entity management, cross-border compliance)
- A Commenda client profile affected (venture-backed SaaS with foreign subs, mid-market US corporations with cross-border ops, US-headquartered clients with Indian subsidiaries, PE-owned roll-ups, etc.)
- A partner or BD angle (Rillet implementation partnership, Big 4 client-poach angle, referral flow shift)

Vague hooks like "may affect the accounting industry" or "worth watching" are NOT concrete. If you cannot name a concrete hook, do NOT include the item in "items". Move it to "archived" with a short reason.

## INDIVIDUAL-ONLY TAX ITEMS (SPECIAL INVERSION)

Items whose ONLY affected taxpayer is a natural person (individual sole traders, individual landlords, personal income tax rates, individual filing deadlines, personal allowances, self-assessment mechanics) MUST BE ARCHIVED unless there is a clear DOWNSTREAM CORPORATE or FIRM-CAPACITY hook stated explicitly in the take.

Valid firm-capacity or downstream hook examples:
- "UK accounting firms losing capacity to handle corporate work" (for MTD-ITSA)
- "Personal rate change triggers owner-comp restructuring for pass-through corporations"
- "Sole-trader displacement creates BD flow for corporate structuring services"

For THIS class of items ONLY, invert the standing "when in doubt, publish" rule: when in doubt on an individual-only item, ARCHIVE it. Everywhere else, keep the "when in doubt, publish" bias intact.

## TEST CASES (calibration)

- UK MTD ITSA rollout to sole traders and landlords → ARCHIVE. Reason: "individual-only, no firm-capacity hook stated." Only publish if the hook "UK accounting firms losing capacity to handle corporate work" is real and appears in the take.
- France B2B e-invoicing mandate → PUBLISH. Reason: indirect tax, affects business entities, direct ops impact on multi-country clients with French subsidiaries.
- Personal income tax rate change (any jurisdiction) → ARCHIVE. Only publish if a specific downstream corporate action is stated (e.g., pass-through owner-comp restructuring).
- US corporate tax rate change → PUBLISH. Direct 1120 impact, universal Commenda client relevance.

## Coverage priorities (in order)
1. AI launches in finance/accounting/tax: Anthropic, OpenAI, Google. Big 4 partnerships and AI rollouts (Deloitte, PwC, EY, KPMG). Vendor AI: Intuit, Xero, QuickBooks, Sage, Zoho, Thomson Reuters, Avalara, Wolters Kluwer.
2. Accounting Tools Watch (every brief must include at least one item with category "TOOL"). Watchlist: Rillet, Puzzle, DualEntry, Numeric, Campfire, Inkle, Pilot, Tola, Sage Intacct, Anrok, Zamp, Column Tax, Onshore, Combinely, Black Ore, Aiwyn, Karbon, Brex, Mercury, Ramp, FloQast, BlackLine, Trullion, Vic.ai.
3. Corp tax tech: return automation, e-filing, IRS / HMRC / MCA / SAT / ICAI tech announcements, tax provision tools, AI tax-prep.
4. Service-delivery and ops tech for accounting firms.
5. Commenda-adjacent competitors in multi-entity, global compliance, entity management.
6. Direct tax + accounting reporting (category "REPORTING") — INCLUDE ONE ITEM ONLY WHEN MATERIAL:
   - IRS form or schedule changes affecting 1120, 1120-F, K-2, K-3
   - IRS revenue procedures, rulings, or notices materially affecting corporate tax
   - FASB / IASB / PCAOB / SEC standard changes with corporate reporting impact
   - International tax developments: Pillar 2 / GloBE country implementations, BEAT, Section 174, Section 163(j), CbCR
   - Cross-border reporting mandate shifts: EU CSRD, India ICAI major standards, Mexico CFDI schema, UK MTD for BUSINESSES only (not ITSA/individuals)
   - MUST be national or international significance. Skip niche state-level rules.
   - Do NOT force one every day.

## Geography
US-heavy baseline. Today's regional lean: {lean} For REPORTING, US federal takes priority; international only if it affects US multinationals or Commenda's cross-border book.

## Freshness and anti-repetition (CRITICAL)
- HARD CUTOFF: only news from the last 36 hours. Monday brief may include Fri-Mon to bridge weekend.
- Already covered companies/topics in the last 14 days are listed below. Do NOT re-cover unless GENUINELY NEW development in the last 36 hours.
- Do NOT include URLs from the recently-posted list.

## Recently covered companies (DO NOT REPEAT unless new development)
{seen_entities_str}

## Recently posted headlines (avoid near-duplicates)
{seen_headlines_str}

## Recently posted URLs (DO NOT REUSE)
{seen_urls_str}

## OUTPUT: JSON ONLY

Return EXACTLY this JSON structure. No prose before or after, no code fences.

{{
  "items": [
    {{
      "category": "REPORTING",
      "entity": "IRS",
      "date": "JUL 15",
      "headline": "IRS releases revised Schedule K-3 with new Pillar 2 disclosure requirements.",
      "body": "The draft schedule adds three new columns for GloBE income adjustments effective for tax year 2026 filings. Public comment period runs through August 30.",
      "take": "Multi-entity 1120 clients with foreign subs will need K-3 updates. Front-load the workpaper build.",
      "client_q": "Do we need to file the new K-3 columns for tax year 2025 or only 2026?",
      "commenda_hook": "Multi-entity 1120 clients with foreign subs need K-3 workpaper updates ahead of TY 2026 filings.",
      "url": "https://www.irs.gov/pub/irs-drop/some-notice",
      "url_display": "irs.gov/pub/irs-drop/some-notice"
    }}
  ],
  "archived": [
    {{"headline": "UK MTD ITSA rollout begins for sole traders over 50k", "reason": "individual-only, no firm-capacity hook stated"}}
  ],
  "watching": ["Pillar 2 US implementation timeline", "Section 174 R&E amortization repeal bill", "Anthropic finance-agents cookbook", "PCAOB AI audit standard draft"],
  "skipped": ["Generic AI tax tools listicles", "Routine IRS season-prep posts", "Recycled Big 4 trend pieces"]
}}

## Field rules
- "category": exactly ONE of: AI, DEAL, PRODUCT, DISTRIBUTION, TAX AUTO, BIG 4, COMPETITOR, REGULATORY, REPORTING, TOOL, INDIA, UK, MEXICO, EU, LATAM.
- "entity": uppercase COMPANY, agency, or standard-setter name.
- "date": "MON DD" (e.g., "JUL 15").
- "headline": one sentence, declarative, period at end, plain text.
- "body": two sentences, ≤ 45 words combined.
- "take": one sentence, ≤ 30 words. For individual-only tax items, the firm-capacity or downstream-corporate hook MUST be stated here.
- "client_q": OPTIONAL. Include ONLY on items likely to trigger a client question. ≤ 25 words. Max 2 items per brief.
- "commenda_hook": REQUIRED on every item. One sentence naming a concrete service line, client profile, or partner/BD angle. Vague hooks disqualify the item.
- "url": use the URL exactly as it appears in your Google Search results.
- "url_display": short "domain/path" form.
- "archived": REQUIRED list, can be empty. Items considered but not published, each with keys "headline" and "reason".

## Length
- "items": 5 typical, 6-7 heavy news, 3-4 quiet. Never 8+.
- Every brief must include at least one item with category "TOOL".
- REPORTING is opt-in based on news day.

## Suggested search queries (rotate, mix)
Tech / tools:
- "Anthropic Claude finance accounting [current month year]"
- "Big 4 AI agent announcement [current month year]"
- "Intuit Xero Sage AI news [current month year]"
- "accounting startup funding [current month year]"
- "AI ERP multi-entity news [current month year]"

Direct tax + reporting (run 1-2 per day):
- "IRS 1120 revenue procedure notice [current year]"
- "IRS K-2 K-3 update [current year]"
- "FASB accounting standards update [current year]"
- "PCAOB standard release [current year]"
- "SEC corporate reporting rule [current year]"
- "Pillar 2 GloBE country implementation [current year]"
- "Section 174 R&E capitalization update [current year]"
- "OECD international tax rules [current year]"

Pending regulations to track in WATCHING (rotate):
- Pillar 2 US implementation status
- Section 174 R&E amortization repeal
- PCAOB AI audit standard drafts
- SEC climate disclosure rule status
- IRS form draft comment periods
- FASB open exposure drafts
- India ICAI upcoming standard changes
- EU CSRD phase-in dates

NO em-dashes anywhere.

OUTPUT JSON NOW.
"""


def format_brief(data, ctx, grounding_domains=None):
    raw_items = data.get("items", [])
    items = []
    python_archived = []

    for it in raw_items:
        url = (it.get("url") or "").strip()
        headline = (it.get("headline") or "").strip()
        hook = (it.get("commenda_hook") or "").strip()

        if VERTEX_REDIRECT in url:
            resolved = resolve_url(url)
            if resolved and VERTEX_REDIRECT not in resolved and resolved.startswith("http"):
                print(f"[resolve] Vertex redirect -> {resolved}")
                url = resolved
                it["url"] = resolved
                dom = extract_domain(resolved)
                if dom and (not it.get("url_display") or VERTEX_REDIRECT in (it.get("url_display") or "")):
                    it["url_display"] = dom
            else:
                python_archived.append({"headline": headline, "reason": "vertex redirect unresolvable"})
                continue

        url_domain = extract_domain(url)

        if not url_works(url):
            python_archived.append({"headline": headline, "reason": "URL unreachable"})
            continue

        if grounding_domains and url_domain not in grounding_domains:
            python_archived.append({"headline": headline, "reason": f"domain {url_domain} not in grounding sources"})
            continue

        if not hook:
            python_archived.append({"headline": headline, "reason": "no commenda_hook stated (relevance gate)"})
            continue

        items.append(it)

    all_archived = list(data.get("archived", []) or []) + python_archived

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
        client_q = (it.get("client_q") or "").strip()
        hook = (it.get("commenda_hook") or "").strip()
        url = (it.get("url") or "").strip()
        url_display = (it.get("url_display") or url).strip()

        lines = [
            f"`{i:02d} ▎ {cat} · {ent} ▎ {date}`",
            f"*{headline}*",
            body,
            "",
            f"> _Take:_ {take}",
        ]
        if client_q:
            lines.append(f"> _Client Q:_ {client_q}")
        if hook:
            lines.append(f"_Hook: {hook}_")
        lines.append(f"↳ <{url}|{url_display}>")
        blocks.append("\n".join(lines))

    separator = "\n\n─────────────────────────────\n\n"
    stories = separator.join(blocks)

    watching = " · ".join(data.get("watching", [])) or "(quiet)"
    skipped = " · ".join(data.get("skipped", [])) or "(none)"

    archived_lines = []
    for a in all_archived:
        hl = (a.get("headline") or "").strip()
        reason = (a.get("reason") or "").strip()
        if hl and reason:
            archived_lines.append(f"{hl} ({reason})")
    archived_str = " · ".join(archived_lines[:6]) or "(none)"

    footer = (
        "```\n"
        f"WATCHING  {watching}\n"
        f"ARCHIVED  {archived_str}\n"
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

    raw, sources = gemini_chat_with_sources(build_prompt(ctx, lean, dedup), with_search=True)
    print(f"[grounding] {len(sources)} source URIs from Google Search")

    try:
        data = parse_gemini_json(raw)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw Gemini output:\n{raw[:2000]}")
        raise

    grounding_domains = resolve_grounding_domains(sources)
    print(f"[grounding] {len(grounding_domains)} unique source domains: {sorted(grounding_domains)}")

    brief_text = format_brief(data, ctx, grounding_domains=grounding_domains)
    if brief_text is None:
        print("No items survived validation; not posting today.")
        return

    result = slack_post(brief_text)
    print(f"Brief posted: ts={result.get('ts')}, channel={CHANNEL_ID}")


if __name__ == "__main__":
    main()
