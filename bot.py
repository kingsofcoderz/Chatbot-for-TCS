import os
import time
import requests
import xml.etree.ElementTree as ET
import json
from openai import OpenAI

# =====================
# 🔐 ENV SECRETS (MUST BE FIRST)
# =====================

NS_NATION = os.getenv("NS_NATION")
NS_PASSWORD = os.getenv("NS_PASSWORD")
NS_REGION = os.getenv("NS_REGION")
NS_CLIENT = os.getenv("NS_CLIENT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("Bot starting...")
print("NS_NATION:", NS_NATION)
print("NS_REGION:", NS_REGION)
print("OPENAI KEY EXISTS:", bool(OPENAI_API_KEY))

# =====================
# ❗ SAFETY CHECKS
# =====================

if not NS_NATION:
    raise Exception("Missing NS_NATION")
if not NS_PASSWORD:
    raise Exception("Missing NS_PASSWORD")
if not NS_REGION:
    raise Exception("Missing NS_REGION")
if not OPENAI_API_KEY:
    raise Exception("Missing OPENAI_API_KEY")

if not OPENAI_API_KEY or not OPENAI_API_KEY.startswith("sk-"):
    raise Exception("Invalid OpenAI API Key")

client = OpenAI(api_key=OPENAI_API_KEY)

# =====================
# ⚙️ CONFIG
# =====================

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"
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
# 🔐 LOGIN → GET X-PIN
# =====================

def get_xpin():
    global xpin

    headers = {
        "User-Agent": NS_CLIENT
    }

    data = {
        "a": "login",
        "nation": NS_NATION,
        "password": NS_PASSWORD
    }

    r = requests.post(API_URL, data=data, headers=headers)

    print("Login status:", r.status_code)
    print("Login headers:", dict(r.headers))

    xpin = r.headers.get("X-Pin")

    if not xpin:
        raise Exception("Failed to get X-Pin")


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
# 🧠 OPENAI RESPONSE
# =====================

def ask_openai(prompt, memory_context):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an RMB assistant inside a NationStates region. Keep replies short and useful."
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

                        memory[msg_id] = {"last_message": prompt}
                        save_memory(memory)

                        reply = ask_openai(prompt, str(memory[msg_id]))

                        time.sleep(REPLY_DELAY)
                        post_rmb(reply)

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print("Error:", e)
            time.sleep(15)


if __name__ == "__main__":
    main()
