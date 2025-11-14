import os
import json
import datetime
import logging
import requests
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

LOG_FILE = "logs.json"

# ==========================================================
# 天気
# ==========================================================
def get_weather(user_text="東京"):
    try:
        import re
        city_match = re.search(r"(.+?)の天気", user_text)
        city = city_match.group(1) if city_match else "東京"

        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}"
            f"&units=metric&lang=ja"
        )
        res = requests.get(url, timeout=6)
        data = res.json()

        if data.get("cod") != 200:
            return f"{city}の天気は見つからなかったよ。"

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"今の{city}の天気は{desc}、気温は{temp:.1f}度だよ！"

    except:
        return "天気情報を取得できなかったよ。"

# ==========================================================
# ログ保存
# ==========================================================
def save_log(user_text, reply_text, audio_url):
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)

    logs.append({
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_text,
        "reply": reply_text,
        "audio": audio_url
    })

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# ==========================================================
# ルーティング
# ==========================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/logs")
def view_logs():
    if not os.path.exists(LOG_FILE):
        return "<h2>まだログはありません。</h2>"

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = json.load(f)

    html = "<h2>会話ログ</h2>"
    for l in logs:
        html += f"<p><b>{l['time']}</b><br>"
        html += f"<b>あなた：</b> {l['user']}<br>"
        html += f"<b>ゆうくん：</b> {l['reply']}<br>"
        if l["audio"]:
            html += f"<audio controls src='{l['audio']}'></audio>"
        html += "<hr></p>"

    return html

# ==========================================================
# 音声 → テキスト（5秒録音対応）
# ==========================================================
@app.route("/voice", methods=["POST"])
def voice_to_text():
    audio_file = request.files["audio"]

    text = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=audio_file
    ).text

    return jsonify({"text": text})

# ==========================================================
# 会話本体
# ==========================================================
@app.route("/talk", methods=["POST"])
def talk():
    user_text = request.json.get("message", "").strip()

    # ----- 特殊処理 -----
    if "天気" in user_text:
        reply = get_weather(user_text)

    elif any(k in user_text for k in ["時間", "何時"]):
        now = datetime.datetime.now().strftime("%H時%M分")
        reply = f"今は{now}だよ！"

    else:
        prompt = (
            "あなたは優しいAIのゆうくんです。"
            "60〜80代向けにゆっくり丁寧に話します。"
            "返答は毎回変化させて、同じ内容を繰り返さないようにしてください。"
            "呼称として「おばあちゃん」「おじいちゃん」は使わない。"
        )

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.65
        )

        reply = res.choices[0].message["content"].strip()

    # ----- 音声生成（途切れ防止） -----
    filename = f"static/yukun_{datetime.datetime.now().timestamp()}.mp3"

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=reply,
    )
    speech.stream_to_file(filename)

    audio_url = "/" + filename

    # ----- ログ保存 -----
    save_log(user_text, reply, audio_url)

    return jsonify({
        "reply": reply,
        "audio_url": audio_url
    })

# ==========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
