import os
import json
from datetime import datetime
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# -------------------------
# 天気取得
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
        return f"{city}の天気は {desc}、気温は {temp:.1f} 度のようですよ。"

    except:
        return "天気情報を取得できませんでした。"


# -------------------------
# ChatGPT（丁寧語のゆうくん）
# -------------------------
def ai_reply(user_text):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "あなたは優しい孫の“ゆうくん”として、必ず丁寧語で話してください。相手をおじいちゃん・おばあちゃんとは呼ばず『あなた』と呼びます。"
            },
            {"role": "user", "content": user_text}
        ]
    }

    r = requests.post(url, headers=headers, json=payload)
    return r.json()["choices"][0]["message"]["content"]


# -------------------------
# TTS（音声生成）※今回の最重要修正ポイント
# -------------------------
def generate_voice(text, filename):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"     # ← これが抜けていると音声が生成されません
    }
    payload = {
        "model": "gpt-4o-mini-tts",
        "voice": "verse",
        "input": text
    }

    r = requests.post(url, headers=headers, json=payload)

    # エラー確認（Render デバッグ用）
    if r.status_code != 200:
        print("TTS ERROR:", r.text)

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
# 過去ログ一覧
# -------------------------
@app.route("/logs")
def logs():
    if not os.path.exists("logs"):
        os.makedirs("logs")

    days = [d for d in sorted(os.listdir("logs")) if not d.startswith(".")]
    return render_template("logs.html", days=days)


# -------------------------
# 日別ログ表示
# -------------------------
@app.route("/logs/<day>")
def log_day(day):
    folder = f"logs/{day}"
    entries = []

    if not os.path.exists(folder):
        return f"{day} のログがありません。"

    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".json"):
            base = fname.replace(".json", "")
            json_path = f"{folder}/{base}.json"
            mp3_path = f"{folder}/{base}.mp3"

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            entries.append({
                "id": base,
                "user": data["user"],
                "bot": data["bot"],
                "audio": f"/{mp3_path}"
            })

    return render_template("log_view.html", day=day, entries=entries)


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
    elif "何時" in user_text or "時間" in user_text:
        reply = f"今は {datetime.now().strftime('%H時%M分')} のようですよ。"
    elif "今日" in user_text and "日" in user_text:
        reply = f"今日は {datetime.now().strftime('%Y年%m月%d日')} のようですよ。"
    else:
        reply = ai_reply(user_text)

    # 保存
    day = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(f"logs/{day}"):
        os.makedirs(f"logs/{day}")

    conv_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    mp3_path = f"logs/{day}/{conv_id}.mp3"
    json_path = f"logs/{day}/{conv_id}.json"

    # 音声生成
    generate_voice(reply, mp3_path)

    # JSON保存
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
