import os
import logging
from datetime import datetime
import requests
from flask import Flask, request, jsonify, render_template

# ---------------------------------------------------------------------
# Flask 初期化
# ---------------------------------------------------------------------
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# ---------------------------------------------------------------------
# キャラクター別の音声タイプ
# ---------------------------------------------------------------------
def get_voice(character: str):
    if "孫娘" in character:
        return "verse"
    elif "孫息子" in character:
        return "nova"
    elif "おばあちゃん" in character or "婆" in character:
        return "alloy"
    else:
        return "nova"


# ---------------------------------------------------------------------
# 天気取得（Open-Meteo API：無料・APIキー不要）
# ---------------------------------------------------------------------
def get_weather_text():
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 35.17,    # 名古屋付近
            "longitude": 136.91,
            "current_weather": True,
            "timezone": "Asia/Tokyo"
        }
        r = requests.get(url, params=params)
        data = r.json()
        w = data["current_weather"]
        temp = w.get("temperature")
        wind = w.get("windspeed")
        return f"今の気温は {temp}℃、風速は {wind}m/s みたいですよ。"
    except:
        return "天気情報を取得できませんでした。"


# ---------------------------------------------------------------------
# 音声生成
# ---------------------------------------------------------------------
def generate_voice(text: str, voice_type: str):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini-tts",
        "voice": voice_type,
        "input": text
    }

    audio = requests.post(url, headers=headers, json=payload)
    filename = f"static/voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

    with open(filename, "wb") as f:
        f.write(audio.content)

    return filename


# ---------------------------------------------------------------------
# トップページ（404 回避）
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------
# チャット画面
# ---------------------------------------------------------------------
@app.route("/chat")
def chat_page():
    return render_template("chat.html")


# ---------------------------------------------------------------------
# API：会話
# ---------------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.json
    user_msg = data.get("message", "")
    character = data.get("character", "孫娘（みさちゃん）")

    # --- 日付・時間 ---
    if "今日" in user_msg and "日" in user_msg:
        reply = f"今日は {datetime.now().strftime('%Y年%m月%d日')} ですよ。"
    elif "今" in user_msg and "時間" in user_msg:
        reply = f"今の時刻は {datetime.now().strftime('%H時%M分')} です。"
    # --- 天気 ---
    elif "天気" in user_msg:
        reply = get_weather_text()
    else:
        # 通常会話（OpenAI Chat）
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": f"あなたは {character} として優しく会話してください。"},
                {"role": "user", "content": user_msg}
            ]
        }
        res = requests.post(url, headers=headers, json=payload).json()
        reply = res["choices"][0]["message"]["content"]

    # 音声生成
    voice_type = get_voice(character)
    audio_path = generate_voice(reply, voice_type)

    # 音声ログ（画面下に表示する用）
    log_block = f"【音声ログ】\n生成ボイス: {voice_type}\nファイル: {audio_path}"

    return jsonify({
        "reply": reply,
        "audio": audio_path,
        "log": log_block
    })


# ---------------------------------------------------------------------
# 起動
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
