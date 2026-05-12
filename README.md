# Commenda AM Brief

Generates and posts a daily accounting/finance/tax tech brief to Slack `#commenda-am-brief`.

- Daily Brief: Mon-Fri 8:00 AM IST
- Saturday Deep Dive: Sat 10:00 AM IST
- Gamechanger Drops: Mon-Fri 10/13/16/19 IST, silent unless material news

## Setup

1. Add repository secrets at Settings → Secrets and variables → Actions:
   - `SLACK_BOT_TOKEN` (Commenda AM bot token, starts `xoxb-`)
   - `GEMINI_API_KEY` (Google AI Studio free tier)
2. Trigger Daily Brief manually once from Actions tab to verify.

## Tweaking

- Channel / canvas / user IDs in `scripts/lib.py`.
- Editorial rules and format in `scripts/brief.py` `build_prompt()`.
- Saturday themes in `scripts/deepdive.py` `THEMES`.
- Regional rotation in `scripts/lib.py` `regional_lean_for_day()`.
