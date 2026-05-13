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
# FETCH RMB
# =====================

def fetch_rmb():
    r = requests.get(
        API_URL,
        params={
            "region": NS_REGION,
            "q": "messages",
            "limit": 20
        },
        headers={
            "User-Agent": NS_CLIENT
        },
        timeout=20
    )

    print("\nFETCH STATUS:", r.status_code)
    return r.text


# =====================
# PARSE (FIXED BASED ON YOUR XML)
# =====================

def parse_messages(xml_data):
    try:
        root = ET.fromstring(xml_data)

        messages = []

        for post in root.findall(".//POST"):
            msg_id = post.get("id")
            nation = post.findtext("NATION") or ""
            text = post.findtext("MESSAGE") or ""

            messages.append((msg_id, nation, text.strip()))

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
                    "content": "You are an RMB chatbot. Keep replies short and natural."
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
# POST TO RMB (CORRECT NS METHOD)
# =====================

def post_rmb(message):
    r = requests.post(
        API_URL,
        data={
            "c": "rmbpost",
            "nation": NS_NATION,
            "region": NS_REGION,
            "message": message[:500]
        },
        headers={
            "User-Agent": NS_CLIENT
        },
        timeout=20
    )

    print("\nPOST STATUS:", r.status_code)
    print("POST RESPONSE:", r.text[:200])


# =====================
# MAIN LOOP (FIXED LOGIC)
# =====================

def main():
    while True:
        xml = fetch_rmb()
        messages = parse_messages(xml)

        print("MESSAGES FOUND:", len(messages))

        for msg_id, nation, text in messages:

            if not msg_id or msg_id in seen_ids:
                continue

            seen_ids.add(msg_id)

            print(f"\n[{nation}] {text}")

            # ❌ IGNORE BOT OWN POSTS (CRITICAL FIX)
            if nation == NS_NATION:
                continue

            if TRIGGER in text.lower():
                prompt = text.split(TRIGGER, 1)[-1].strip()

                if prompt:
                    print("TRIGGER FOUND:", prompt)

                    reply = ask_ai(prompt)

                    time.sleep(3)
                    post_rmb(reply)

        time.sleep(60)


if __name__ == "__main__":
    main()
