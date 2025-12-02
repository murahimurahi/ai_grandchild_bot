import os
import json
from datetime import datetime
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# --------------------------------
# 天気取得
# --------------------------------
def get_weather(text):
    try:
        import re
        m = re.search(r"(.*)の天気", text)
        city = m.group(1) if m else "名古屋"

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
        r = requests.get(url)
        data = r.json()

        if data.get("cod") != 200:
            return f"{city}の天気は見つかりませんでした。"

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"{city}の天気は {desc}、気温は {temp:.1f} 度みたいですよ。"

    except:
        return "天気を取得できませんでした。"


# --------------------------------
# AI返答（呼称に“おじいちゃん禁止”）
# --------------------------------
def ai_reply(text):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "あなたは優しい孫のゆうくんとして、丁寧語で話します。ただし、相手を『おじいちゃん』『おばあちゃん』とは呼ばず、『あなた』『お客さん』などに統一します。"
            },
            {"role": "user", "content": text}
        ]
    }
    r = requests.post(url, headers=headers, json=payload)
    return r.json()["choices"][0]["message"]["content"]


# --------------------------------
# TTS音声生成
# --------------------------------
def generate_voice(text, path):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {"model": "gpt-4o-mini-tts", "voice": "verse", "input": text}

    r = requests.post(url, headers=headers, json=payload)

    with open(path, "wb") as f:
        f.write(r.content)


# --------------------------------
# 画面
# --------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")


# --------------------------------
# 音声ファイル配信
# --------------------------------
@app.route("/logs/<day>/<fname>")
def serve_voice(day, fname):
    return send_from_directory(f"logs/{day}", fname)


# --------------------------------
# 会話API
# --------------------------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json
    user_text = data.get("text", "").strip()

    # AI応答
    if "天気" in user_text:
        reply = get_weather(user_text)
    else:
        reply = ai_reply(user_text)

    # ログ保存
    day = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(f"logs/{day}"):
        os.makedirs(f"logs/{day}")

    cid = datetime.now().strftime("%H-%M-%S")
    json_path = f"logs/{day}/{cid}.json"
    mp3_path = f"logs/{day}/{cid}.mp3"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"user": user_text, "bot": reply}, f, ensure_ascii=False)

    generate_voice(reply, mp3_path)

    return jsonify({
        "reply": reply,
        "voice": f"/logs/{day}/{cid}.mp3"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
