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
    "User-Agent": (
        "ChatBotTCS/2.0 "
        "(NationStates RMB research bot; contact: dev)"
    )
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

    blocked = [
        "**",
        "__",
        "[img]",
        "[/img]",
        "[url]",
        "[/url]",
        "[quote]",
        "[/quote]"
    ]

    for x in blocked:
        text = text.replace(x, "")

    return text.replace("\n", " ").strip()

# =========================
# GEMINI
# =========================

def call_gemini(prompt):

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    r = requests.post(
        url,
        json=payload,
        timeout=30
    )

    try:
        data = r.json()
    except Exception:
        raise AIModelError("Gemini returned invalid JSON")

    if "candidates" not in data:
        raise AIModelError(str(data))

    return data["candidates"][0]["content"]["parts"][0]["text"]

# =========================
# MULTI-PAGE WIKIPEDIA SEARCH
# =========================

def wiki_search(query):

    print("\n🔎 SEARCH:", query)

    try:

        search_url = "https://en.wikipedia.org/w/api.php"

        r = requests.get(
            search_url,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 5
            },
            headers=HEADERS,
            timeout=15
        )

        print("📡 SEARCH STATUS:", r.status_code)

        try:
            data = r.json()
        except Exception:
            print("❌ SEARCH NOT JSON")
            return ""

        results = data.get("query", {}).get("search", [])

        print("📦 RESULTS FOUND:", len(results))

        if not results:
            return ""

        collected = []

        # =========================
        # CHECK MULTIPLE ARTICLES
        # =========================

        for result in results:

            try:

                title = result["title"]

                print("📘 CHECKING:", title)

                summary_url = (
                    "https://en.wikipedia.org/api/rest_v1/page/summary/"
                    + title.replace(" ", "_")
                )

                r2 = requests.get(
                    summary_url,
                    headers=HEADERS,
                    timeout=10
                )

                print("📡 SUMMARY STATUS:", r2.status_code)

                if r2.status_code != 200:
                    continue

                try:
                    data2 = r2.json()
                except Exception:
                    continue

                extract = data2.get("extract", "")

                if not extract:
                    continue

                # Trim huge articles
                extract = extract[:800]

                collected.append(
                    f"{title}:\n{extract}"
                )

            except Exception as e:
                print("⚠️ ARTICLE ERROR:", e)

        print("🧠 ARTICLES COLLECTED:", len(collected))

        return "\n\n".join(collected)

    except Exception as e:
        print("💥 SEARCH ERROR:", e)
        return ""

# =========================
# SEARCH WRAPPER
# =========================

def web_search(query):

    research = wiki_search(query)

    if not research:
        return "No reliable information found."

    return research

# =========================
# CHATBOT MODE
# =========================

def ask_chatbot(prompt):

    system = (
        "You are ChatBotTCS for NationStates RMB. "
        "Be short, friendly, and use BBCode only."
    )

    return clean_bbcode(
        call_gemini(
            system + "\n\nUSER:\n" + prompt
        )
    )

# =========================
# CHATSEARCH MODE
# =========================

def ask_chatsearch(prompt):

    research = web_search(prompt)

    print("\n🧠 FINAL RESEARCH:")
    print(research[:1000])

    system = (
        "You are ChatBotTCS. "
        "Answer ONLY using the research data provided. "
        "Use the newest and most relevant information. "
        "Do not guess or hallucinate. "
        "If uncertain, say you don't know."
    )

    final_prompt = (
        system
        + "\n\nRESEARCH DATA:\n"
        + research
        + "\n\nQUESTION:\n"
        + prompt
    )

    return clean_bbcode(
        call_gemini(final_prompt)
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

    r = requests.post(
        NS_API,
        data=prepare,
        headers=headers,
        timeout=20
    )

    if "<SUCCESS>" not in r.text:
        print("❌ POST FAILED")
        return

    token = (
        r.text
        .split("<SUCCESS>")[1]
        .split("</SUCCESS>")[0]
    )

    xpin = r.headers.get("X-Pin")

    if not xpin:
        print("❌ NO XPIN")
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

    r2 = requests.post(
        NS_API,
        data=execute,
        headers=headers,
        timeout=20
    )

    print("✅ RMB POSTED:", r2.status_code)

# =========================
# GET RMB POSTS
# =========================

def get_messages():

    url = (
        f"{NS_API}"
        f"?region={REGION}&q=messages"
    )

    r = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    return r.text

# =========================
# MAIN LOOP
# =========================

def main():

    print("🚀 BOT STARTED")

    seen = set()

    while True:

        try:

            xml = get_messages()

            root = ET.fromstring(xml)

            posts = root.findall(".//POST")

            for post in posts:

                pid = post.attrib.get("id")

                nation = post.find("NATION").text
                message = post.find("MESSAGE").text

                if not message:
                    continue

                if nation.lower() == NATION.lower():
                    continue

                if pid in seen:
                    continue

                msg = message.lower()

                response = None

                try:

                    # =========================
                    # NORMAL CHAT
                    # =========================

                    if "#chatbot" in msg:

                        q = (
                            message
                            .replace("#chatbot", "")
                            .strip()
                        )

                        response = ask_chatbot(
                            q or "Hello"
                        )

                    # =========================
                    # RESEARCH MODE
                    # =========================

                    elif "#chatsearch" in msg:

                        q = (
                            message
                            .replace("#chatsearch", "")
                            .strip()
                        )

                        response = ask_chatsearch(
                            q or "Hello"
                        )

                    else:
                        continue

                    response = response[:500]

                    print("\n💬 FINAL RESPONSE:")
                    print(response)

                    post_rmb(response)

                    seen.add(pid)

                    time.sleep(15)

                except AIModelError as e:

                    print("❌ AI FAILED:", e)

        except Exception as e:

            print("💥 LOOP ERROR:", e)

        time.sleep(10)

# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()
