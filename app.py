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

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
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
# ログ保存
# -----------------------------
def save_log(user_text, bot_text, audio_file):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    folder = f"logs/{today}"

    if not os.path.exists(folder):
        os.makedirs(folder)

    # テキストログ
    with open(f"{folder}/log.txt", "a", encoding="utf-8") as f:
        f.write(f"【あなた】{user_text}\n")
        f.write(f"【ゆうくん】{bot_text}\n\n")

    # 音声保存
    if audio_file:
        with open(f"{folder}/voice.mp3", "wb") as f:
            f.write(audio_file)


# -----------------------------
# ルーティング
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


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
    voicefile = f"{folder}/voice.mp3"

    text_content = ""
    if os.path.exists(textfile):
        with open(textfile, "r", encoding="utf-8") as f:
            text_content = f.read()

    has_voice = os.path.exists(voicefile)

    return render_template(
        "log_view.html",
        day=day,
        text_content=text_content,
        has_voice=has_voice
    )


# -----------------------------
# 音声ファイルを Flask で返す（重要！）
# -----------------------------
@app.route("/voice/<day>")
def get_voice(day):
    filepath = f"logs/{day}/voice.mp3"
    if not os.path.exists(filepath):
        return "音声が見つからないよ。", 404
    return send_file(filepath, mimetype="audio/mpeg")


# -----------------------------
# 会話API
# -----------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "").trim() if data.get("message") else ""

    # ------------------- 特殊対応 -------------------
    if "天気" in user_text:
        reply_text = get_weather(user_text)

    elif any(k in user_text for k in ["時間", "何時"]):
        now = datetime.datetime.now().strftime("%H時%M分")
        reply_text = f"今は{now}だよ！"

    else:
        prompt = (
            "あなたは優しい孫のゆうくんです。利用者と自然に会話します。"
            "呼称として『おばあちゃん』『おじいちゃん』は使わず、"
            "丁寧で優しい言
