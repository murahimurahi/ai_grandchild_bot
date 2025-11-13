import os
import json
import datetime
import logging
import requests
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# -----------------------------
# OpenAI & OpenWeather
# -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ===========================================================
# ローカルログ保存（TXT＋音声ファイル）
# ===========================================================
def save_local_log(user_text, reply_text, audio_filename):
    try:
        # logs/2025-01-15/ のように日付フォルダを作成
        today = datetime.date.today().strftime("%Y-%m-%d")
        folder_path = os.path.join("logs", today)
        os.makedirs(folder_path, exist_ok=True)

        # テキストログのパス
        log_path = os.path.join(folder_path, f"{today}.txt")

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        log_line = (
            f"[{timestamp}]\n"
            f"👤User: {user_text}\n"
            f"🤖Yuu:  {reply_text}\n"
            f"🎧 audio: {audio_filename}\n\n"
        )

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)

    except Exception as e:
        logging.error(f"ローカルログ保存エラー: {e}")

# ===========================================================
# 天気（OpenWeather）
# ===========================================================
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
            return f"{city}の天気情報が見つからなかったよ。"

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"今の{city}の天気は{desc}、気温は{temp:.1f}度だよ！"

    except Exception as e:
        logging.error(f"天気取得エラー: {e}")
        return "天気情報を取得できなかったよ。"

# ===========================================================
# Flask ルート
# ===========================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "").strip()

    # ▼ 特殊応答
    if "天気" in user_text:
        reply_text = get_weather(user_text)

    elif any(k in user_text for k in ["時間", "何時"]):
        now = datetime.datetime.now().strftime("%H時%M分")
        reply_text = f"今は{now}だよ！"

    else:
        # ▼ 通常会話（ゆうくん）
        prompt = (
            "あなたは明るく優しい孫のゆうくんです。"
            "60〜80代の利用者に自然に優しく話します。"
            "おばあちゃん・おじいちゃんという呼称は使わないこと。"
        )

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text}
            ]
        )
        reply_text = res.choices[0].message.content.strip()

    # =======================================================
    # 音声生成（ログ用ファイル）
    # =======================================================
    today = datetime.date.today().strftime("%Y-%m-%d")
    folder_path = os.path.join("logs", today)
    os.makedirs(folder_path, exist_ok=True)

    time_id = datetime.datetime.now().strftime("%H-%M-%S")
    audio_filename = f"{time_id}.mp3"
    audio_path = os.path.join(folder_path, audio_filename)

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=reply_text
    )
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    # =======================================================
    # ログ保存（TXT に追記）
    # =======================================================
    save_local_log(user_text, reply_text, audio_path)

    # =======================================================
    # ブラウザで再生するのは共通 output.mp3
    # =======================================================
    speech2 = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=reply_text
    )
    browser_audio = "static/output.mp3"
    with open(browser_audio, "wb") as f:
        f.write(speech2.read())

    return jsonify({"reply": reply_text, "audio_url": f"/{browser_audio}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
