import os
import time
import requests
import xml.etree.ElementTree as ET
from openai import OpenAI

# =====================
# ENV
# =====================

NS_NATION = os.getenv("NS_NATION")
NS_REGION = os.getenv("NS_REGION")
NS_CLIENT = os.getenv("NS_CLIENT", "RMB Bot")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"

TRIGGER = "#chatgpt"
seen = set()

# =====================
# DEBUG START
# =====================

print("BOT STARTED")
print("Nation:", NS_NATION)
print("Region:", NS_REGION)

# =====================
# FETCH RMB (FIXED)
# =====================
def fetch_rmb():
    try:
        url = "https://www.nationstates.net/cgi-bin/api.cgi"

        r = requests.get(
            url,
            params=[
                ("a", "regiondata"),
                ("region", NS_REGION),
                ("q", "messages")
            ],
            headers={
                "User-Agent": NS_CLIENT
            },
            timeout=20
        )

        print("REQUEST:", r.url)
        print("STATUS:", r.status_code)

        return r.text

    except Exception as e:
        print("FETCH ERROR:", e)
        return ""


# =====================
# PARSE XML SAFE
# =====================

def parse_messages(xml_data):
    try:
        if not xml_data or "<MESSAGE" not in xml_data:
            return []

        start = xml_data.find("<")
        xml_data = xml_data[start:]
        end = xml_data.rfind(">") + 1
        xml_data = xml_data[:end]

        root = ET.fromstring(xml_data)

        msgs = []

        for m in root.findall(".//MESSAGE"):
            mid = m.get("id")
            text = "".join(m.itertext()).strip()
            msgs.append((mid, text))

        return msgs

    except Exception as e:
        print("XML ERROR:", e)
        return []


# =====================
# OPENAI
# =====================

def ask_ai(prompt):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an RMB assistant. Reply short and natural."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return res.choices[0].message.content

    except Exception as e:
        print("OPENAI ERROR:", e)
        return "Error generating reply."


# =====================
# POST RMB
# =====================

def post_rmb(msg):
    try:
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
            },
            timeout=20
        )

        print("POST STATUS:", r.status_code)

    except Exception as e:
        print("POST ERROR:", e)


# =====================
# MAIN LOOP
# =====================

def main():
    while True:
        xml = fetch_rmb()
        messages = parse_messages(xml)

        for mid, text in messages:
            if not mid or mid in seen:
                continue

            seen.add(mid)

            if TRIGGER in text.lower():
                prompt = text.split(TRIGGER, 1)[-1].strip()

                if prompt:
                    print("TRIGGER:", prompt)

                    reply = ask_ai(prompt)

                    time.sleep(5)
                    post_rmb(reply)

        time.sleep(60)


if __name__ == "__main__":
    main()
