import os
import json
import logging
from datetime import datetime
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

# -------------------------------------------------------------------
# キャラクター別 TTS
# -------------------------------------------------------------------
def get_voice_type():
    return "verse"   # 今回は固定（孫娘仕様）


# -------------------------------------------------------------------
# OpenAI Chat API（requests版）
# -------------------------------------------------------------------
def chat_completion(user_text: str):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system",
             "content": "あなたは優しい孫のゆうくんです。丁寧語で優しく会話してください。"},
            {"role": "user", "content": user_text}
        ]
    }

    r = requests.post(url, headers=headers, json=payload)
    data = r.json()
    return data["choices"][0]["message"]["content"]


# -------------------------------------------------------------------
# OpenAI TTS（requests版）
# -------------------------------------------------------------------
def generate_tts_mp3(text: str, save_path: str):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini-tts",
        "voice": get_voice_type(),
        "input": text
    }

    r = requests.post(url, headers=headers, json=payload)
    with open(save_path, "wb") as f:
        f.write(r.content)


# -------------------------------------------------------------------
# 天気（OpenWeather）
# -------------------------------------------------------------------
def get_weather(user_text):
    try:
        import re
        m = re.search(r"(.+?)の天気", user_text)
        city = m.group(1) if m else "名古屋"

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
        r = requests.get(url)
        data = r.json()

        if data.get("cod") != 200:
            return f"{city}の天気は見つかりませんでした。"

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]

        return f"{city}の天気は {desc}、気温は {temp:.1f} 度のようです。"
    except:
        return "天気情報の取得に失敗しました。"


# -------------------------------------------------------------------
# トップページ
# -------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# -------------------------------------------------------------------
# チャット画面
# -------------------------------------------------------------------
@app.route("/chat")
def chat_page():
    return render_template("chat.html")


# -------------------------------------------------------------------
# 過去ログ（カレンダー）
# -------------------------------------------------------------------
@app.route("/logs")
def logs():
    if not os.path.exists("logs"):
        os.makedirs("logs")

    days = sorted(os.listdir("logs"))
    days = [d for d in days if not d.startswith(".")]
    return render_template("logs.html", days=days)


# -------------------------------------------------------------------
# 過去ログ（１日分）
# -------------------------------------------------------------------
@app.route("/logs/<day>")
def log_day(day):
    folder = f"logs/{day}"
    if not os.path.exists(folder):
        return f"{day} のログはありません"

    entries = []
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".json"):
            base = fname[:-5]
            json_path = f"{folder}/{base}.json"
            mp3_path = f"{folder}/{base}.mp3"

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            entries.append({
                "id": base,
                "user": data["user"],
                "bot": data["bot"],
                "audio": f"/{mp3_path}" if os.path.exists(mp3_path) else None
            })

    return render_template("log_view.html", day=day, entries=entries)


# -------------------------------------------------------------------
# 会話 API（UI変更なし）
# -------------------------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "").strip()

    # --- 天気 ---
    if "天気" in user_text:
        reply_text = get_weather(user_text)

    # --- 時間 ---
    elif "何時" in user_text or "時間" in user_text:
        reply_text = f"今は {datetime.now().strftime('%H時%M分')} ですよ。"

    # --- 日付 ---
    elif "今日" in user_text and "日" in user_text:
        reply_text = f"今日は {datetime.now().strftime('%Y年%m月%d日')} ですよ。"

    # --- 通常会話 ---
    else:
        reply_text = chat_completion(user_text)

    # -------------------------------------------------------------------
    # 音声生成（mp3）
    # -------------------------------------------------------------------
    day = datetime.now().strftime("%Y-%m-%d")
    folder = f"logs/{day}"
    if not os.path.exists(folder):
        os.makedirs(folder)

    conv_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    mp3_path = f"{folder}/{conv_id}.mp3"
    json_path = f"{folder}/{conv_id}.json"

    # mp3生成
    generate_tts_mp3(reply_text, mp3_path)

    # JSON保存
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "user": user_text,
            "bot": reply_text
        }, f, ensure_ascii=False, indent=2)

    return jsonify({
        "reply": reply_text,
        "audio_url": "/" + mp3_path
    })


# -------------------------------------------------------------------
# Flask 実行
# -------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
