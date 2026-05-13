import os
import time
import requests
import xml.etree.ElementTree as ET
import json
from openai import OpenAI

print("STARTING BOT...")

# =====================
# ENV
# =====================

NS_NATION = os.getenv("NS_NATION")
NS_PASSWORD = os.getenv("NS_PASSWORD")
NS_REGION = os.getenv("NS_REGION")
NS_CLIENT = os.getenv("NS_CLIENT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("ENV LOADED")

if not OPENAI_API_KEY:
    raise Exception("Missing OPENAI key")

client = OpenAI(api_key=OPENAI_API_KEY)

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"

POLL_INTERVAL = 120
REPLY_DELAY = 10
TRIGGER = "#chatgpt"

seen_ids = set()
xpin = None


# =====================
# LOGIN
# =====================
def get_xpin():
    global xpin

    url = "https://www.nationstates.net/cgi-bin/api.cgi"

    headers = {
        "User-Agent": f"{NS_CLIENT} (bot contact: example)"
    }

    data = {
        "a": "login",
        "nation": NS_NATION.lower().strip(),
        "password": NS_PASSWORD.strip()
    }

    r = requests.post(url, data=data, headers=headers)

    print("LOGIN STATUS:", r.status_code)
    print("LOGIN RESPONSE:", r.text[:200])  # IMPORTANT DEBUG

    xpin = r.headers.get("X-Pin")

    if not xpin:
        raise Exception("X-Pin failed - check nation/password format or UA")
# =====================
# RMB FETCH
# =====================

def fetch_rmb():
    r = requests.get(API_URL, params={
        "a": "regiondata",
        "region": NS_REGION,
        "q": "messages"
    }, headers={
        "User-Agent": NS_CLIENT,
        "X-Pin": xpin
    })

    return r.text


def parse(xml):
    root = ET.fromstring(xml)
    return [(m.get("id"), m.text or "") for m in root.findall(".//MESSAGE")]


def ask(prompt):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content


def post(msg):
    requests.post(API_URL, data={
        "a": "rmbpost",
        "region": NS_REGION,
        "nation": NS_NATION,
        "c": msg
    }, headers={
        "User-Agent": NS_CLIENT,
        "X-Pin": xpin
    })


# =====================
# MAIN LOOP
# =====================

def main():
    global xpin

    print("LOGIN START")
    get_xpin()

    while True:
        try:
            xml = fetch_rmb()
            msgs = parse(xml)

            for mid, text in msgs:
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)

                if TRIGGER in text:
                    prompt = text.split(TRIGGER, 1)[1].strip()
                    reply = ask(prompt)

                    time.sleep(REPLY_DELAY)
                    post(reply)

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(10)


if __name__ == "__main__":
    main()
