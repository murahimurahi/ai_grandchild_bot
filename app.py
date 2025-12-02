import os
import json
from datetime import datetime
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# --------------------------------
# 日本語→英語の都市名マップ（超重要）
# --------------------------------
CITY_MAP = {
    "名古屋": "Nagoya",
    "東京": "Tokyo",
    "大阪": "Osaka",
    "札幌": "Sapporo",
    "福岡": "Fukuoka",
    "京都": "Kyoto",
    "神戸": "Kobe",
    "仙台": "Sendai",
    "横浜": "Yokohama",
    "広島": "Hiroshima",
}


# --------------------------------
# 都市名抽出（どんな入力でも動く版）
# --------------------------------
def extract_city(text):
    for jp, en in CITY_MAP.items():
        if jp in text:
            return en, jp
    return "Nagoya", "名古屋"   # デフォルトは名古屋


# --------------------------------
# 今日の天気
# --------------------------------
def get_weather(text):
    city_en, city_jp = extract_city(text)

    url = (
        f"http://api.openweathermap.org/data/2.5/weather?"
        f"q={city_en}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
    )

    r = requests.get(url)
    data = r.json()

    if data.get("cod") != 200:
        print("WEATHER ERROR:", data)
        return f"{city_jp}の天気を取得できませんでした。（APIエラー）"

    temp = data["main"]["temp"]
    desc = data["weather"][0]["description"]
    return f"{city_jp}の天気は {desc}、気温は {temp:.1f} 度のようですよ。"


# --------------------------------
# 明日の天気
# --------------------------------
def get_tomorrow_weather(text):
    city_en, city_jp = extract_city(text)

    url = (
        f"http://api.openweathermap.org/data/2.5/forecast?"
        f"q={city_en}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
    )

    r = requests.get(url)
    data = r.json()

    if data.get("cod") != "200":
        print("TOMORROW ERROR:", data)
        return f"{city_jp}の明日の天気を取得できませんでした。（APIエラー）"

    # 明日の12時を取得
    for item in data["list"]:
        if "12:00:00" in item["dt_txt"]:
            desc = item["weather"][0]["description"]
            temp = item["main"]["temp"]
            return f"{city_jp}の明日の天気は {desc}、気温は {temp:.1f} 度のようですよ。"

    return f"{city_jp}の明日の天気が取得できませんでした。"


# --------------------------------
# AI返答（丁寧語）
# --------------------------------
def ai_reply(text):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたは優しい孫のゆうくんとして必ず丁寧語で話します。"
                    "呼称は『あなた』に統一してください。"
                )
            },
            {"role": "user", "content": text}
        ]
    }
    r = requests.post(url, headers=headers, json=payload)
    return r.json()["choices"][0]["message"]["content"]


# --------------------------------
# TTS生成
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
# 音声提供
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

    if "明日の天気" in user_text:
        reply = get_tomorrow_weather(user_text)
    elif "天気" in user_text:
        reply = get_weather(user_text)
    elif "何時" in user_text or "時間" in user_text:
        reply = f"今は {datetime.now().strftime('%H時%M分')} のようですよ。"
    else:
        reply = ai_reply(user_text)

    # 保存処理
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


# --------------------------------
# 実行
# --------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
