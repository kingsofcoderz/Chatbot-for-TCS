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
    "User-Agent": "ChatBotTCS Debug Bot"
}

NS_API = "https://www.nationstates.net/cgi-bin/api.cgi"

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
# GEMINI
# =========================

def call_gemini(prompt):

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    )

    r = requests.post(url, json={
        "contents": [{"parts": [{"text": prompt}]}]
    }, timeout=25)

    data = r.json()

    if "candidates" not in data:
        raise AIModelError(str(data))

    return data["candidates"][0]["content"]["parts"][0]["text"]

# =========================
# WIKIPEDIA SEARCH (WITH LOGS)
# =========================

def wiki_search(query):

    print("\n🔎 SEARCH QUERY:", query)

    try:
        url = "https://en.wikipedia.org/w/api.php"

        r = requests.get(url, params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }, timeout=10)

        print("📡 WIKI STATUS:", r.status_code)

        try:
            data = r.json()
        except Exception:
            print("❌ WIKI NOT JSON:", r.text[:200])
            return ""

        results = data.get("query", {}).get("search", [])

        print("📦 RESULTS COUNT:", len(results))

        if not results:
            print("⚠️ NO RESULTS FOUND")
            return ""

        title = results[0]["title"]
        print("📘 TOP RESULT:", title)

        summary_url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + title.replace(" ", "_")
        )

        r2 = requests.get(summary_url, timeout=10)

        print("📡 SUMMARY STATUS:", r2.status_code)

        try:
            data2 = r2.json()
        except Exception:
            print("❌ SUMMARY NOT JSON:", r2.text[:200])
            return ""

        extract = data2.get("extract", "")

        print("📄 EXTRACT FOUND:", bool(extract))

        return extract

    except Exception as e:
        print("💥 SEARCH ERROR:", e)
        return ""

# =========================
# SEARCH WRAPPER
# =========================

def web_search(query):

    wiki = wiki_search(query)

    if wiki:
        return wiki

    return "No reliable information found."

# =========================
# CHATSEARCH
# =========================

def ask_chatsearch(prompt):

    data = web_search(prompt)

    print("🧠 FINAL SEARCH DATA:", data[:200])

    system = (
        "Use the search data to answer accurately. "
        "If empty, say you don't know."
    )

    return clean_bbcode(call_gemini(
        system + "\n\nSEARCH:\n" + data + "\n\nQUESTION:\n" + prompt
    ))

# =========================
# BOT LOOP (UNCHANGED CORE)
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

    r = requests.post(NS_API, data=prepare, headers=headers)

    if "<SUCCESS>" not in r.text:
        print("POST FAILED")
        return

    token = r.text.split("<SUCCESS>")[1].split("</SUCCESS>")[0]
    xpin = r.headers.get("X-Pin")

    headers["X-Pin"] = xpin

    requests.post(NS_API, data={
        "c": "rmbpost",
        "nation": NATION,
        "region": REGION,
        "text": text,
        "mode": "execute",
        "token": token
    }, headers=headers)

def get_messages():
    url = f"{NS_API}?region={REGION}&q=messages"
    return requests.get(url, headers=HEADERS).text

def main():

    print("BOT STARTED")

    seen = set()

    while True:

        try:
            xml = get_messages()
            root = ET.fromstring(xml)

            for post in root.findall(".//POST"):

                pid = post.attrib.get("id")
                nation = post.find("NATION").text
                message = post.find("MESSAGE").text

                if not message or pid in seen:
                    continue

                if nation.lower() == NATION.lower():
                    continue

                msg = message.lower()

                if "#chatsearch" in msg:

                    query = message.replace("#chatsearch", "").strip()

                    response = ask_chatsearch(query or "hello")

                    response = response[:500]

                    post_rmb(response)
                    seen.add(pid)

                    time.sleep(15)

        except Exception as e:
            print("LOOP ERROR:", e)

        time.sleep(10)

if __name__ == "__main__":
    main()
