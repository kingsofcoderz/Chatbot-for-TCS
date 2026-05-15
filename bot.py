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
    "User-Agent": "ChatBotTCS NationStates Bot"
}

NS_API = "https://www.nationstates.net/cgi-bin/api.cgi"

# =========================
# ERROR
# =========================

class AIModelError(Exception):
    pass

# =========================
# CLEAN TEXT
# =========================

def clean_bbcode(text):
    if not text:
        return "..."

    for tag in ["**", "__", "[img]", "[/img]", "[url]", "[/url]", "[quote]", "[/quote]"]:
        text = text.replace(tag, "")

    return text.replace("\n", " ").strip()

# =========================
# GEMINI (SAFE)
# =========================

def call_gemini(prompt):

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    r = requests.post(url, json=payload, timeout=25)
    data = r.json()

    if "candidates" not in data:
        raise AIModelError(str(data))

    return data["candidates"][0]["content"]["parts"][0]["text"]

# =========================
# WIKIPEDIA SEARCH (FIXED + SAFE)
# =========================

def wiki_search(query):

    try:
        search_url = "https://en.wikipedia.org/w/api.php"

        r = requests.get(search_url, params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }, timeout=10)

        if r.status_code != 200:
            return ""

        try:
            data = r.json()
        except:
            return ""

        results = data.get("query", {}).get("search", [])

        if not results:
            # fallback: simpler query
            simple = query.split(" ")[0]

            r = requests.get(search_url, params={
                "action": "query",
                "list": "search",
                "srsearch": simple,
                "format": "json"
            }, timeout=10)

            try:
                data = r.json()
            except:
                return ""

            results = data.get("query", {}).get("search", [])

        if not results:
            return ""

        title = results[0]["title"]

        summary_url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + title.replace(" ", "_")
        )

        r2 = requests.get(summary_url, timeout=10)

        if r2.status_code != 200:
            return ""

        try:
            data2 = r2.json()
        except:
            return ""

        return data2.get("extract", "")

    except:
        return ""

# =========================
# SEARCH WRAPPER
# =========================

def web_search(query):

    wiki = wiki_search(query)

    if not wiki:
        return "No reliable information found."

    return wiki

# =========================
# CHATBOT MODE
# =========================

def ask_chatbot(prompt):

    system = (
        "You are ChatBotTCS for NationStates RMB. "
        "Be short and use BBCode only."
    )

    return clean_bbcode(call_gemini(system + "\n\nUSER: " + prompt))

# =========================
# CHATSEARCH MODE
# =========================

def ask_chatsearch(prompt):

    data = web_search(prompt)

    system = (
        "Use the provided search data to answer accurately. "
        "If empty, say you don't know."
    )

    return clean_bbcode(
        call_gemini(system + "\n\nSEARCH DATA:\n" + data + "\n\nQUESTION:\n" + prompt)
    )

# =========================
# POST RMB
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
                    print("AI FAILED:", e)

        except Exception as e:
            print("LOOP ERROR:", e)

        time.sleep(10)

# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()
