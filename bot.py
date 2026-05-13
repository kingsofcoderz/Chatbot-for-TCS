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
NS_CLIENT = os.getenv("NS_CLIENT", "ChatBot (contact: discord)")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

BASE_URL = "https://www.nationstates.net/cgi-bin/api.cgi"

TRIGGER = "#chatgpt"
seen = set()

print("BOT STARTED")
print("Nation:", NS_NATION)
print("Region:", NS_REGION)

# =====================
# FETCH RMB (CORRECT NS DOCS METHOD)
# =====================

def fetch_rmb():
    try:
        params = {
            "region": NS_REGION,
            "q": "messages",
            "limit": 10
        }

        headers = {
            "User-Agent": NS_CLIENT,
            "Accept": "text/xml"
        }

        r = requests.get(BASE_URL, params=params, headers=headers, timeout=20)

        print("REQUEST:", r.url)
        print("STATUS:", r.status_code)
        print("BODY SAMPLE:", r.text[:200])

        return r.text

    except Exception as e:
        print("FETCH ERROR:", e)
        return ""


# =====================
# PARSE XML
# =====================

def parse_messages(xml_data):
    try:
        if not xml_data or "<MESSAGE" not in xml_data:
            return []

        start = xml_data.find("<")
        xml_data = xml_data[start:]
        xml_data = xml_data[:xml_data.rfind(">")+1]

        root = ET.fromstring(xml_data)

        messages = []

        for msg in root.findall(".//MESSAGE"):
            msg_id = msg.get("id")
            text = "".join(msg.itertext()).strip()
            messages.append((msg_id, text))

        return messages

    except Exception as e:
        print("XML ERROR:", e)
        return []


# =====================
# AI RESPONSE
# =====================

def ask_ai(prompt):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an RMB assistant inside a NationStates region. Keep replies short, natural, chat-style."
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
        return "AI error."


# =====================
# POST TO RMB
# =====================

def post_rmb(msg):
    try:
        data = {
            "a": "rmbpost",
            "region": NS_REGION,
            "nation": NS_NATION,
            "c": msg[:500]
        }

        r = requests.post(
            BASE_URL,
            data=data,
            headers={"User-Agent": NS_CLIENT},
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

        for msg_id, text in messages:
            if not msg_id or msg_id in seen:
                continue

            seen.add(msg_id)

            if TRIGGER in text.lower():
                prompt = text.split(TRIGGER, 1)[-1].strip()

                if prompt:
                    print("TRIGGER:", prompt)

                    reply = ask_ai(prompt)

                    time.sleep(3)
                    post_rmb(reply)

        time.sleep(60)


if __name__ == "__main__":
    main()
