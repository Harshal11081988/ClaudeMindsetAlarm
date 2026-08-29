"""
Dashboard for the Mindset Alarm system.
Deploy on Streamlit Community Cloud pointing at this repo, main file:
streamlit_app/app.py

Required Streamlit secrets (Settings -> Secrets on Streamlit Cloud):
  GITHUB_TOKEN   a fine-grained PAT with contents:write on this repo
  GITHUB_REPO    e.g. "Harshal11081988/mindset-alarm"

Note: Streamlit Cloud's filesystem is ephemeral, so config edits are
written back to GitHub directly (not to local disk) via the GitHub API.
"""

import json
from datetime import datetime, timezone

import requests
import streamlit as st

st.set_page_config(page_title="Mindset Alarm", layout="centered")

GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"


def fetch_raw(path, default):
    try:
        resp = requests.get(f"{RAW_BASE}/{path}", timeout=10)
        if resp.status_code == 200:
            return json.loads(resp.text)
    except Exception:
        pass
    return default


def push_file(path, content_dict, message):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    get_resp = requests.get(f"{API_BASE}/{path}", headers=headers, timeout=10)
    sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None

    import base64

    body = {
        "message": message,
        "content": base64.b64encode(json.dumps(content_dict, indent=2).encode()).decode(),
        "branch": "main",
    }
    if sha:
        body["sha"] = sha

    put_resp = requests.put(f"{API_BASE}/{path}", headers=headers, json=body, timeout=10)
    return put_resp.status_code in (200, 201), put_resp.text


st.title("Mindset Alarm")
st.caption("Recommendation engine — 5 daily slots, delivered via Email + WhatsApp")

config = fetch_raw("config.json", {})
log = fetch_raw("log.json", [])

tab_history, tab_config = st.tabs(["History", "Configure"])

with tab_history:
    if not log:
        st.info("No sends logged yet. The GitHub Actions workflow writes here after each run.")
    else:
        for entry in reversed(log[-30:]):
            ts = entry.get("timestamp", "")
            try:
                ts_display = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M UTC")
            except ValueError:
                ts_display = ts
            status = "⚠️ errors" if entry.get("errors") else "✅ sent"
            st.markdown(f"**{entry.get('slot_label', '')}** — {ts_display} — {status}")
            st.write(entry.get("content", ""))
            if entry.get("errors"):
                st.error("; ".join(entry["errors"]))
            st.divider()

with tab_config:
    st.subheader("Slot times (IST)")
    if config.get("slots"):
        updated_slots = []
        for slot in config["slots"]:
            col1, col2 = st.columns([1, 2])
            with col1:
                new_time = st.text_input(
                    f"Slot {slot['id']} time",
                    value=slot["time_ist"],
                    key=f"time_{slot['id']}",
                )
            with col2:
                new_label = st.text_input(
                    f"Slot {slot['id']} label",
                    value=slot["label"],
                    key=f"label_{slot['id']}",
                )
            updated_slots.append({"id": slot["id"], "time_ist": new_time, "label": new_label})

        st.caption(
            "Note: editing times here updates config.json, but the actual cron "
            "schedule lives in .github/workflows/send_alarm.yml and must be "
            "updated to match — Streamlit config alone won't reschedule GitHub Actions."
        )

    st.subheader("Mindset framework")
    new_context = st.text_area("Context", value=config.get("context", ""), height=100)
    new_system_prompt = st.text_area(
        "System prompt", value=config.get("system_prompt", ""), height=150
    )

    if st.button("Save changes to GitHub"):
        if not GITHUB_TOKEN or not GITHUB_REPO:
            st.error("Missing GITHUB_TOKEN / GITHUB_REPO in Streamlit secrets.")
        else:
            new_config = dict(config)
            new_config["slots"] = updated_slots
            new_config["context"] = new_context
            new_config["system_prompt"] = new_system_prompt
            ok, msg = push_file("config.json", new_config, "config: update via dashboard")
            if ok:
                st.success("Saved. Refresh to see updated values.")
            else:
                st.error(f"Failed to save: {msg}")
