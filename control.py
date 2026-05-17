from flask import Flask, request
import os

app = Flask(__name__)

STATE_FILE = "bot_state.txt"

# simple secret key (set in Railway env vars)
SECRET = os.getenv("ADMIN_SECRET", "change_me")


# =========================
# STATE HANDLING
# =========================

def set_state(state):
    with open(STATE_FILE, "w") as f:
        f.write(state)


def get_state():
    try:
        return open(STATE_FILE).read().strip()
    except:
        return "on"


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return {
        "bot_status": get_state(),
        "usage": "/on?key=xxx or /off?key=xxx"
    }


@app.route("/on")
def turn_on():

    if request.args.get("key") != SECRET:
        return {"error": "unauthorized"}, 403

    set_state("on")
    return {"status": "BOT ON"}


@app.route("/off")
def turn_off():

    if request.args.get("key") != SECRET:
        return {"error": "unauthorized"}, 403

    set_state("off")
    return {"status": "BOT OFF"}


# =========================
# RUN (RAILWAY)
# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
