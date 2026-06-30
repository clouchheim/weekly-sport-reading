# Weekly Sport Science & Sport Analytics Reading

Sends one email every Monday morning with one recent peer-reviewed paper and one
recent sport analytics tool/project, both from the last 7 days.

## How it works
1. A scheduled GitHub Action runs `main.py` every Monday.
2. `main.py` makes ONE Anthropic API call that uses web search to find the two
   items and return them as JSON.
3. Python builds the HTML email and sends it over SMTP.

Formatting is done in Python, so the only tokens spent are the single search +
JSON call. Expect a few cents per week.

## Setup
1. Put `main.py` and `.github/workflows/weekly.yml` in a GitHub repo
   (the workflow file must keep that exact path).
2. In the repo: Settings -> Secrets and variables -> Actions -> New repository secret.
   Add:
   - `ANTHROPIC_API_KEY` - from console.anthropic.com
   - `RECIPIENTS` - comma-separated list, e.g. `coach@usss.org,me@usss.org`
   - `SMTP_USER` - the sending email address
   - `SMTP_PASS` - a Gmail **App Password** (not your normal password), or an
     SMTP key from Resend/Postmark/etc.
3. Test it: Actions tab -> "Weekly Sport Reading" -> "Run workflow".

### Gmail app password
With 2-Step Verification on, go to Google Account -> Security -> App passwords,
generate one, and use it as `SMTP_PASS`. Keep `SMTP_HOST=smtp.gmail.com`,
`SMTP_PORT=587`.

### Using Resend/Postmark instead of Gmail
Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` to the provider's SMTP
credentials. No code change needed.

## Timing note
GitHub cron runs in UTC and does not adjust for daylight saving. `0 13 * * 1`
is 7:00am Mountain in summer and 6:00am in winter. Shift the hour if you care
about the exact minute year-round.

## Tuning
- Bump `MODEL` to a Sonnet model if you want stronger recency filtering.
- Raise/lower `max_uses` in `main.py` to trade thoroughness against cost.
- Some weeks may have thin pickings; the script fails loudly (no email) rather
  than sending a fabricated item, so check the Action log if you get no email.
