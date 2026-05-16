import requests
import xml.etree.ElementTree as ET
import time
import os
import re

# =========================
# CONFIG
# =========================

NATION = "chatbottcs"
REGION = "chatbot_of_the_citrus_sea"

PASSWORD = os.getenv("PASSWORD", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

HEADERS = {
    "User-Agent": (
        "ChatBotTCS/4.0 "
        "(NationStates RMB research bot)"
    )
}

NS_API = "https://www.nationstates.net/cgi-bin/api.cgi"

# =========================
# ERROR CLASS
# =========================

class AIModelError(Exception):
    pass

# =========================
# CLEAN BBCode
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

    for tag in blocked:
        text = text.replace(tag, "")

    text = text.replace("\n", " ")

    return text.strip()

# =========================
# GEMINI API
# =========================

def call_gemini(prompt):

    MODELS = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite-preview-06-17",
        "gemini-1.5-flash"
    ]

    last_error = None

    for model in MODELS:

        try:

            print(f"\n🤖 TRYING MODEL: {model}")

            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={GEMINI_API_KEY}"
            )

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
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
            except:
                continue

            if "candidates" not in data:
                last_error = data
                continue

            return (
                data["candidates"][0]
                ["content"]["parts"][0]["text"]
            )

        except Exception as e:
            last_error = e

    raise AIModelError(
        f"All models failed: {last_error}"
    )

# =========================
# RELEVANCE FILTER
# =========================

def relevant_sentences(text, query):

    keywords = re.findall(
        r"\w+",
        query.lower()
    )

    sentences = re.split(
        r'(?<=[.!?]) +',
        text
    )

    good = []

    for sentence in sentences:

        s = sentence.lower()

        score = 0

        for keyword in keywords:

            if keyword in s:
                score += 1

        if score >= 1:
            good.append(sentence)

    if not good:
        return text[:700]

    return " ".join(good[:10])

# =========================
# MULTI-PAGE WIKI SEARCH
# =========================

def wiki_search(query):

    print("\n🔎 SEARCH:", query)

    try:

        search_url = (
            "https://en.wikipedia.org/w/api.php"
        )

        # =========================
        # SEARCH ARTICLES
        # =========================

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

        results = (
            data.get("query", {})
            .get("search", [])
        )

        print("📦 RESULTS:", len(results))

        if not results:
            return ""

        collected = []

        # =========================
        # GET ARTICLE EXTRACTS
        # =========================

        for result in results:

            try:

                title = result["title"]

                print("📘 ARTICLE:", title)

                r2 = requests.get(
                    search_url,
                    params={
                        "action": "query",
                        "prop": "extracts",
                        "exintro": True,
                        "explaintext": True,
                        "titles": title,
                        "format": "json"
                    },
                    headers=HEADERS,
                    timeout=15
                )

                try:
                    data2 = r2.json()
                except:
                    continue

                pages = (
                    data2.get("query", {})
                    .get("pages", {})
                )

                for page_id in pages:

                    page = pages[page_id]

                    extract = page.get(
                        "extract",
                        ""
                    )

                    if not extract:
                        continue

                    # =========================
                    # SMART FILTER
                    # =========================

                    extract = relevant_sentences(
                        extract,
                        query
                    )

                    if len(extract) < 40:
                        continue

                    collected.append(
                        f"{title}:\n{extract}"
                    )

            except Exception as e:
                print("⚠️ ARTICLE ERROR:", e)

        print("🧠 COLLECTED:", len(collected))

        final = "\n\n".join(collected)

        return final[:4000]

    except Exception as e:
        print("💥 SEARCH ERROR:", e)
        return ""

# =========================
# SEARCH WRAPPER
# =========================

def web_search(query):

    result = wiki_search(query)

    if not result:
        return "No reliable information found."

    return result

# =========================
# NORMAL CHAT
# =========================

def ask_chatbot(prompt):

    system = (
        "You are ChatBotTCS on NationStates RMB. "
        "Be short, friendly, natural, and use BBCode only."
    )

    final_prompt = (
        system
        + "\n\nUSER:\n"
        + prompt
    )

    return clean_bbcode(
        call_gemini(final_prompt)
    )

# =========================
# SEARCH CHAT
# =========================

def ask_chatsearch(prompt):

    research = web_search(prompt)

    print("\n🧠 RESEARCH DATA:\n")
    print(research[:1500])

    system = (
        "You are a search assistant. "
        "Answer ONLY using the research data. "
        "Prioritize answering the CURRENT status first. "
        "Be direct and concise. "
        "Do not add unrelated history unless asked. "
        "If uncertain, say you don't know."
    )

    final_prompt = (
        system
        + "\n\nRESEARCH DATA:\n"
        + research
        + "\n\nQUESTION:\n"
        + prompt
    )

    response = call_gemini(final_prompt)

    return clean_bbcode(response)

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

    r = requests.post(
        NS_API,
        data=prepare_data,
        headers=headers,
        timeout=20
    )

    if "<SUCCESS>" not in r.text:
        print("❌ PREPARE FAILED")
        print(r.text)
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

    execute_data = {
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
        data=execute_data,
        headers=headers,
        timeout=20
    )

    print("✅ POSTED:", r2.status_code)

# =========================
# RMB READER
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

                if nation.lower() == NATION.lower():
                    continue

                if post_id in seen_posts:
                    continue

                msg = message.lower()

                response = None

                try:

                    # =========================
                    # NORMAL CHAT
                    # =========================

                    if "#chatbot" in msg:

                        cleaned = (
                            message
                            .replace("#chatbot", "")
                            .strip()
                        )

                        if not cleaned:
                            cleaned = "Hello"

                        response = ask_chatbot(
                            cleaned
                        )

                    # =========================
                    # SEARCH MODE
                    # =========================

                    elif "#chatsearch" in msg:

                        cleaned = (
                            message
                            .replace("#chatsearch", "")
                            .strip()
                        )

                        if not cleaned:
                            cleaned = "Hello"

                        response = ask_chatsearch(
                            cleaned
                        )

                    else:
                        continue

                    response = response[:500]

                    print("\n💬 FINAL RESPONSE:")
                    print(response)

                    post_rmb(response)

                    seen_posts.add(post_id)

                    time.sleep(15)

                except AIModelError as e:

                    print("❌ AI FAILED:", e)

        except Exception as e:

            print("💥 LOOP ERROR:", e)

        time.sleep(10)

# =========================
# START
# =========================

if __name__ == "__main__":
    main()n💬 FINAL RESPONSE:")
                    print(response)

                    post_rmb(response)

                    seen_posts.add(post_id)

                    time.sleep(15)

                except AIModelError as e:

                    print("❌ AI FAILED:", e)

        except Exception as e:

            print("💥 LOOP ERROR:", e)

        time.sleep(10)

# =========================
# START
# =========================

if __name__ == "__main__":
    main()
