import requests
import xml.etree.ElementTree as ET
import time
import os
import sqlite3

# =========================
# CONFIG
# =========================

NATION = "chatbottcs"
REGION = "chatbot_of_the_citrus_sea"

PASSWORD = os.getenv("PASSWORD", "").strip()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

TRIGGER = "#chatbot"

HEADERS = {
    "User-Agent": "ChatBotTCS NationStates Bot by Shabarish"
}

NS_API = "https://www.nationstates.net/cgi-bin/api.cgi"

# =========================
# DATABASE
# =========================

conn = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS seen_posts (
    post_id TEXT PRIMARY KEY
)
""")

conn.commit()

def has_seen_post(post_id):

    cursor.execute(
        "SELECT post_id FROM seen_posts WHERE post_id=?",
        (post_id,)
    )

    return cursor.fetchone() is not None

def save_seen_post(post_id):

    try:

        cursor.execute(
            "INSERT INTO seen_posts (post_id) VALUES (?)",
            (post_id,)
        )

        conn.commit()

    except:
        pass

# =========================
# BBCODE CLEANER
# =========================

def clean_bbcode(text):

    text = text.replace("**", "")
    text = text.replace("__", "")

    text = text.replace("\n", " ")

    blocked_tags = [
        "[img]",
        "[/img]",
        "[url]",
        "[/url]",
        "[quote]",
        "[/quote]"
    ]

    for tag in blocked_tags:
        text = text.replace(tag, "")

    return text

# =========================
# GEMINI AI
# =========================

def ask_gemini(prompt):

    if not GEMINI_API_KEY:
        return "Gemini API key missing."

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "You are a helpful AI bot on the "
                            "NationStates regional message board. "
                            "Use NationStates BBCode when useful. "
                            "Allowed tags are: "
                            "[b], [i], [u], [nation], [region]. "
                            "Do NOT use markdown. "
                            "Keep replies brief and natural.\n\n"
                            f"User message: {prompt}"
                        )
                    }
                ]
            }
        ]
    }

    try:

        r = requests.post(
            url,
            json=payload,
            timeout=30
        )

        print("GEMINI STATUS:", r.status_code)

        data = r.json()

        reply = (
            data["candidates"][0]
            ["content"]["parts"][0]["text"]
        )

        reply = clean_bbcode(reply)

        return reply

    except Exception as e:

        print("GEMINI ERROR:", e)

        return "AI failed to respond."

# =========================
# RMB POSTING
# =========================

def post_rmb(text):

    prepare_data = {
        "c": "rmbpost",
        "nation": NATION,
        "region": REGION,
        "text": text,
        "mode": "prepare"
    }

    prepare_headers = HEADERS.copy()
    prepare_headers["X-Password"] = PASSWORD

    r = requests.post(
        NS_API,
        data=prepare_data,
        headers=prepare_headers
    )

    print("PREPARE STATUS:", r.status_code)

    if "<SUCCESS>" not in r.text:
        print("PREPARE FAILED")
        print(r.text)
        return

    token = r.text.split("<SUCCESS>")[1].split("</SUCCESS>")[0]

    xpin = r.headers.get("X-Pin")

    if not xpin:
        print("NO XPIN")
        return

    execute_data = {
        "c": "rmbpost",
        "nation": NATION,
        "region": REGION,
        "text": text,
        "mode": "execute",
        "token": token
    }

    execute_headers = HEADERS.copy()
    execute_headers["X-Pin"] = xpin

    r2 = requests.post(
        NS_API,
        data=execute_data,
        headers=execute_headers
    )

    print("EXECUTE STATUS:", r2.status_code)
    print(r2.text)

# =========================
# RMB READER
# =========================

def get_messages():

    url = f"{NS_API}?region={REGION}&q=messages"

    r = requests.get(
        url,
        headers=HEADERS
    )

    print("READ STATUS:", r.status_code)

    return r.text

# =========================
# MAIN LOOP
# =========================

def main():

    print("Bot started...")

    while True:

        try:

            xml_data = get_messages()

            root = ET.fromstring(xml_data)

            posts = root.findall(".//POST")

            for post in posts:

                post_id = post.attrib.get("id")

                nation = post.find("NATION").text
                message = post.find("MESSAGE").text

                if not message:
                    continue

                print(nation, ":", message)

                # Ignore own bot
                if nation.lower() == NATION.lower():
                    continue

                # Prevent duplicates
                if has_seen_post(post_id):
                    continue

                # Trigger detection
                if TRIGGER in message.lower():

                    print("TRIGGER FOUND")

                    cleaned = (
                        message
                        .replace(TRIGGER, "")
                        .strip()
                    )

                    if not cleaned:
                        cleaned = "Hello"

                    response = ask_gemini(cleaned)

                    response = response[:500]

                    print("AI RESPONSE:", response)

                    post_rmb(response)

                    save_seen_post(post_id)

                    # Flood control
                    time.sleep(15)

        except Exception as e:

            print("ERROR:", e)

        time.sleep(10)

# =========================
# START
# =========================

if __name__ == "__main__":
    main()
