import os
import time
import requests
import xml.etree.ElementTree as ET
import json
from openai import OpenAI

# =====================
# ENV
# =====================

NS_NATION = os.getenv("NS_NATION")
NS_PASSWORD = os.getenv("NS_PASSWORD")
NS_REGION = os.getenv("NS_REGION")
NS_CLIENT = os.getenv("NS_CLIENT", "Chatbot-Bot (contact: dev)")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"

# =====================
# CONFIG
# =====================

POLL_INTERVAL = 120
REPLY_DELAY = 10
TRIGGER = "#chatgpt"

seen_ids = set()
xpin = None

MEMORY_FILE = "memory.json"


# =====================
# MEMORY
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
# LOGIN
# =====================
def get_xpin():
    global xpin

    url = "https://www.nationstates.net/cgi-bin/api.cgi"

    headers = {
        "User-Agent": NS_CLIENT
    }

    params = {
        "a": "login",
        "nation": NS_NATION,
        "password": NS_PASSWORD
    }

    r = requests.get(url, params=params, headers=headers)

    print("LOGIN STATUS:", r.status_code)
    print("LOGIN RESPONSE:", r.text[:200])

    if r.status_code != 200:
        raise Exception("Login failed HTTP")

    xpin = r.headers.get("X-Pin")

    if not xpin:
        raise Exception("No X-Pin returned")

    print("LOGIN OK")


# =====================
# FETCH RMB
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
# PARSE RMB (FIXED)
# =====================

def parse_messages(xml_data):
    root = ET.fromstring(xml_data)
    messages = []

    for msg in root.findall(".//MESSAGE"):
        msg_id = msg.get("id")

        # FIX: proper extraction
        text = "".join(msg.itertext()).strip()

        messages.append((msg_id, text))

    return messages


# =====================
# OPENAI
# =====================

def ask_openai(prompt, memory_context):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an RMB assistant inside NationStates. Keep replies short and natural."
            },
            {
                "role": "user",
                "content": f"Memory: {memory_context}\n\nUser: {prompt}"
            }
        ]
    )
    return res.choices[0].message.content


# =====================
# POST RMB
# =====================

def post_rmb(message):
    data = {
        "a": "rmbpost",
        "region": NS_REGION,
        "nation": NS_NATION,
        "c": message[:500]
    }

    headers = {
        "User-Agent": NS_CLIENT,
        "X-Pin": xpin
    }

    r = requests.post(API_URL, data=data, headers=headers)

    print("POST STATUS:", r.status_code)


# =====================
# MAIN LOOP
# =====================

def main():
    global xpin

    print("Bot starting...")

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

                # normalize text (IMPORTANT FIX)
                clean_text = " ".join(text.split()).lower()

                if TRIGGER in clean_text:

                    prompt = text.split(TRIGGER, 1)[-1].strip()

                    if prompt:

                        memory[msg_id] = {"last": prompt}
                        save_memory(memory)

                        reply = ask_openai(prompt, str(memory.get(msg_id)))

                        time.sleep(REPLY_DELAY)
                        post_rmb(reply)

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print("Error:", e)
            time.sleep(15)


if __name__ == "__main__":
    main()
