import os
import datetime
import logging
import requests
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import json

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


# -----------------------------
# 天気取得（改善版）
# -----------------------------
def get_weather(user_text="東京"):
    try:
        import re
        city_match = re.search(r"(.+?)の天気", user_text)
        city = city_match.group(1) if city_match else user_text

        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}"
            "&units=metric&lang=ja"
        )
        res = requests.get(url, timeout=6)
        data = res.json()

        if data.get("cod") != 200:
            return f"{city}の天気は分からなかったよ。"

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"今の{city}の天気は{desc}、気温は{temp:.1f}度だよ！"

    except Exception:
        return "天気情報を取得できなかったよ。"


# -----------------------------
# ページ
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/logs")
def logs():
    files = sorted(os.listdir(LOG_DIR))
    files = [f for f in files if not f.startswith(".")]
    return render_template("logs.html", files=files)


# -----------------------------
# 会話処理
# -----------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "").strip()

    # ログ日付フォルダを自動生成
    day = datetime.datetime.now().strftime("%Y-%m-%d")
    folder = os.path.join(LOG_DIR, day)
    os.makedirs(folder, exist_ok=True)

    # --------------- 特殊処理 ---------------
    if "天気" in user_text:
        reply_text = get_weather(user_text)

    elif any(k in user_text for k in ["時間", "何時"]):
        now = datetime.datetime.now().strftime("%H時%M分")
        reply_text = f"今は{now}だよ！"

    else:
        system_prompt = (
            "あなたは明るく優しい孫のゆうくんです。\n"
            "利用者に自然で丁寧に返答し、60〜80代向けに優しく話します。\n"
            "呼称として「おばあちゃん」「おじいちゃん」は使わない。\n"
        )

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
        )
        reply_text = res.choices[0].message.content.strip()

    # --------------- 音声生成 ---------------
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_file = f"output_{ts}.mp3"
    audio_path = f"static/{audio_file}"

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=reply_text
    )
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    # --------------- ログ保存（音声も） ---------------
    log_json = {
        "time": ts,
        "user": user_text,
        "reply": reply_text,
        "audio": audio_file
    }

    with open(os.path.join(folder, f"{ts}.json"), "w", encoding="utf-8") as f:
        json.dump(log_json, f, ensure_ascii=False, indent=2)

    return jsonify({
        "reply": reply_text,
        "audio_url": "/" + audio_path
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
