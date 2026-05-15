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

HEADERS = {
    "User-Agent": "ChatBotTCS NationStates Bot by Shabarish"
}

NS_API = "https://www.nationstates.net/cgi-bin/api.cgi"

# =========================
# ERROR
# =========================

class AIModelError(Exception):
    pass

# =========================
# CLEANER
# =========================

def clean_bbcode(text):
    if not text:
        return "..."

    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("\n", " ")

    for tag in ["[img]", "[/img]", "[url]", "[/url]", "[quote]", "[/quote]"]:
        text = text.replace(tag, "")

    return text.strip()

# =========================
# GEMINI (SAFE SINGLE MODEL)
# =========================

def call_gemini(prompt):

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    r = requests.post(url, json=payload, timeout=20)
    data = r.json()

    try:
        if "candidates" not in data:
            raise AIModelError(str(data))

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        raise AIModelError(str(e))

# =========================
# WIKIPEDIA (FIXED PROPER SEARCH)
# =========================

def wiki_search(query):

    try:
        search_url = "https://en.wikipedia.org/w/api.php"

        params = {
            "action": "opensearch",
            "search": query,
            "limit": 1,
            "namespace": 0,
            "format": "json"
        }

        r = requests.get(search_url, params=params, timeout=10)
        data = r.json()

        if not data or len(data) < 2 or len(data[1]) == 0:
            return ""

        title = data[1][0]

        summary_url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + title.replace(" ", "_")
        )

        r2 = requests.get(summary_url, timeout=10)

        if r2.status_code != 200:
            return ""

        return r2.json().get("extract", "")

    except:
        return ""

# =========================
# MASTER SEARCH
# =========================

def web_search(query):

    wiki = wiki_search(query)

    return f"""
WIKIPEDIA:
{wiki}
""".strip()

# =========================
# CHAT MODES
# =========================

def ask_chatbot(prompt):

    system = (
        "You are ChatBotTCS for NationStates RMB. "
        "Be short, friendly, and use BBCode only."
    )

    return clean_bbcode(call_gemini(system + "\n\nUSER: " + prompt))


def ask_chatsearch(prompt):

    search_data = web_search(prompt)

    system = (
        "You are ChatBotTCS. Answer using the search data. "
        "If empty, say you don't know."
    )

    return clean_bbcode(
        call_gemini(system + "\n\nSEARCH DATA:\n" + search_data + "\n\nQUESTION:\n" + prompt)
    )

# =========================
# RMB POST
# =========================

def post_rmb(text):

    prepare = {
        "c": "rmbpost",
        "nation": NATION,
        "region": REGION,
        "text": text,
        "mode": "prepare"
    }

    headers = HEADERS.copy()
    headers["X-Password"] = PASSWORD

    r = requests.post(NS_API, data=prepare, headers=headers, timeout=20)

    if "<SUCCESS>" not in r.text:
        print("POST FAILED")
        return

    token = r.text.split("<SUCCESS>")[1].split("</SUCCESS>")[0]
    xpin = r.headers.get("X-Pin")

    if not xpin:
        print("NO XPIN")
        return

    execute = {
        "c": "rmbpost",
        "nation": NATION,
        "region": REGION,
        "text": text,
        "mode": "execute",
        "token": token
    }

    headers["X-Pin"] = xpin

    requests.post(NS_API, data=execute, headers=headers, timeout=20)

# =========================
# GET MESSAGES
# =========================

def get_messages():
    url = f"{NS_API}?region={REGION}&q=messages"
    r = requests.get(url, headers=HEADERS, timeout=20)
    return r.text

# =========================
# MAIN LOOP
# =========================

def main():

    print("Bot started...")

    seen = set()

    while True:

        try:
            xml = get_messages()
            root = ET.fromstring(xml)

            posts = root.findall(".//POST")

            for post in posts:

                post_id = post.attrib.get("id")
                nation = post.find("NATION").text
                message = post.find("MESSAGE").text

                if not message:
                    continue

                if nation.lower() == NATION.lower():
                    continue

                if post_id in seen:
                    continue

                msg = message.lower()

                try:

                    if "#chatbot" in msg:
                        q = message.replace("#chatbot", "").strip()
                        response = ask_chatbot(q or "Hello")

                    elif "#chatsearch" in msg:
                        q = message.replace("#chatsearch", "").strip()
                        response = ask_chatsearch(q or "Hello")

                    else:
                        continue

                    response = response[:500]

                    post_rmb(response)
                    seen.add(post_id)

                    time.sleep(15)

                except AIModelError as e:
                    print("AI ERROR:", e)

        except Exception as e:
            print("LOOP ERROR:", e)

        time.sleep(10)

# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()
