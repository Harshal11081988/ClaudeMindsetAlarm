# Mindset Alarm

Personal recommendation engine: 5 fixed daily slots generate a short,
sigma/alpha-framed mindset message (via Claude API) and deliver it over
Email and WhatsApp. GitHub Actions is the scheduler; Streamlit is the
dashboard.

## How it fires

`.github/workflows/send_alarm.yml` runs on 5 cron triggers (06:00, 10:00,
13:00, 17:00, 21:00 IST). Each run calls `scripts/send_recommendation.py`,
which generates one message, sends it via email + WhatsApp, and appends
the result to `log.json`, which the workflow commits back to the repo.

GitHub's scheduled workflows are best-effort and can lag by several
minutes during high load, and get **auto-disabled after 60 days of repo
inactivity** — push something occasionally, or star your own commit habit
into it via the build-in-public routine.

## Setup

### 1. Secrets (GitHub repo -> Settings -> Secrets and variables -> Actions)
| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic API key |
| `EMAIL_HOST` | e.g. `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USER` | sender address |
| `EMAIL_PASS` | Gmail **app password**, not your login password |
| `EMAIL_TO` | where you want it delivered |
| `TWILIO_ACCOUNT_SID` | from Twilio console |
| `TWILIO_AUTH_TOKEN` | from Twilio console |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` (Twilio sandbox) |
| `WHATSAPP_TO` | `whatsapp:+91XXXXXXXXXX` |

### 2. WhatsApp sandbox (fastest path, no Meta approval)
1. Twilio console -> Messaging -> Try it out -> Send a WhatsApp message
2. Send the given `join <code>` phrase from your WhatsApp to the sandbox number
3. Sandbox sessions expire after 72 hrs of inactivity — resend `join <code>`
   if messages stop arriving. Move to a paid Twilio WhatsApp sender to
   remove this limitation later.

### 3. Test manually before trusting the cron
Actions tab -> Mindset Alarm -> Run workflow -> pick a `slot_id` -> Run.
Check `log.json` and your inbox/WhatsApp.

### 4. Deploy the dashboard
Streamlit Community Cloud -> New app -> point at this repo,
main file path: `streamlit_app/app.py`. Add to its secrets:
```
GITHUB_TOKEN = "ghp_..."   # fine-grained PAT, contents:write on this repo
GITHUB_REPO = "Harshal11081988/mindset-alarm"
```

## Repo structure
```
.github/workflows/send_alarm.yml   the scheduler
scripts/send_recommendation.py     generate + send + log
streamlit_app/app.py               dashboard (history + config editor)
config.json                        slot times, mindset prompt, context
log.json                           append-only send history
```
