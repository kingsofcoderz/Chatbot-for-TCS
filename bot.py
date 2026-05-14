import requests

NATION = "chatbottcs"
REGION = "chatbot_of_the_citrus_sea"
PASSWORD = "welcome123"

HEADERS = {
    "User-Agent": "ChatBotTCS Testing Bot"
}

def post_rmb(text):
    url = "https://www.nationstates.net/cgi-bin/api.cgi"

    data = {
        "c": "rmbpost",
        "nation": NATION,
        "region": REGION,
        "text": text,
        "mode": "prepare"
    }

    headers = HEADERS.copy()
    headers["X-Password"] = PASSWORD

    # STEP 1: PREPARE
    r = requests.post(url, data=data, headers=headers)

    print("PREPARE STATUS:", r.status_code)
    print(r.text)

    if "<SUCCESS>" not in r.text:
        print("Prepare failed")
        return

    # Extract token
    token = r.text.split("<SUCCESS>")[1].split("</SUCCESS>")[0]

    # STEP 2: EXECUTE
    data["mode"] = "execute"
    data["token"] = token

    r2 = requests.post(url, data=data, headers=headers)

    print("EXECUTE STATUS:", r2.status_code)
    print(r2.text)

post_rmb("Bot online test")
