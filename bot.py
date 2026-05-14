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
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "").strip()

HEADERS = {
    "User-Agent": "ChatBotTCS NationStates Bot by Shabarish"
}

NS_API = "https://www.nationstates.net/cgi-bin/api.cgi"

# =========================
# CLEANER
# =========================

def clean_bbcode(text):
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("\n", " ")

    blocked_tags = ["[img]", "[/img]", "[url]", "[/url]", "[quote]", "[/quote]"]

    for tag in blocked_tags:
        text = text.replace(tag, "")

    return text.strip()

# =========================
# WEB SEARCH
# =========================

def web_search(query):
    if not SERPAPI_KEY:
        return "Search unavailable (missing API key)."

    url = "https://serpapi.com/search.json"

    params = {
        "q": query,
        "api_key": SERPAPI_KEY
    }

    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()

        results = []

        for item in data.get("organic_results", [])[:5]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            results.append(f"{title} - {snippet}")

        return "\n".join(results)

    except Exception as e:
        return f"Search failed: {e}"

# =========================
# GEMINI (CHATBOT)
# =========================

def ask_gemini(prompt):

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
                            "You are ChatBotTCS for NationStates RMB. "
                            "Be short, friendly, use BBCode only [b][i][u][nation][region]. "
                            "No markdown.\n\n"
                            f"User: {prompt}"
                        )
                    }
                ]
            }
        ]
    }

    r = requests.post(url, json=payload, timeout=30)

    data = r.json()

    reply = data["candidates"][0]["content"]["parts"][0]["text"]

    return clean_bbcode(reply)

# =========================
# GEMINI + SEARCH
# =========================

def ask_gemini_search(prompt):

    search_results = web_search(prompt)

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
                            "You are ChatBotTCS. Use web results to answer accurately.\n\n"
                            f"WEB RESULTS:\n{search_results}\n\n"
                            f"QUESTION: {prompt}\n"
                        )
                    }
                ]
            }
        ]
    }

    r = requests.post(url, json=payload, timeout=30)

    data = r.json()

    reply = data["candidates"][0]["content"]["parts"][0]["text"]

    return clean_bbcode(reply)

# =========================
# RMB POST
# =========================

def post_rmb(text):

    prepare_data = {
        "c": "rmbpost",
        "nation": NATION,
        "region": REGION,
        "text": text,
        "mode": "prepare"
    }

    headers = HEADERS.copy()
    headers["X-Password"] = PASSWORD

    r = requests.post(NS_API, data=prepare_data, headers=headers)

    if "<SUCCESS>" not in r.text:
        print("Prepare failed")
        return

    token = r.text.split("<SUCCESS>")[1].split("</SUCCESS>")[0]
    xpin = r.headers.get("X-Pin")

    if not xpin:
        print("No X-Pin")
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

    r2 = requests.post(NS_API, data=execute_data, headers=execute_headers)

    print("POST:", r2.status_code)

# =========================
# GET MESSAGES
# =========================

def get_messages():

    url = f"{NS_API}?region={REGION}&q=messages"

    r = requests.get(url, headers=HEADERS)

    return r.text

# =========================
# MAIN LOOP
# =========================

def main():

    print("Bot started...")

    seen = set()

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

                if nation.lower() == NATION.lower():
                    continue

                if post_id in seen:
                    continue

                msg_lower = message.lower()

                response = None

                # =========================
                # CHATSEARCH MODE
                # =========================
                if "#chatsearch" in msg_lower:

                    cleaned = message.replace("#chatsearch", "").strip()

                    if not cleaned:
                        cleaned = "Hello"

                    response = ask_gemini_search(cleaned)

                # =========================
                # CHATBOT MODE
                # =========================
                elif "#chatbot" in msg_lower:

                    cleaned = message.replace("#chatbot", "").strip()

                    if not cleaned:
                        cleaned = "Hello"

                    response = ask_gemini(cleaned)

                # =========================
                # POST RESPONSE
                # =========================
                if response:

                    response = response[:500]

                    print("AI:", response)

                    post_rmb(response)

                    seen.add(post_id)

                    time.sleep(15)

        except Exception as e:
            print("ERROR:", e)

        time.sleep(10)

# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()
