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

# ----------------------------------------------------
# 天気取得
# ----------------------------------------------------
def get_weather(user_text="東京"):
    try:
        import re
        m = re.search(r"(.+?)の天気", user_text)
        city = m.group(1) if m else "東京"

        url = (
            "http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
        )
        res = requests.get(url, timeout=6)
        data = res.json()

        if data.get("cod") != 200:
            return f"{city}の天気は見つからなかったよ。"

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"今の{city}の天気は{desc}、気温は{temp:.1f}度だよ！"

    except Exception:
        return "天気情報を取得できなかったよ。"


# ----------------------------------------------------
# トップページ
# ----------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ----------------------------------------------------
# 会話API（TTSあり）
# ----------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "").strip()

    # ---------------- 特殊コマンド ----------------
    # 天気
    if "天気" in user_text:
        reply = get_weather(user_text)

    # 時間
    elif any(k in user_text for k in ["時間", "何時"]):
        now = datetime.datetime.now().strftime("%H時%M分")
        reply = f"今は{now}だよ！"

    # 通常会話
    else:
        prompt = (
            "あなたは優しく明るい孫のゆうくんです。"
            "利用者に丁寧に返事をして、内容に合わせた自然な返答をしてください。"
            "60〜80代向けに、ゆっくり優しい言葉を使ってください。"
            "『おばあちゃん』『おじいちゃん』は使わない。"
            "同じ表現は繰り返さず、その都度ちがう自然な返答をしてください。"
        )
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text}
            ]
        )
        reply = res.choices[0].message.content.strip()

    # ----------------------------------------------------
    # TTS（毎回ユニークパス生成）
    # ----------------------------------------------------
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = f"static/output_{ts}.mp3"

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=reply
    )
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    # ----------------------------------------------------
    # 会話ログ保存（KEEPフォルダは除外される）
    # ----------------------------------------------------
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    save_dir = os.path.join("logs", today)
    os.makedirs(save_dir, exist_ok=True)

    log_file = os.path.join(save_dir, "log.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"【あなた】{user_text}\n")
        f.write(f"【ゆうくん】{reply}\n\n")

    return jsonify({
        "reply": reply,
        "audio_url": "/" + audio_path
    })


# ----------------------------------------------------
# ログ一覧  ※KEEPを除外
# ----------------------------------------------------
@app.route("/logs")
def logs():
    base_path = "logs"
    if not os.path.exists(base_path):
        return render_template("logs.html", folders=[])

    # 🔥 KEEPフォルダ（_keep）はここで除外
    folders = sorted([
        f for f in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, f)) and not f.startswith("_")
    ])

    return render_template("logs.html", folders=folders)


# ----------------------------------------------------
# 日別ログ表示
# ----------------------------------------------------
@app.route("/logs/<day>")
def show_log(day):
    path = os.path.join("logs", day, "log.txt")
    if not os.path.exists(path):
        return f"ログがありません: {day}"

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return f"<pre style='padding:20px; font-size:18px;'>{content}</pre>"


# ----------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
