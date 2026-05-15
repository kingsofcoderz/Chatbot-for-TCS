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
# CLEANER
# =========================

def clean_bbcode(text):
    if not text:
        return "..."

    for tag in ["**", "__", "[img]", "[/img]", "[url]", "[/url]", "[quote]", "[/quote]"]:
        text = text.replace(tag, "")

    return text.replace("\n", " ").strip()

# =========================
# GEMINI (SINGLE STABLE MODEL)
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
# MULTI-RESEARCH ENGINE
# =========================

def wiki_search(query):
    try:
        url = "https://en.wikipedia.org/w/api.php"

        r = requests.get(url, params={
            "action": "opensearch",
            "search": query,
            "limit": 3,
            "namespace": 0,
            "format": "json"
        }, timeout=10)

        data = r.json()
        titles = data[1] if len(data) > 1 else []

        results = []

        for title in titles:
            try:
                summary_url = (
                    "https://en.wikipedia.org/api/rest_v1/page/summary/"
                    + title.replace(" ", "_")
                )

                r2 = requests.get(summary_url, timeout=10)

                if r2.status_code == 200:
                    text = r2.json().get("extract", "")
                    if text:
                        results.append(f"{title}: {text}")

            except:
                continue

        return "\n".join(results)

    except:
        return ""

# =========================
# SIMPLE EXTRA SOURCE (SAFE FALLBACK FACT BUILDER)
# =========================

def simple_fallback(query):
    try:
        # lightweight “knowledge guess” via Wikipedia direct summary attempt
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_")
        r = requests.get(url, timeout=10)

        if r.status_code == 200:
            return r.json().get("extract", "")

    except:
        pass

    return ""

# =========================
# MASTER RESEARCH SYSTEM
# =========================

def web_search(query):

    wiki_multi = wiki_search(query)
    wiki_single = simple_fallback(query)

    combined = f"""
MULTI-WIKIPEDIA RESULTS:
{wiki_multi}

SINGLE-FALLBACK:
{wiki_single}
""".strip()

    return combined

# =========================
# CHAT MODES
# =========================

def ask_chatbot(prompt):

    system = (
        "You are ChatBotTCS for NationStates RMB. "
        "Be short, friendly, use BBCode only."
    )

    return clean_bbcode(call_gemini(system + "\n\nUSER: " + prompt))


def ask_chatsearch(prompt):

    data = web_search(prompt)

    system = (
        "You are ChatBotTCS. Use the research data below to answer. "
        "Combine all sources into one accurate response. "
        "If empty, say you don't know."
    )

    return clean_bbcode(call_gemini(
        system + "\n\nRESEARCH DATA:\n" + data + "\n\nQUESTION:\n" + prompt
    ))

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
                    print("AI FAILED:", e)

        except Exception as e:
            print("LOOP ERROR:", e)

        time.sleep(10)

# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()
