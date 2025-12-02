import os
import json
from datetime import datetime, timedelta, timezone
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)

# ===== 日本時間 =====
JST = timezone(timedelta(hours=9))

# ===== APIキー =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# ========================================================
#  今日の天気
# ========================================================
def get_weather(text):
    try:
        import re
        m = re.search(r"(.*)の天気", text)

        if m:
            raw_city = m.group(1)
            city = raw_city.replace("の", "").strip()
        else:
            city = "名古屋"

        url = (
            f"http://api.openweathermap.org/data/2.5/weather?"
            f"q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
        )
        r = requests.get(url)
        data = r.json()

        if data.get("cod") != 200:
            return f"{city}の天気は見つかりませんでした。"

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"{city}の天気は {desc}、気温は {temp:.1f} 度みたいですよ。"

    except Exception as e:
        print("WEATHER ERROR:", e)
        return "天気を取得できませんでした。"


# ========================================================
#  明日の天気
# ========================================================
def get_tomorrow_weather(text):
    try:
        import re
        m = re.search(r"(.*)の?明日の天気", text)

        if m:
            raw_city = m.group(1)
            city = raw_city.replace("の", "").strip()
        else:
            city = "名古屋"

        url = (
            f"http://api.openweathermap.org/data/2.5/forecast?"
            f"q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
        )
        r = requests.get(url)
        data = r.json()

        if data.get("cod") != "200":
            return f"{city}の明日の天気は見つかりませんでした。"

        # 明日の 12:00 の予報がもっとも安定
        target = None
        for item in data["list"]:
            if "12:00:00" in item["dt_txt"]:
                target = item
                break

        if not target:
            return f"{city}の明日の天気を取得できませんでした。"

        desc = target["weather"][0]["description"]
        temp = target["main"]["temp"]

        return f"{city}の明日の天気は {desc}、気温は {temp:.1f} 度みたいですよ。"

    except Exception as e:
        print("TOMORROW ERROR:", e)
        return "明日の天気を取得できませんでした。"


# ========================================================
#  AI返答（丁寧語＋呼称禁止）
# ========================================================
def ai_reply(text):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたは優しい孫のゆうくんとして、必ず丁寧語で話します。"
                    "相手を『おじいちゃん』『おばあちゃん』とは呼ばず、"
                    "『あなた』『お客さん』に統一してください。"
                )
            },
            {"role": "user", "content": text}
        ]
    }
    r = requests.post(url, headers=headers, json=payload)
    return r.json()["choices"][0]["message"]["content"]


# ========================================================
#  TTS（音声生成）
# ========================================================
def generate_voice(text, path):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"model": "gpt-4o-mini-tts", "voice": "verse", "input": text}

    r = requests.post(url, headers=headers, json=payload)

    # デバッグ用
    if r.status_code != 200:
        print("TTS ERROR:", r.text)

    with open(path, "wb") as f:
        f.write(r.content)


# ========================================================
#  画面系
# ========================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")


# ========================================================
#  過去ログ（音声配信）
# ========================================================
@app.route("/logs/<day>/<fname>")
def serve_voice(day, fname):
    return send_from_directory(f"logs/{day}", fname)


# ========================================================
#  会話API
# ========================================================
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json
    user_text = data.get("text", "").strip()

    now = datetime.now(JST)

    # --------- 特殊会話 ---------
    if "明日の天気" in user_text:
        reply = get_tomorrow_weather(user_text)

    elif "天気" in user_text:
        reply = get_weather(user_text)

    elif "何時" in user_text or "時間" in user_text:
        reply = f"今は {now.strftime('%H時%M分')} のようですよ。"

    elif "今日" in user_text and "日" in user_text:
        reply = f"今日は {now.strftime('%Y年%m月%d日')} のようですよ。"

    else:
        reply = ai_reply(user_text)

    # --------- ログ保存 ---------
    day = now.strftime("%Y-%m-%d")
    if not os.path.exists(f"logs/{day}"):
        os.makedirs(f"logs/{day}")

    cid = now.strftime("%H-%M-%S")

    json_path = f"logs/{day}/{cid}.json"
    mp3_path = f"logs/{day}/{cid}.mp3"

    # テキストログ
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"user": user_text, "bot": reply}, f, ensure_ascii=False)

    # 音声生成
    generate_voice(reply, mp3_path)

    return jsonify({
        "reply": reply,
        "voice": f"/logs/{day}/{cid}.mp3"
    })


# ========================================================
#  実行
# ========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
