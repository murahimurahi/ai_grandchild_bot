import os, json, datetime
from flask import Flask, render_template, request, jsonify, make_response
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

LOG_DIR = "data/logs"
os.makedirs(LOG_DIR, exist_ok=True)

# -------------------------------
# 季節背景の自動判定
# -------------------------------
@app.route("/")
def index():
    month = datetime.datetime.now().month
    if month in [3, 4, 5]:
        season = "spring"
    elif month in [6, 7, 8]:
        season = "summer"
    elif month in [9, 10, 11]:
        season = "autumn"
    else:
        season = "winter"
    return render_template("index.html", season=season)

# -------------------------------
# 会話処理
# -------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")

    # やさしい孫トーン
    system_text = """あなたは優しく思いやりのある少年『ゆうくん』です。
誰に対しても明るく穏やかに、安心できるように話してください。
語尾は自然に、1文のテンポをゆっくりと優しく。
笑顔が伝わるような声のトーンを意識してください。"""

    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": message}
            ],
            timeout=20  # ←ここ追加で安全
        )
        reply_text = chat_response.choices[0].message.content.strip()
    except Exception as e:
        print("Chatエラー:", e)
        return jsonify({"reply": "ごめん、いま少し考えごとしてたみたい。", "audio_url": None})

    # 🎙 音声生成（通常モード）
    os.makedirs("static", exist_ok=True)
    audio_path = "static/output.mp3"
    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="fable",
            input=reply_text
        )
        with open(audio_path, "wb") as f:
            f.write(speech.read())
        print("音声生成成功")
    except Exception as e:
        print("音声生成エラー:", e)
        return jsonify({"reply": reply_text, "audio_url": None})

    # 💾 会話ログ（日ごと保存）
    today = datetime.date.today().strftime("%Y-%m-%d")
    log_path = os.path.join(LOG_DIR, f"{today}.json")
    log_entry = {
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "user": message,
        "yuukun": reply_text
    }
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []
    logs.append(log_entry)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    # レスポンス返却
    response = make_response(jsonify({
        "reply": reply_text,
        "audio_url": f"/{audio_path}?v={os.urandom(4).hex()}"
    }))
    response.headers["Cache-Control"] = "no-store"
    return response


# -------------------------------
# 起動
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
