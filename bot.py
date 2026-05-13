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

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"

TRIGGER = "#chatgpt"
seen = set()

print("BOT STARTED")
print("Nation:", NS_NATION)
print("Region:", NS_REGION)

# =====================
# RAW FETCH (NO AUTO ENCODING)
# =====================

def fetch_rmb():
    try:
        region = NS_REGION.replace(" ", "%20")

        url = (
            f"{API_URL}"
            f"?a=messages"
            f"&region={region}"
        )

        headers = {
            "User-Agent": NS_CLIENT,
            "Accept": "text/xml"
        }

        r = requests.get(url, headers=headers, timeout=20)

        print("REQUEST:", url)
        print("STATUS:", r.status_code)
        print("RESPONSE SAMPLE:", r.text[:200])

        return r.text

    except Exception as e:
        print("FETCH ERROR:", e)
        return ""


# =====================
# XML PARSER SAFE
# =====================

def parse_messages(xml_data):
    try:
        if "<MESSAGE" not in xml_data:
            return []

        start = xml_data.find("<")
        xml_data = xml_data[start:]
        xml_data = xml_data[:xml_data.rfind(">")+1]

        root = ET.fromstring(xml_data)

        msgs = []

        for msg in root.findall(".//MESSAGE"):
            mid = msg.get("id")
            text = "".join(msg.itertext()).strip()
            msgs.append((mid, text))

        return msgs

    except Exception as e:
        print("XML ERROR:", e)
        return []


# =====================
# AI
# =====================

def ask_ai(prompt):
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Reply short like a chat bot."},
                {"role": "user", "content": prompt}
            ]
        )
        return res.choices[0].message.content

    except Exception as e:
        print("AI ERROR:", e)
        return "error"


# =====================
# POST
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
            headers={"User-Agent": NS_CLIENT},
            timeout=20
        )

        print("POST STATUS:", r.status_code)

    except Exception as e:
        print("POST ERROR:", e)


# =====================
# LOOP
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
                    time.sleep(3)
                    post_rmb(reply)

        time.sleep(60)


if __name__ == "__main__":
    main()

    
