import requests
import xml.etree.ElementTree as ET
import time
import os
import re
from datetime import datetime

# =========================
# CONFIG
# =========================

NATION = "chatbottcs"
REGION = "chatbot_of_the_citrus_sea"

PASSWORD = os.getenv("PASSWORD", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

HEADERS = {
    "User-Agent": (
        "ChatBotTCS/6.0 "
        "(NationStates RMB AI Bot)"
    )
}

NS_API = "https://www.nationstates.net/cgi-bin/api.cgi"

# =========================
# MEMORY
# =========================

conversation_history = []

MAX_MEMORY = 8

# =========================
# LOGGER
# =========================

def log(level, message):

    now = datetime.now().strftime(
        "%H:%M:%S"
    )

    print(
        f"[{now}] [{level}] {message}"
    )

# =========================
# ERROR CLASS
# =========================

class AIModelError(Exception):
    pass

# =========================
# CLEAN TEXT
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
# SAVE MEMORY
# =========================

def save_memory(nation, user_msg, bot_msg):

    global conversation_history

    conversation_history.append({
        "nation": nation,
        "user": user_msg,
        "bot": bot_msg
    })

    conversation_history = (
        conversation_history[-MAX_MEMORY:]
    )

    log(
        "MEMORY",
        f"Saved memory. Total = {len(conversation_history)}"
    )

# =========================
# BUILD CONTEXT
# =========================

def build_context():

    if not conversation_history:
        return "No previous context."

    context = []

    for item in conversation_history:

        context.append(
            f"{item['nation']} said: {item['user']}"
        )

        context.append(
            f"Bot replied: {item['bot']}"
        )

    return "\n".join(context)

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

            log(
                "AI",
                f"Trying model: {model}"
            )

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

            log(
                "HTTP",
                f"{model} status = {r.status_code}"
            )

            try:
                data = r.json()
            except Exception:

                log(
                    "ERROR",
                    f"{model} invalid JSON"
                )

                continue

            if "candidates" not in data:

                last_error = data

                log(
                    "ERROR",
                    f"{model} failed"
                )

                log(
                    "DEBUG",
                    str(data)[:500]
                )

                continue

            text = (
                data["candidates"][0]
                ["content"]["parts"][0]["text"]
            )

            log(
                "AI",
                f"{model} success"
            )

            return text

        except Exception as e:

            last_error = e

            log(
                "ERROR",
                f"{model} crashed: {e}"
            )

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
# SMART QUERY REWRITE
# =========================

def improve_query(query, context):

    q = query.lower()

    if (
        "his full name" in q
        and "vijay" in context.lower()
    ):
        return "What is Vijay full name"

    if (
        "current cm" in q
    ):
        return (
            "Current Chief Minister of Tamil Nadu"
        )

    return query

# =========================
# WIKI SEARCH
# =========================

def wiki_search(query):

    log(
        "SEARCH",
        f"Searching: {query}"
    )

    try:

        search_url = (
            "https://en.wikipedia.org/w/api.php"
        )

        r = requests.get(
            search_url,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 3
            },
            headers=HEADERS,
            timeout=15
        )

        log(
            "HTTP",
            f"Wikipedia status = {r.status_code}"
        )

        try:
            data = r.json()
        except Exception:

            log(
                "ERROR",
                "Wikipedia invalid JSON"
            )

            return ""

        results = (
            data.get("query", {})
            .get("search", [])
        )

        log(
            "SEARCH",
            f"Results = {len(results)}"
        )

        if not results:
            return ""

        collected = []

        for result in results:

            try:

                title = result["title"]

                log(
                    "ARTICLE",
                    f"Checking: {title}"
                )

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

                    extract = relevant_sentences(
                        extract,
                        query
                    )

                    if len(extract) < 40:
                        continue

                    collected.append(
                        f"{title}:\n{extract}"
                    )

                    log(
                        "ARTICLE",
                        f"Added: {title}"
                    )

            except Exception as e:

                log(
                    "ERROR",
                    f"Article failed: {e}"
                )

        final = "\n\n".join(collected)

        log(
            "SEARCH",
            f"Collected = {len(collected)}"
        )

        return final[:4000]

    except Exception as e:

        log(
            "CRASH",
            f"Search crashed: {e}"
        )

        return ""

# =========================
# SEARCH WRAPPER
# =========================

def web_search(query):

    result = wiki_search(query)

    if not result:

        log(
            "SEARCH",
            "No reliable info"
        )

        return "No reliable information found."

    return result

# =========================
# NORMAL CHAT
# =========================

def ask_chatbot(prompt, context):

    system = (
        "You are ChatBotTCS on NationStates RMB. "
        "Be short, friendly, and natural. "
        "Use BBCode only."
    )

    final_prompt = (
        system
        + "\n\nCONTEXT:\n"
        + context
        + "\n\nUSER:\n"
        + prompt
    )

    return clean_bbcode(
        call_gemini(final_prompt)
    )

# =========================
# SEARCH CHAT
# =========================

def ask_chatsearch(prompt, context):

    improved = improve_query(
        prompt,
        context
    )

    log(
        "SEARCH",
        f"Improved query = {improved}"
    )

    research = web_search(improved)

    log(
        "RESEARCH",
        research[:1000]
    )

    system = (
        "You are a search assistant. "
        "Use research data first. "
        "Use conversation context if needed. "
        "Prioritize current information. "
        "Be direct and concise. "
        "Do not invent facts."
    )

    final_prompt = (
        system
        + "\n\nCONTEXT:\n"
        + context
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

    log(
        "POST",
        f"Posting ({len(text)} chars)"
    )

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

        log(
            "ERROR",
            "Prepare failed"
        )

        log(
            "DEBUG",
            r.text[:500]
        )

        return

    token = (
        r.text
        .split("<SUCCESS>")[1]
        .split("</SUCCESS>")[0]
    )

    xpin = r.headers.get("X-Pin")

    if not xpin:

        log(
            "ERROR",
            "Missing X-Pin"
        )

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

    log(
        "POST",
        f"Execute status = {r2.status_code}"
    )

# =========================
# RMB FETCH
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

    log(
        "START",
        "Bot started"
    )

    seen_posts = set()

    while True:

        try:

            xml_data = get_messages()

            root = ET.fromstring(xml_data)

            posts = root.findall(".//POST")

            log(
                "RMB",
                f"Posts fetched = {len(posts)}"
            )

            context = build_context()

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

                log(
                    "MESSAGE",
                    f"{nation}: {message[:100]}"
                )

                msg = message.lower()

                response = None

                try:

                    if "#chatbot" in msg:

                        cleaned = (
                            message
                            .replace("#chatbot", "")
                            .strip()
                        )

                        if not cleaned:
                            cleaned = "Hello"

                        response = ask_chatbot(
                            cleaned,
                            context
                        )

                    elif "#chatsearch" in msg:

                        cleaned = (
                            message
                            .replace("#chatsearch", "")
                            .strip()
                        )

                        if not cleaned:
                            cleaned = "Hello"

                        response = ask_chatsearch(
                            cleaned,
                            context
                        )

                    else:
                        continue

                    response = response[:500]

                    log(
                        "FINAL",
                        response
                    )

                    post_rmb(response)

                    save_memory(
                        nation,
                        cleaned,
                        response
                    )

                    seen_posts.add(post_id)

                    time.sleep(15)

                except AIModelError as e:

                    log(
                        "ERROR",
                        f"AI failed: {e}"
                    )

        except Exception as e:

            log(
                "CRASH",
                f"Loop crashed: {e}"
            )

        time.sleep(10)

# =========================
# START
# =========================

if __name__ == "__main__":
    main()
