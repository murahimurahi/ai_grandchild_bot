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

# =========================
# 天気
# =========================
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


# =========================
# ホーム
# =========================
@app.route("/")
def index():
    return render_template("index.html")


# =========================
# ログ保存処理
# =========================
def save_log(text, reply, audio_path):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    folder = f"logs/{today}"

    os.makedirs(folder, exist_ok=True)

    ts = datetime.datetime.now().strftime("%H-%M-%S")

    # ユーザー発言ログ
    with open(f"{folder}/{ts}_user.txt", "w", encoding="utf-8") as f:
        f.write(text)

    # ボット返答ログ
    with open(f"{folder}/{ts}_bot.txt", "w", encoding="utf-8") as f:
        f.write(reply)

    # 音声（mp3）もコピー保存
    os.system(f"cp {audio_path} {folder}/{ts}_bot.mp3")


# =========================
# 会話API
# =========================
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "").trim()

    # ------------------- 特殊対応 -------------------
    if "天気" in user_text:
        reply_text = get_weather(user_text)

    elif any(k in user_text for k in ["時間", "何時"]):
        now = datetime.datetime.now().strftime("%H時%M分")
        reply_text = f"今は{now}だよ！"

    else:
        prompt = (
            "あなたは明るく優しい孫のゆうくんです。"
            "利用者に自然で丁寧に返答し、必ず敬語で話します。"
            "呼称として「おばあちゃん」「おじいちゃん」は使いません。"
        )

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text}
            ]
        )
        reply_text = res.choices[0].message.content.strip()

    # ------------------- 音声生成 -------------------
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = f"static/output_{ts}.mp3"

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=reply_text
    )
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    # ------------------- ログ保存 -------------------
    save_log(user_text, reply_text, audio_path)

    return jsonify({
        "reply": reply_text,
        "audio_url": "/" + audio_path
    })


# =========================
# ログ一覧画面
# =========================
@app.route("/logs")
def logs():
    if not os.path.exists("logs"):
        os.makedirs("logs", exist_ok=True)

    items = sorted(os.listdir("logs"))

    # .keep は非表示
    items = [i for i in items if i != ".keep"]

    return render_template("logs.html", items=items)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
