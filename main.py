import requests
import xml.etree.ElementTree as ET
import time
import os
import re
import threading
from datetime import datetime
from flask import Flask, request, jsonify

# =========================
# CONFIG
# =========================

NATION = "chatbottcs"
REGION = "the_citrus_sea"

PASSWORD = os.getenv("PASSWORD", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change_me")

HEADERS = {
    "User-Agent": "ChatBotTCS/1.0 (NationStates RMB AI Bot)"
}

NS_API = "https://www.nationstates.net/cgi-bin/api.cgi"

STATE_FILE = "bot_state.txt"


def bot_enabled():
    try:
        return open(STATE_FILE).read().strip() == "on"
    except:
        return True


def set_state(v):
    with open(STATE_FILE, "w") as f:
        f.write(v)

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({"status": "on" if bot_enabled() else "off"})


@app.route("/on")
def on():
    if request.args.get("key") != ADMIN_SECRET:
        return jsonify({"error": "unauthorized"}), 403
    set_state("on")
    return jsonify({"bot": "ON"})

@app.route("/off")
def off():

    if request.args.get("key") != ADMIN_SECRET:
        return jsonify({"error": "unauthorized"}), 403

    set_state("off")

    return jsonify({"bot": "OFF"})

user_memories = {}
MAX_MEMORY = 5


def log(level, message):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{level}] {message}")


def save_memory(nation, user_msg, bot_msg):
    nation = nation.lower()

    if nation not in user_memories:
        user_memories[nation] = []

    user_memories[nation].append({
        "user": user_msg,
        "bot": bot_msg
    })

    user_memories[nation] = user_memories[nation][-MAX_MEMORY:]


def build_context(nation):
    nation = nation.lower()

    if nation not in user_memories:
        return "No previous context."

    return "\n".join(
        f"User: {m['user']}\nBot: {m['bot']}"
        for m in user_memories[nation]
)

class AIModelError(Exception):
    pass


def call_gemini(prompt):

    MODELS = [

        "gemini-2.5-flash",

        "gemini-2.5-flash-lite-preview-06-17",

        "gemini-2.0-flash",

        "gemini-2.0-flash-lite"

    ]

    last_error = None

    for model in MODELS:

        try:

            log(
                "AI",
                f"Trying {model}"
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
                f"{model} -> {r.status_code}"
            )

            try:
                data = r.json()
            except Exception:
                log(
                    "ERROR",
                    f"{model} returned invalid JSON"
                )
                log(
                    "DEBUG",
                    r.text[:500]
                )
                continue
            if "candidates" not in data:
                last_error = data
                log(
                    "ERROR",
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

CHATBOT_SYSTEM = """
You are ChatBotTCS on NationStates RMB.

Rules:
- Be short, natural, friendly
- Allowed BBCode ONLY: [b], [i], [u], [nation], [region]
- Forbidden: [color], [size], [quote], [url], [img], [list], [*]
- Never use markdown
- Never invent BBCode tags
"""


SEARCH_SYSTEM = """
You are a search assistant for NationStates RMB.

Rules:
- Use ONLY provided research
- Do not hallucinate facts
- Be concise
- Allowed BBCode ONLY: [b], [i], [u], [nation], [region]
"""

def improve_query(query, context):

    try:
        prompt = f"""
Convert this into a Wikipedia search query.

Rules:
- short
- no filler
- keep names

Context:
{context}

Query:
{query}

Output ONLY query
"""

        response = call_gemini(prompt).replace("\n", " ").strip()
        return response[:100] if len(response) > 3 else query

    except:
        return query


def relevant_sentences(text, query):

    q = set(re.findall(r"\w+", query.lower()))
    sentences = re.split(r'(?<=[.!?]) +', text)

    scored = []

    for s in sentences:
        words = set(re.findall(r"\w+", s.lower()))
        overlap = len(q & words)

        score = overlap / (len(q) + 1)

        if query.lower() in s.lower():
            score += 1.5

        scored.append((score, s))

    scored.sort(reverse=True, key=lambda x: x[0])

    return " ".join([s for _, s in scored[:10]]) or text[:1200]

def wiki_search(query):

    log("SEARCH", f"Searching: {query}")

    try:

        url = "https://en.wikipedia.org/w/api.php"

        r = requests.get(
            url,
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

        log("HTTP", f"Wikipedia search = {r.status_code}")

        try:
            data = r.json()

        except Exception:

            log("ERROR", "Wikipedia search invalid JSON")
            log("DEBUG", r.text[:500])

            return ""

        results = data.get("query", {}).get("search", [])

        log("SEARCH", f"Results = {len(results)}")

        if not results:
            return ""

        collected = []

        for result in results:

            try:

                title = result["title"]

                log("ARTICLE", f"Checking {title}")

                r2 = requests.get(
                    url,
                    params={
                        "action": "query",
                        "prop": "extracts",
                        "explaintext": True,
                        "titles": title,
                        "format": "json"
                    },
                    headers=HEADERS,
                    timeout=15
                )

                try:
                    data2 = r2.json()

                except Exception:

                    log("ERROR", "Wikipedia extract invalid JSON")
                    log("DEBUG", r2.text[:500])

                    continue

                pages = data2.get("query", {}).get("pages", {})

                for page in pages.values():

                    extract = page.get("extract", "")

                    if not extract:
                        continue

                    extract = relevant_sentences(
                        extract,
                        query
                    )

                    if len(extract) < 50:
                        continue

                    collected.append(
                        f"{title}:\n{extract}"
                    )

                    log("ARTICLE", f"Added {title}")

            except Exception as e:

                log("ERROR", f"Article failed: {e}")

        final = "\n\n".join(collected)

        log("SEARCH", f"Collected = {len(collected)}")

        return final[:5000]

    except Exception as e:

        log("CRASH", f"Search crashed: {e}")

        return ""

seen_posts = set()

def get_messages():
    url = f"{NS_API}?region={REGION}&q=messages"
    r = requests.get(url, headers=HEADERS)
    return ET.fromstring(r.text).findall(".//POST")


def post_rmb(text):

    data = {
        "c": "rmbpost",
        "nation": NATION,
        "region": REGION,
        "text": text,
        "mode": "prepare"
    }

    headers = HEADERS.copy()
    headers["X-Password"] = PASSWORD

    r = requests.post(NS_API, data=data, headers=headers)

    if "<SUCCESS>" not in r.text:
        return

    token = r.text.split("<SUCCESS>")[1].split("</SUCCESS>")[0]
    xpin = r.headers.get("X-Pin")

    if not xpin:
        return

    data["mode"] = "execute"
    data["token"] = token
    headers["X-Pin"] = xpin

    requests.post(NS_API, data=data, headers=headers)

def ask_chatbot(prompt, context):

    final_prompt = CHATBOT_SYSTEM + f"""

Context:
{context}

User:
{prompt}
"""

    return call_gemini(final_prompt)


def ask_chatsearch(prompt, context):

    optimized = improve_query(prompt, context)
    wiki = wiki_search(optimized)

    final_prompt = SEARCH_SYSTEM + f"""

Context:
{context}

Research:
{wiki}

Question:
{prompt}
"""

    return call_gemini(final_prompt)

def bot_loop():

    log("START", "Bot running")

    while True:

        if not bot_enabled():
            log("CONTROL", "BOT OFF")
            time.sleep(5)
            continue

        log("CONTROL", "BOT ON")

        try:
            posts = get_messages()

            for post in posts:

                pid = post.attrib.get("id")
                if pid in seen_posts:
                    continue

                seen_posts.add(pid)

                nation = post.find("NATION").text
                msg = post.find("MESSAGE").text

                if not msg or nation.lower() == NATION.lower():
                    continue

                context = build_context(nation)
                lower = msg.lower()

                if "#chatsearch" in lower:
                    q = msg.replace("#chatsearch", "")
                    reply = ask_chatsearch(q, context)

                elif "#chatbot" in lower:
                    q = msg.replace("#chatbot", "")
                    reply = ask_chatbot(q, context)

                else:
                    continue

                final = f"Replying to [nation]{nation}[/nation]\n\n{reply}"[:500]

                post_rmb(final)
                save_memory(nation, msg, reply)

                time.sleep(20)

        except Exception as e:
            log("ERROR", str(e))

        time.sleep(10)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
