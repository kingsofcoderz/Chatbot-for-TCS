import requests
import time

NATION = "chatbottcs"
REGION = "chatbot_of_the_citrus_sea"

NS_HEADERS = {
    "User-Agent": "ChatBotTCS Bot"
}

def ask_ai(prompt):
    try:
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma:1b",
                "prompt": f"You are a helpful AI bot. Reply clearly.\nUser: {prompt}",
                "stream": False
            },
            timeout=30
        )
        return r.json().get("response", "No response")
    except:
        return "🤖 AI is offline, but I saw your message."

def get_messages():
    url = f"https://www.nationstates.net/cgi-bin/api.cgi?region={REGION}&q=messages"
    r = requests.get(url, headers=NS_HEADERS)
    return r.text

def post_rmb(text):
    url = "https://www.nationstates.net/cgi-bin/api.cgi"
    data = {
        "c": "rmbpost",
        "nation": NATION,
        "region": REGION,
        "text": text,
        "mode": "post"
    }
    requests.post(url, data=data, headers=NS_HEADERS)

def main():
    print("Bot started...")

    last_seen = ""

    while True:
        try:
            data = get_messages()

            if "#chatgpt" in data and data != last_seen:
                print("Trigger found")

                reply = ask_ai(data)

                post_rmb(reply)

                last_seen = data

        except Exception as e:
            print("Error:", e)

        time.sleep(10)

if __name__ == "__main__":
    main()
