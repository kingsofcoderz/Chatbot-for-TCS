import os
import time
import requests
import xml.etree.ElementTree as ET
import json
from openai import OpenAI

print("STARTING BOT...")
print("ENV LOADED")

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"

# =====================
# ENV
# =====================
NS_NATION = os.getenv("NS_NATION")
NS_PASSWORD = os.getenv("NS_PASSWORD")
NS_REGION = os.getenv("NS_REGION")
NS_CLIENT = os.getenv("NS_CLIENT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# =====================
# CONFIG
# =====================
POLL_INTERVAL = 120
REPLY_DELAY = 10
TRIGGER = "#chatgpt"

seen = set()

# =====================
# HEADERS BASE
# =====================
def base_headers():
    return {
        "User-Agent": NS_CLIENT,
        "X-Password": NS_PASSWORD
    }

# =====================
# FETCH RMB
# =====================
def fetch_rmb():
    params = {
        "a": "regiondata",
        "region": NS_REGION,
        "q": "messages"
    }

    r = requests.get(API_URL, params=params, headers=base_headers())

    print("RMB STATUS:", r.status_code)

    return r.text, r.headers.get("X-Pin")

# =====================
# PARSE
# =====================
def parse_messages(xml_data):
    root = ET.fromstring(xml_data)
    msgs = []

    for m in root.findall(".//MESSAGE"):
        msgs.append((m.get("id"), m.text or ""))

    return msgs

# =====================
# OPENAI
# =====================
def ask_ai(prompt):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an RMB assistant in a NationStates region."},
            {"role": "user", "content": prompt}
        ]
    )
    return res.choices[0].message.content

# =====================
# POST RMB
# =====================
def post_rmb(msg):
    data = {
        "a": "rmbpost",
        "region": NS_REGION,
        "nation": NS_NATION,
        "c": msg
    }

    r = requests.post(API_URL, data=data, headers=base_headers())

    print("POST STATUS:", r.status_code)

# =====================
# MAIN LOOP
# =====================
def main():
    while True:
        try:
            xml, xpin = fetch_rmb()

            msgs = parse_messages(xml)

            for msg_id, text in msgs:

                if msg_id in seen:
                    continue
                seen.add(msg_id)

                if TRIGGER in text:
                    prompt = text.split(TRIGGER, 1)[1].strip()

                    if not prompt:
                        continue

                    print("PROMPT:", prompt)

                    reply = ask_ai(prompt)

                    time.sleep(REPLY_DELAY)
                    post_rmb(reply)

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(15)

if __name__ == "__main__":
    main()
