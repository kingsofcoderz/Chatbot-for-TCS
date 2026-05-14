import requests

NATION = "chatbottcs"
REGION = "chatbot_of_the_citrus_sea"
PASSWORD = "welcome123"

HEADERS = {
    "User-Agent": "ChatBotTCS/1.0"
}

def post_rmb(text):

    url = "https://www.nationstates.net/cgi-bin/api.cgi"

    # ---------------- PREPARE ----------------

    prepare_data = {
        "c": "rmbpost",
        "nation": NATION,
        "region": REGION,
        "text": text,
        "mode": "prepare"
    }

    prepare_headers = HEADERS.copy()
    prepare_headers["X-Password"] = PASSWORD

    r = requests.post(
        url,
        data=prepare_data,
        headers=prepare_headers
    )

    print("PREPARE STATUS:", r.status_code)
    print(r.text)

    if "<SUCCESS>" not in r.text:
        print("Prepare failed")
        return

    # Get token
    token = r.text.split("<SUCCESS>")[1].split("</SUCCESS>")[0]

    # Get X-Pin
    xpin = r.headers.get("X-Pin")

    print("TOKEN:", token)
    print("XPIN:", xpin)

    # ---------------- EXECUTE ----------------

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

    r2 = requests.post(
        url,
        data=execute_data,
        headers=execute_headers
    )

    print("EXECUTE STATUS:", r2.status_code)
    print(r2.text)

post_rmb("Hello from bot")
