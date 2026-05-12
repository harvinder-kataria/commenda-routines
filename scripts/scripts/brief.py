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
