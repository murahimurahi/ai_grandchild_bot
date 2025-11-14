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
# 今日の天気
# -----------------------------
def get_weather_today(user_text="東京"):
    try:
        import re
        city_match = re.search(r"(.+?)の天気", user_text)
        city = city_match.group(1).replace("の", "") if city_match else "東京"

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
        return f"今日の{city}の天気は{desc}、気温は{temp:.1f}度だよ。"

    except:
        return "天気情報を取得できなかったよ。"


# -----------------------------
# 明日の天気（OpenWeather forecast）
# -----------------------------
def get_weather_tomorrow(user_text="東京"):
    try:
        import re
        city_match = re.search(r"(.+?)の明日の天気", user_text)
        if not city_match:
            city_match = re.search(r"(.+?)の天気", user_text)
        city = city_match.group(1).replace("の", "") if city_match else "東京"

        url = (
            f"https://api.openweathermap.org/data/2.5/forecast?"
            f"q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
        )
        res = requests.get(url, timeout=6)
        data = res.json()

        if data.get("cod") != "200":
            return f"明日の{city}の天気は見つからなかったよ。"

        # tomorrow 12:00 の天気を取る（最も安定している）
        target = None
        for item in data["list"]:
            if "12:00:00" in item["dt_txt"]:
                target = item
                break

        if not target:
            return f"明日の{city}の天気データが見つからなかったよ。"

        temp = target["main"]["temp"]
        desc = target["weather"][0]["description"]
        return f"明日の{city}の天気は{desc}、最高気温は{temp:.1f}度くらいだよ。"

    except:
        return "明日の天気情報を取得できなかったよ。"


# -----------------------------
# ログ保存
# -----------------------------
def save_log(user_text, bot_text, audio_file, timestamp):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    folder = f"logs/{today}"

    if not os.path.exists(folder):
        os.makedirs(folder)

    with open(f"{folder}/log.txt", "a", encoding="utf-8") as f:
        f.write(f"[TIME]{timestamp}\n")
        f.write(f"【あなた】{user_text}\n")
        f.write(f"【ゆうくん】{bot_text}\n")
        f.write("[END]\n\n")

    if audio_file:
        with open(f"{folder}/voice_{timestamp}.mp3", "wb") as f:
            f.write(audio_file)


# -----------------------------
# ログ一覧
# -----------------------------
@app.route("/logs")
def logs():
    if not os.path.exists("logs"):
        os.makedirs("logs")

    days = sorted(os.listdir("logs"))
    days = [d for d in days if not d.startswith(".")]
    return render_template("logs.html", days=days)


# -----------------------------
# ログ表示（会話ごと）
# -----------------------------
@app.route("/logs/<day>")
def show_log(day):
    folder = f"logs/{day}"
    textfile = f"{folder}/log.txt"

    conversations = []

    if os.path.exists(textfile):
        with open(textfile, "r", encoding="utf-8") as f:
            blocks = f.read().split("[END]")

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.split("\n")
            ts = lines[0].replace("[TIME]", "")
            text = "\n".join(lines[1:])

            voice_file = f"{folder}/voice_{ts}.mp3"
            voice_url = f"/voice/{day}/{ts}" if os.path.exists(voice_file) else None

            conversations.append({
                "timestamp": ts,
                "text": text,
                "voice": voice_url
            })

    return render_template(
        "log_view.html",
        day=day,
        conversations=conversations
    )


# -----------------------------
# 音声取得
# -----------------------------
@app.route("/voice/<day>/<ts>")
def get_voice(day, ts):
    filepath = f"logs/{day}/voice_{ts}.mp3"
    if not os.path.exists(filepath):
        return "音声が見つからないよ。", 404
    return send_file(filepath, mimetype="audio/mpeg")


# -----------------------------
# 会話
# -----------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "").strip()

    # ✅ 明日の天気
    if "明日" in user_text and "天気" in user_text:
        reply_text = get_weather_tomorrow(user_text)

    # 今日の天気
    elif "天気" in user_text:
        reply_text = get_weather_today(user_text)

    # 日付・曜日
    elif any(k in user_text for k in ["何日", "今日", "日付", "曜日"]):
        now = datetime.datetime.now()
        youbi = ["月", "火", "水", "木", "金", "土", "日"][now.weekday()]
        reply_text = f"今日は {now.month}月{now.day}日、{youbi}曜日だよ。"

    # 時間
    elif any(k in user_text for k in ["何時", "時間", "いま何時"]):
        now = datetime.datetime.now().strftime("%H時%M分")
        reply_text = f"今は{now}だよ。"

    # 通常会話
    else:
        prompt = (
            "あなたは優しい孫のゆうくんです。利用者と自然に会話します。"
            "呼称として『おばあちゃん』『おじいちゃん』は使わず、"
            "丁寧で優しい言葉で話してください。"
        )

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text}
            ]
        )
        reply_text = res.choices[0].message.content.strip()

    # 音声合成
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = f"static/output_{ts}.mp3"

    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=reply_text
    )
    audio_binary = speech.read()

    with open(audio_path, "wb") as f:
        f.write(audio_binary)

    save_log(user_text, reply_text, audio_binary, ts)

    return jsonify({
        "reply": reply_text,
        "audio_url": "/" + audio_path
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
