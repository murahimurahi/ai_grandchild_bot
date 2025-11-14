import os
import datetime
import logging
import requests
from flask import Flask, render_template, request, jsonify, send_file
from openai import OpenAI

app = Flask(__name__, static_folder="static", template_folder="templates")
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


# -----------------------------
# 天気
# -----------------------------
def get_weather(user_text="東京"):
    try:
        import re
        city_match = re.search(r"(.+?)の天気", user_text)
        city = city_match.group(1) if city_match else "東京"

        url = (
            f"http://api.openweathermap.org/data/2.5/weather?"
            f"q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
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


# -----------------------------
# ログ保存（会話単位で音声も保存）
# -----------------------------
def save_log(user_text, bot_text, audio_file, timestamp):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    folder = f"logs/{today}"

    if not os.path.exists(folder):
        os.makedirs(folder)

    # テキストログにブロック単位で記録
    with open(f"{folder}/log.txt", "a", encoding="utf-8") as f:
        f.write(f"[TIME]{timestamp}\n")
        f.write(f"【あなた】{user_text}\n")
        f.write(f"【ゆうくん】{bot_text}\n")
        f.write("[END]\n\n")

    # 音声ログ（timestamp名で保存）
    if audio_file:
        voice_path = f"{folder}/voice_{timestamp}.mp3"
        with open(voice_path, "wb") as f:
            f.write(audio_file)


# -----------------------------
# ログ閲覧
# -----------------------------
@app.route("/logs")
def logs():
    if not os.path.exists("logs"):
        os.makedirs("logs")

    days = sorted(os.listdir("logs"))
    days = [d for d in days if not d.startswith(".")]
    return render_template("logs.html", days=days)


@app.route("/logs/<day>")
def show_log(day):
    folder = f"logs/{day}"
    textfile = f"{folder}/log.txt"

    conversations = []

    if os.path.exists(textfile):
        with open(textfile, "r", encoding="utf-8") as f:
            lines = f.read().split("[END]")

        for block in lines:
            block = block.strip()
            if not block:
                continue

            rows = block.split("\n")
            ts = rows[0].replace("[TIME]", "").strip()
            text = "\n".join(rows[1:])

            # 音声ファイルチェック
            voice_path = None
            voice_file = f"{folder}/voice_{ts}.mp3"
            if os.path.exists(voice_file):
                voice_path = f"/voice/{day}/{ts}"

            conversations.append({
                "timestamp": ts,
                "text": text,
                "voice": voice_path
            })

    return render_template(
        "log_view.html",
        day=day,
        conversations=conversations
    )


# -----------------------------
# 音声ファイル取得
# -----------------------------
@app.route("/voice/<day>/<ts>")
def get_voice(day, ts):
    filepath = f"logs/{day}/voice_{ts}.mp3"
    if not os.path.exists(filepath):
        return "音声が見つからないよ。", 404
    return send_file(filepath, mimetype="audio/mpeg")


# -----------------------------
# 会話API
# -----------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "").strip()

    # ------------------- 日付・曜日 -------------------
    if an
