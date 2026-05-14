import requests
import xml.etree.ElementTree as ET
import time
import os

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
                            "Reply briefly, naturally, and clearly. "
                            "Avoid markdown.\n\n"
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

        # Clean RMB formatting
        reply = reply.replace("\n", " ")

        return reply

    except Exception as e:

        print("GEMINI ERROR:", e)

        return "AI failed to respond."

# =========================
# RMB POSTING
# =========================

def post_rmb(text):

    # ---------- PREPARE ----------

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

    # ---------- EXECUTE ----------

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

    seen_posts = set()

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

                # Ignore bot's own posts
                if nation.lower() == NATION.lower():
                    continue

                # Prevent duplicate replies
                if post_id in seen_posts:
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

                    # RMB safety limit
                    response = response[:500]

                    print("AI RESPONSE:", response)

                    post_rmb(response)

                    seen_posts.add(post_id)

                    # Avoid RMB flood control
                    time.sleep(15)

        except Exception as e:

            print("ERROR:", e)

        # Poll every 10 seconds
        time.sleep(10)

# =========================
# START
# =========================

if __name__ == "__main__":
    main()
