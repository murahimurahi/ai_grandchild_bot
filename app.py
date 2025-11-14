import os
import json
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from openai import OpenAI
import requests

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

LOG_FILE = "logs.json"


# -----------------------------
# ログ保存
# -----------------------------
def save_log(user, reply, audio_url):
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)

    logs.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "reply": reply,
        "audio_url": audio_url
    })

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


# -----------------------------
# Web UI
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/logs")
def view_logs():
    if not os.path.exists(LOG_FILE):
        return "まだログはありません。"

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = json.load(f)

    html = "<h2>会話ログ</h2>"
    for l in logs:
        html += f"<p><b>{l['time']} / YOU:</b> {l['user']}<br>"
        html += f"<b>Yukun:</b> {l['reply']}<br>"
        if l["audio_url"]:
            html += f"<audio controls src='{l['audio_url']}'></audio></p><hr>"
    return html


# -----------------------------
# Speech-to-Text
# -----------------------------
@app.route("/voice", methods=["POST"])
def voice_to_text():
    audio = request.files["audio"]

    text = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=audio
    ).text

    return jsonify({"text": text})


# -----------------------------
# 会話（本体）
# -----------------------------
@app.route("/talk", methods=["POST"])
def talk():
    user_text = request.json.get("user_text", "")

    # --- GPT 返答 ---
    gpt = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは優しいAIのゆうくん。語尾はやわらかい。返答は短め。"},
            {"role": "user", "content": user_text}
        ],
        temperature=0.6
    )

    reply = gpt.choices[0].message["content"]

    # --- TTS ---
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=reply
    )

    audio_path = f"static/{datetime.now().timestamp()}.mp3"
    speech.stream_to_file(audio_path)
    audio_url = "/" + audio_path

    # --- ログ保存 ---
    save_log(user_text, reply, audio_url)

    return jsonify({
        "reply": reply,
        "audio_url": audio_url
    })


# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
