"""Saturday Deep Dive. Runs Sat 10 AM IST."""
from datetime import datetime
from lib import gemini_chat, slack_post, get_today_context, CHANNEL_ID

THEMES = [
    "Tools landscape: compare 3 multi-entity accounting platforms (Rillet vs DualEntry vs Sage Intacct or similar). Which solves which client profile.",
    "Regional landscape: India accounting/tax tooling state of play. Inkle, ICAI digital, GST automation, who's winning what.",
    "Strategic move analysis: pick the biggest accounting/finance AI story of the week and unpack what it means for service-delivery firms.",
    "Regulatory deep-dive: a tech-relevant regulation (US BOI, EU AML/CTF, India GST changes) and how it reshapes tooling vendors.",
    "Big 4 deep-dive: pick one Big 4's AI rollout and what's measurable vs marketing. EY/PwC/Deloitte/KPMG rotates each cycle.",
    "Tooling category deep-dive: month-end close automation, OR AP/AR automation, OR tax provision software. Tools, maturity, gaps.",
]


def week_theme():
    week = datetime.utcnow().isocalendar()[1]
    return THEMES[week % len(THEMES)]


def main():
    ctx = get_today_context()
    theme = week_theme()
    prompt = f"""Write a Saturday Deep Dive for Harvinder, a CPA at Commenda. Long-form (700-1100 words). Format with Slack mrkdwn (*bold*, _italic_, > blockquotes, fenced code blocks).

DATE: {ctx['date_str']}
THIS WEEK'S THEME: {theme}

Use Google Search to gather current, well-sourced material. Cite specific companies, dollar figures, customers, dates. No hedging.

Structure:
- Title: `*Saturday Deep Dive · {ctx['date_display']}*`
- Hook: 2-3 lines that frame the angle.
- Body: 3-4 sections with `*Section heading*` style. Specific facts, named comparisons, real numbers.
- "What it means for Commenda" section at the end: 3-5 bullets, tied to multi-entity / multi-country / 1120 service-delivery / Big-4-displacement angles.
- Citations: inline `↳ [domain/path](url)` links scattered through, plus a "Sources" block at the bottom with 4-6 links.

Hard rules:
- NO em-dashes anywhere.
- Slack mrkdwn only.
- Concrete over abstract. Numbers over adjectives.
- Output the deep dive directly. No preamble.

OUTPUT NOW.
"""
    text = gemini_chat(prompt, with_search=True)
    result = slack_post(text)
    print(f"Deep dive posted: ts={result.get('ts')}")


if __name__ == "__main__":
    main()
