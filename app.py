import os
import json
from datetime import datetime
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# -------------------------
# 天気
# -------------------------
def get_weather(user_text):
    try:
        import re
        m = re.search(r"(.*)の天気", user_text)
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
        return "天気情報を取得できませんでした。"


# -------------------------
# OpenAI Chat API
# -------------------------
def ai_reply(user_text):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたは優しい孫のゆうくんとして丁寧語で話します。"
                    "相手の呼び方は『あなた』で統一します。"
                    "『おじいちゃん』『おばあちゃん』などの家族呼称は絶対に使いません。"
                    "相手から要望があれば、その呼び方に従います。"
                )
            },
            {"role": "user", "content": user_text}
        ]
    }

    r = requests.post(url, headers=headers, json=payload)
    return r.json()["choices"][0]["message"]["content"]


# -------------------------
# TTS（音声生成）
# -------------------------
def generate_voice(text, filename):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini-tts",
        "voice": "verse",
        "input": text
    }

    r = requests.post(url, headers=headers, json=payload)
    with open(filename, "wb") as f:
        f.write(r.content)


# -------------------------
# UI
# -------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat")
def chat_page():
    return render_template("chat.html")


# -------------------------
# 会話API
# -------------------------
@app.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.json
    user_text = data.get("message", "").strip()

    # 特殊処理
    if "天気" in user_text:
        reply = get_weather(user_text)
    else:
        reply = ai_reply(user_text)

    # 保存処理
    day = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(f"logs/{day}"):
        os.makedirs(f"logs/{day}")

    conv_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    mp3_path = f"logs/{day}/{conv_id}.mp3"
    json_path = f"logs/{day}/{conv_id}.json"

    generate_voice(reply, mp3_path)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"user": user_text, "bot": reply}, f, ensure_ascii=False)

    return jsonify({
        "reply": reply,
        "voice_url": "/" + mp3_path
    })


# -------------------------
# メイン
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
