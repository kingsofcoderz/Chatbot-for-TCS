import os
import time
import requests
import xml.etree.ElementTree as ET
from openai import OpenAI

# =====================
# CONFIG
# =====================

NS_NATION = os.getenv("NS_NATION")
NS_REGION = os.getenv("NS_REGION")
NS_CLIENT = os.getenv("NS_CLIENT", "Chatbot (contact: dev)")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"

TRIGGER = "#chatgpt"

seen_messages = set()

# =====================
# FETCH RMB
# =====================
def fetch_rmb():
    r = requests.get(
        API_URL,
        params={
            "a": "messages",
            "region": NS_REGION
        },
        headers={"User-Agent": NS_CLIENT},
        timeout=20
    )

    print("STATUS:", r.status_code)
    print("RAW:", r.text[:300])

    return r.text


# =====================
# SAFE XML PARSER (FIXED)
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

        messages = []

        for msg in root.findall(".//MESSAGE"):
            msg_id = msg.get("id")
            text = "".join(msg.itertext()).strip()
            messages.append((msg_id, text))

        return messages

    except Exception as e:
        print("XML PARSE ERROR:", e)
        return []


# =====================
# OPENAI RESPONSE
# =====================

def ask_openai(prompt):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful RMB assistant in a NationStates region. Keep replies short."
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
        return "Sorry, I failed to respond."


# =====================
# POST RMB
# =====================

def post_rmb(message):
    try:
        r = requests.post(
            API_URL,
            data={
                "a": "rmbpost",
                "region": NS_REGION,
                "nation": NS_NATION,
                "c": message[:500]
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
    print("Bot started...")
    print("Nation:", NS_NATION)
    print("Region:", NS_REGION)

    while True:
        try:
            xml = fetch_rmb()
            messages = parse_messages(xml)

            for msg_id, text in messages:

                if not msg_id or msg_id in seen_messages:
                    continue

                seen_messages.add(msg_id)

                clean = " ".join(text.split()).lower()

                if TRIGGER in clean:
                    prompt = text.split(TRIGGER, 1)[-1].strip()

                    if prompt:
                        print("TRIGGER FOUND:", prompt)

                        reply = ask_openai(prompt)

                        time.sleep(5)
                        post_rmb(reply)

            time.sleep(60)

        except Exception as e:
            print("LOOP ERROR:", e)
            time.sleep(10)


if __name__ == "__main__":
    main()
