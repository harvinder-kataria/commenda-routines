"""Saturday Deep Dive. Runs Sat 10 AM IST."""
from datetime import datetime
from lib import (
    gemini_chat_with_sources, slack_post, get_today_context,
    resolve_grounding_domains, CHANNEL_ID,
)

THEMES = [
    "Tools landscape: compare 3 multi-entity accounting platforms (Rillet vs DualEntry vs Sage Intacct or similar). Which solves which client profile.",
    "Regional landscape: India accounting/tax tooling state of play. Inkle, ICAI digital, GST automation, who's winning what.",
    "Strategic move analysis: pick the biggest accounting/finance AI story of the week and unpack what it means for service-delivery firms.",
    "Regulatory deep-dive: a tech-relevant regulation (US BOI, EU AML/CTF, India GST changes, Pillar 2 implementation) and how it reshapes tooling vendors.",
    "Big 4 deep-dive: pick one Big 4's AI rollout and what's measurable vs marketing. EY/PwC/Deloitte/KPMG rotates each cycle.",
    "Tooling category deep-dive: month-end close automation, OR AP/AR automation, OR tax provision software. Tools, maturity, gaps.",
    "Direct tax reporting deep-dive: unpack a material 1120-relevant change (Section 174, K-2/K-3, Pillar 2, FASB standard). Practical impact on service delivery.",
]


def week_theme():
    week = datetime.utcnow().isocalendar()[1]
    return THEMES[week % len(THEMES)]


def build_sources_block(grounding_domains):
    if not grounding_domains:
        return ""
    lines = ["", "*Sources*"]
    for d in sorted(grounding_domains)[:12]:
        lines.append(f"↳ <https://{d}|{d}>")
    return "\n".join(lines)


def main():
    ctx = get_today_context()
    theme = week_theme()
    prompt = f"""Write a Saturday Deep Dive for Harvinder, a CPA at Commenda. Long-form (700-1100 words). Format with Slack mrkdwn (*bold*, _italic_, > blockquotes, fenced code blocks).

DATE: {ctx['date_str']}
THIS WEEK'S THEME: {theme}

Use Google Search to gather current, well-sourced material. Cite specific companies, dollar figures, customers, dates. No hedging.

## ACCURACY RULES (CRITICAL)
- NEVER fabricate URLs, company names, products, dollar figures, or customer lists.
- Only cite facts that appear in your Google Search results.
- Do not embed URLs inline in the body. The script appends a Sources block automatically from real search domains.

## Structure
- Title: `*Saturday Deep Dive · {ctx['date_display']}*`
- Hook: 2-3 lines that frame the angle.
- Body: 3-4 sections with `*Section heading*` style. Specific facts, named comparisons, real numbers.
- "What it means for Commenda" section at the end: 3-5 bullets, tied to multi-entity / multi-country / 1120 service-delivery / Big-4-displacement angles.

## Hard rules
- NO em-dashes.
- Slack mrkdwn only, no HTML, no Markdown link format.
- Do NOT append your own Sources block or list of URLs. The script will add one from real grounding data.
- Concrete over abstract. Numbers over adjectives.
- Output the deep dive directly. No preamble.

OUTPUT NOW.
"""
    text, sources = gemini_chat_with_sources(prompt, with_search=True)
    print(f"[grounding] {len(sources)} source URIs from Google Search")
    grounding_domains = resolve_grounding_domains(sources)
    print(f"[grounding] {len(grounding_domains)} unique source domains: {sorted(grounding_domains)}")

    sources_block = build_sources_block(grounding_domains)
    full_text = text.strip() + ("\n" + sources_block if sources_block else "")

    result = slack_post(full_text)
    print(f"Deep dive posted: ts={result.get('ts')}")


if __name__ == "__main__":
    main()
