import os
import time
import requests
import xml.etree.ElementTree as ET
import json
from openai import OpenAI

NS_NATION = os.getenv("NS_NATION")
NS_PASSWORD = os.getenv("NS_PASSWORD")
NS_REGION = os.getenv("NS_REGION")
NS_CLIENT = os.getenv("NS_CLIENT", "Chatbot (contact: dev)")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"

TRIGGER = "#chatgpt"

seen = set()

# ------------------------
# FETCH RMB (NO LOGIN NEEDED)
# ------------------------
def fetch_rmb():
    r = requests.get(
        API_URL,
        params={"a": "regiondata", "region": NS_REGION, "q": "messages"},
        headers={"User-Agent": NS_CLIENT}
    )
    return r.text


# ------------------------
# PARSE MESSAGES
# ------------------------
def parse(xml):
    root = ET.fromstring(xml)
    out = []

    for m in root.findall(".//MESSAGE"):
        mid = m.get("id")
        text = "".join(m.itertext()).strip()
        out.append((mid, text))

    return out


# ------------------------
# OPENAI
# ------------------------
def ask(prompt):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a short RMB assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return res.choices[0].message.content


# ------------------------
# POST RMB (THIS NEEDS LOGIN COOKIE STYLE)
# ------------------------
def post_rmb(msg):
    r = requests.post(
        API_URL,
        data={
            "a": "rmbpost",
            "region": NS_REGION,
            "nation": NS_NATION,
            "c": msg[:500]
        },
        headers={
            "User-Agent": NS_CLIENT
        }
    )
    print("POST:", r.status_code, r.text[:100])


# ------------------------
# MAIN LOOP
# ------------------------
while True:
    try:
        xml = fetch_rmb()
        messages = parse(xml)

        for mid, text in messages:
            if mid in seen:
                continue
            seen.add(mid)

            clean = " ".join(text.split()).lower()

            if TRIGGER in clean:
                prompt = text.split(TRIGGER, 1)[-1].strip()

                if prompt:
                    reply = ask(prompt)
                    time.sleep(5)
                    post_rmb(reply)

        time.sleep(60)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(10)
