import os
import time
import requests
import xml.etree.ElementTree as ET
import json
from openai import OpenAI

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"

# =====================
# 🔐 ENV SECRETS
# =====================

NS_NATION = os.getenv("NS_NATION")
NS_PASSWORD = os.getenv("NS_PASSWORD")
NS_REGION = os.getenv("NS_REGION")
NS_CLIENT = os.getenv("NS_CLIENT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# =====================
# ⚙️ CONFIG
# =====================

POLL_INTERVAL = 120
REPLY_DELAY = 10
TRIGGER = "#chatgpt"

seen_ids = set()
xpin = None

MEMORY_FILE = "memory.json"


# =====================
# 🧠 MEMORY SYSTEM
# =====================

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f)


# =====================
# 🔐 LOGIN (GET X-PIN)
# =====================
def get_xpin():
    global xpin

    url = "https://www.nationstates.net/cgi-bin/api.cgi"

    headers = {
        "User-Agent": f"{NS_CLIENT} - Contact: your_email_or_discord",
    }

    data = {
        "a": "login",
        "nation": NS_NATION,
        "password": NS_PASSWORD
    }

    r = requests.post(url, data=data, headers=headers)

    print("Status:", r.status_code)
    print("Headers:", dict(r.headers))
    print("Body:", r.text)

    xpin = r.headers.get("X-Pin")

    if not xpin:
        raise Exception("Login failed: no X-Pin returned (check credentials or UA)")

# =====================
# 📥 FETCH RMB
# =====================

def fetch_rmb():
    params = {
        "a": "regiondata",
        "region": NS_REGION,
        "q": "messages"
    }

    headers = {
        "User-Agent": NS_CLIENT,
        "X-Pin": xpin
    }

    r = requests.get(API_URL, params=params, headers=headers)
    return r.text


# =====================
# 🔍 PARSE XML
# =====================

def parse_messages(xml_data):
    root = ET.fromstring(xml_data)
    messages = []

    for msg in root.findall(".//MESSAGE"):
        msg_id = msg.get("id")
        text = msg.text or ""
        messages.append((msg_id, text))

    return messages


# =====================
# 🧠 OPENAI RESPONSE (WITH MEMORY)
# =====================

def ask_openai(prompt, memory_context):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an RMB assistant inside a NationStates region. Use memory context naturally."
            },
            {
                "role": "user",
                "content": f"Memory: {memory_context}\n\nUser: {prompt}"
            }
        ]
    )
    return res.choices[0].message.content


# =====================
# 💬 POST RMB
# =====================

def post_rmb(message):
    data = {
        "a": "rmbpost",
        "region": NS_REGION,
        "nation": NS_NATION,
        "c": message
    }

    headers = {
        "User-Agent": NS_CLIENT,
        "X-Pin": xpin
    }

    requests.post(API_URL, data=data, headers=headers)


# =====================
# 🔁 MAIN LOOP
# =====================

def main():
    global xpin

    memory = load_memory()
    get_xpin()

    while True:
        try:
            xml = fetch_rmb()
            messages = parse_messages(xml)

            for msg_id, text in messages:

                if msg_id in seen_ids:
                    continue

                seen_ids.add(msg_id)

                if TRIGGER in text:
                    prompt = text.split(TRIGGER, 1)[-1].strip()

                    if prompt:

                        # ---- MEMORY ----
                        memory[msg_id] = {
                            "last_message": prompt
                        }
                        save_memory(memory)

                        memory_context = str(memory[msg_id])

                        # ---- AI ----
                        reply = ask_openai(prompt, memory_context)

                        time.sleep(REPLY_DELAY)
                        post_rmb(reply)

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print("Error:", e)
            time.sleep(15)


if __name__ == "__main__":
    main()
