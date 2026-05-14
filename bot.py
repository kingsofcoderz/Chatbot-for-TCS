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

TRIGGER = "#chatbot"

HEADERS = {
    "User-Agent": "ChatBotTCS NationStates Bot by Shabarish"
}

NS_API = "https://www.nationstates.net/cgi-bin/api.cgi"

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

                # Ignore own bot
                if nation.lower() == NATION.lower():
                    continue

                # Prevent duplicate replies
                if post_id in seen_posts:
                    continue

                # Trigger detection
                if TRIGGER in message.lower():

                    print("TRIGGER FOUND")

                    response = (
                        f"Hello @{nation}, "
                        f"I detected your trigger."
                    )

                    post_rmb(response)

                    seen_posts.add(post_id)

                    # Avoid flood control
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
