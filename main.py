#!/usr/bin/env python3
"""
Weekly Sport Science & Sport Analytics Reading
----------------------------------------------
Runs once per week (via cron / GitHub Actions). Makes ONE Anthropic API call
that uses the web_search tool to find:
  1. one peer-reviewed sport science paper published in the last 7 days
  2. one sport data analytics tool/project released or updated in the last 7 days
Claude returns strict JSON; Python builds the HTML email and sends it via SMTP.

Token efficiency notes:
  - Single API call, capped at a few searches (max_uses below).
  - Haiku model (cheap) is enough; formatting is done in Python, not by the model.
  - No conversation state, no agent loop.
"""

import os
import json
import smtplib
import datetime as dt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from anthropic import Anthropic

# ----------------------------------------------------------------------
# Config (everything secret comes from environment variables / GH secrets)
# ----------------------------------------------------------------------
MODEL = os.environ.get("MODEL", "claude-haiku-4-5-20251001")

# Comma-separated list, e.g. "a@x.com,b@y.com"
RECIPIENTS = [e.strip() for e in os.environ["RECIPIENTS"].split(",") if e.strip()]

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ["SMTP_USER"]          # full email address
SMTP_PASS = os.environ["SMTP_PASS"]          # Gmail "app password" or SMTP key
FROM_ADDR = os.environ.get("FROM_ADDR", SMTP_USER)

SUBJECT = "Weekly Sport Science and Sport Analytics Reading"

# ----------------------------------------------------------------------
# 1. Ask Claude (with web search) for this week's two items
# ----------------------------------------------------------------------
def fetch_items():
    today = dt.date.today()
    week_ago = today - dt.timedelta(days=7)

    prompt = f"""Today is {today.isoformat()}. I need exactly two items, both released
between {week_ago.isoformat()} and {today.isoformat()} (the last 7 days only).

ITEM 1 - A peer-reviewed sport science or sport data analytics paper/article.
  Prefer recognized journals (e.g. Journal of Sports Sciences, Int. Journal of
  Sports Physiology and Performance, Sports Medicine, J. of Sports Analytics) or
  reputable preprint servers (SportRxiv, arXiv stat.AP/cs.LG with a sport focus).
  It MUST have a publication or posting date within the last 7 days.

ITEM 2 - A sport data analytics tool, library, dataset, or open-source project.
  Prefer GitHub releases/repos, new packages, or public project launches with a
  release or significant-update date within the last 7 days.

Use web search to verify dates. If you cannot confirm an item is from the last 7
days, search again rather than guessing. Do not fabricate URLs.

Return ONLY a JSON object, no prose, no markdown fences, in exactly this shape:
{{
  "paper":   {{"title": "...", "url": "https://...", "summary": "Two sentences max."}},
  "tool":    {{"title": "...", "url": "https://...", "summary": "Two sentences max."}}
}}
The summary for each must be at most two sentences, factual, in your own words."""

    client = Anthropic()  # reads ANTHROPIC_API_KEY from env
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 6,            # hard cap on searches -> bounded cost
        }],
        messages=[{"role": "user", "content": prompt}],
    )

    # Concatenate any text blocks the model produced, then extract the JSON object.
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in model output:\n{text}")
    return json.loads(text[start:end + 1])


# ----------------------------------------------------------------------
# 2. Build the HTML email body (deterministic, zero extra tokens)
# ----------------------------------------------------------------------
def build_html(items):
    def block(item):
        return (
            f'<p style="margin:0 0 4px 0;">'
            f'<a href="{item["url"]}" style="font-weight:bold;'
            f'color:#0b3d91;text-decoration:none;">{item["title"]}</a></p>'
            f'<p style="margin:0 0 20px 0;">{item["summary"]}</p>'
        )

    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;'
        'line-height:1.5;color:#222;">'
        f'{block(items["paper"])}'
        f'{block(items["tool"])}'
        '</div>'
    )


# ----------------------------------------------------------------------
# 3. Send via SMTP
# ----------------------------------------------------------------------
def send_email(html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT
    msg["From"] = FROM_ADDR
    msg["To"] = ", ".join(RECIPIENTS)
    msg.attach(MIMEText("Open in an HTML-capable client.", "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(FROM_ADDR, RECIPIENTS, msg.as_string())


def main():
    items = fetch_items()
    # minimal validation so a bad week fails loudly instead of sending junk
    for key in ("paper", "tool"):
        for field in ("title", "url", "summary"):
            if not items.get(key, {}).get(field):
                raise ValueError(f"Missing {key}.{field} in model output: {items}")
    send_email(build_html(items))
    print("Sent:", json.dumps(items, indent=2))


if __name__ == "__main__":
    main()
