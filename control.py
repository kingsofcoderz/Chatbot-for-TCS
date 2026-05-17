from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# =========================
# CONFIG
# =========================

STATE_FILE = "bot_state.txt"
SECRET = os.getenv("ADMIN_SECRET", "change_me")


# =========================
# STATE HANDLING
# =========================

def set_state(state: str):
    with open(STATE_FILE, "w") as f:
        f.write(state)


def get_state():
    try:
        with open(STATE_FILE, "r") as f:
            return f.read().strip()
    except:
        return "on"  # default state


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return jsonify({
        "bot_status": get_state(),
        "endpoints": {
            "on": "/on?key=YOUR_KEY",
            "off": "/off?key=YOUR_KEY"
        }
    })


@app.route("/on")
def turn_on():
    if request.args.get("key") != SECRET:
        return jsonify({"error": "unauthorized"}), 403

    set_state("on")
    return jsonify({"status": "BOT ON"})


@app.route("/off")
def turn_off():
    if request.args.get("key") != SECRET:
        return jsonify({"error": "unauthorized"}), 403

    set_state("off")
    return jsonify({"status": "BOT OFF"})


# =========================
# RAILWAY ENTRY POINT
# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
