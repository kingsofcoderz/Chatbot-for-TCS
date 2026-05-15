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
# ERROR CLASS
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
# GET AVAILABLE MODELS (FIXES YOUR ERROR)
# =========================

def get_available_models():
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        r = requests.get(url, timeout=20)
        data = r.json()

        models = []

        for m in data.get("models", []):
            name = m.get("name", "")
            methods = m.get("supportedGenerationMethods", [])

            if "generateContent" in methods:
                models.append(name.replace("models/", ""))

        print("AVAILABLE MODELS:", models)

        return models

    except Exception as e:
        print("MODEL FETCH ERROR:", e)
        return []

# =========================
# GEMINI CALL (STRICT)
# =========================

def call_gemini_strict(prompt):

    models = get_available_models()

    if not models:
        raise AIModelError("No Gemini models available")

    last_error = None

    for model in models:

        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={GEMINI_API_KEY}"
            )

            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ]
            }

            r = requests.post(url, json=payload, timeout=25)
            data = r.json()

            # DEBUG (optional)
            print("TRY MODEL:", model)

            if "error" in data:
                last_error = data["error"]
                continue

            if "candidates" not in data:
                last_error = data
                continue

            return data["candidates"][0]["content"]["parts"][0]["text"]

        except Exception as e:
            last_error = str(e)
            continue

    raise AIModelError(f"All models failed: {last_error}")

# =========================
# WIKIPEDIA SEARCH
# =========================

def wiki_search(query):
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_")
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return ""

        data = r.json()
        return data.get("extract", "") or ""

    except:
        return ""

# =========================
# DUCKDUCKGO SEARCH (SAFE API)
# =========================

def ddg_search(query):
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        results = []

        if data.get("AbstractText"):
            results.append(data["AbstractText"])

        for item in data.get("RelatedTopics", [])[:5]:
            if isinstance(item, dict) and "Text" in item:
                results.append(item["Text"])

        return "\n".join(results)

    except:
        return ""

# =========================
# MASTER SEARCH
# =========================

def web_search(query):

    wiki = wiki_search(query)
    ddg = ddg_search(query)

    return f"""
WIKIPEDIA:
{wiki}

DUCKDUCKGO:
{ddg}
"""

# =========================
# CHAT MODES
# =========================

def ask_chatbot(prompt):

    system = (
        "You are ChatBotTCS for NationStates RMB. "
        "Be short, friendly, use BBCode only."
    )

    return clean_bbcode(call_gemini_strict(system + "\n\nUSER: " + prompt))


def ask_chatsearch(prompt):

    search_data = web_search(prompt)

    system = (
        "You are ChatBotTCS. Use search data to answer accurately. "
        "Prefer Wikipedia. If no useful data exists, say you don't know."
    )

    return clean_bbcode(
        call_gemini_strict(system + "\n\nSEARCH:\n" + search_data + "\n\nQUESTION:\n" + prompt)
    )

# =========================
# RMB POST
# =========================

def post_rmb(text):

    try:
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

        r2 = requests.post(NS_API, data=execute, headers=headers, timeout=20)

        print("POST:", r2.status_code)

    except Exception as e:
        print("POST ERROR:", e)

# =========================
# GET RMB MESSAGES
# =========================

def get_messages():
    try:
        url = f"{NS_API}?region={REGION}&q=messages"
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.text
    except:
        return ""

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
                response = None

                try:

                    if "#chatbot" in msg:
                        q = message.replace("#chatbot", "").strip()
                        response = ask_chatbot(q or "Hello")

                    elif "#chatsearch" in msg:
                        q = message.replace("#chatsearch", "").strip()
                        response = ask_chatsearch(q or "Hello")

                    if response:
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
