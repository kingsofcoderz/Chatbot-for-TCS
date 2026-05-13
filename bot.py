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
NS_CLIENT = os.getenv("NS_CLIENT", "ChatBot")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"

TRIGGER = "#chatgpt"
seen_ids = set()

print("BOT STARTED")
print("Nation:", NS_NATION)
print("Region:", NS_REGION)

# =====================
# FETCH RMB (DOC-CORRECT)
# =====================

def fetch_rmb():
    try:
        params = {
            "region": NS_REGION,
            "q": "messages",
            "limit": 20
        }

        headers = {
            "User-Agent": NS_CLIENT,
            "Accept": "text/xml"
        }

        r = requests.get(API_URL, params=params, headers=headers, timeout=20)

        print("\n--- FETCH ---")
        print("URL:", r.url)
        print("STATUS:", r.status_code)
        print("SAMPLE:", r.text[:200])

        return r.text

    except Exception as e:
        print("FETCH ERROR:", e)
        return ""


# =====================
# PARSE MESSAGES (SAFE XML)
# =====================

def parse_messages(xml_data):
    try:
        if not xml_data or "<MESSAGE" not in xml_data:
            return []

        root = ET.fromstring(xml_data)

        messages = []

        for msg in root.findall(".//MESSAGE"):
            msg_id = msg.get("id")
            text = "".join(msg.itertext()).strip()
            messages.append((msg_id, text))

        return messages

    except Exception as e:
        print("PARSE ERROR:", e)
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
                    "content": "You are an RMB chatbot inside a NationStates region. Keep replies short, natural, conversational."
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
# POST TO RMB (CORRECT: c=rmbpost)
# =====================

def post_rmb(message):
    try:
        data = {
            "c": "rmbpost",
            "nation": NS_NATION,
            "region": NS_REGION,
            "message": message[:500]
        }

        headers = {
            "User-Agent": NS_CLIENT,
            "Accept": "text/xml"
        }

        r = requests.post(API_URL, data=data, headers=headers, timeout=20)

        print("\n--- POST ---")
        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text[:200])

        return r.text

    except Exception as e:
        print("POST ERROR:", e)
        return ""


# =====================
# MAIN LOOP
# =====================

def main():
    while True:
        xml = fetch_rmb()
        messages = parse_messages(xml)

        print("MESSAGES FOUND:", len(messages))

        for msg_id, text in messages:
            if not msg_id or msg_id in seen_ids:
                continue

            seen_ids.add(msg_id)

            print("MSG:", text)

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
