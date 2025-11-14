import os
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

# --------------------------------------------------
# 天気
# --------------------------------------------------
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

# --------------------------------------------------
# ルート
# --------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/logs")
def show_logs():
    return render_template("logs.html")

# --------------------------------------------------
# 会話
# --------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "").strip()

    # ---- 特殊対応 ----
    if "天気" in user_text:
        reply_text = get_weather(user_text)

    elif any(k in user_text for k in ["時間", "何時"]):
        now = datetime.datetime.now().strftime("%H時%M分")
        reply_text = f"今は{now}だよ！"

    else:
        prompt = (
            "あなたは明るく優しい孫のゆうくんです。"
            "利用者に自然で丁寧に返答し、話題に合わせて回答を変えます。"
            "60〜80代向けにゆっくり優しく話してください。"
            "呼称として「おばあちゃん」「おじいちゃん」は使わない。"
            "同じ返答は繰り返さず、会話に応じて変化させてください。"
        )

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text}
            ]
        )
        reply_text = res.choices[0].message.content.strip()

    # --------------------------------------------------
    # TTS（上書き→ストレージ枯渇防止）
    # --------------------------------------------------
    audio_path = "static/output.mp3"

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=reply_text
    )
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    return jsonify({
        "reply": reply_text,
        "audio_url": "/" + audio_path + "?t=" + str(datetime.datetime.now().timestamp())
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
