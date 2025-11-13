import os
import json
import datetime
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

# ------------------------
# Flask設定
# ------------------------
app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ------------------------
# ログ・音声フォルダ（Render対応）
# ------------------------
LOG_DIR = "/tmp/logs"
AUDIO_DIR = "static/audio"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)


# ------------------------
# 会話を保存（日付ごと）
# ------------------------
def save_conversation(user_msg, ai_reply, audio_file):
    today = datetime.date.today().isoformat()
    file_path = os.path.join(LOG_DIR, f"{today}.json")

    # 既存データを読み込み
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    # 新しい会話を追加
    data.append({
        "user": user_msg,
        "yuukun": ai_reply,
        "audio_file": audio_file
    })

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ------------------------
# トップページ
# ------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ------------------------
# 会話（ゆうくん）
# ------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")

    # --- AI応答生成 ---
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは10歳前後の明るく優しい孫『ゆうくん』です。"
                    "聞き手はおじいちゃんやおばあちゃんのような年上の家族ですが、"
                    "直接そう呼ばずに、自然に穏やかに話してください。"
                    "返答は短く自然で、絵文字や記号を使わず、温かみのある言葉で。"
                    "冗談や括弧の補足説明は使わず、まっすぐ会話します。"
                )
            },
            {"role": "user", "content": message}
        ]
    )
    reply_text = response.choices[0].message.content.strip()

    # --- 音声生成 ---
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="fable",  # 明るい少年声
        input=reply_text
    )

    # --- 音声ファイル保存 ---
    audio_filename = f"{datetime.datetime.now().strftime('%H%M%S')}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    # --- 会話を保存 ---
    save_conversation(message, reply_text, audio_filename)

    # --- 応答返却 ---
    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})


# ------------------------
# 会話ログページ
# ------------------------
@app.route("/logs")
def logs():
    logs_data = []
    for file in sorted(os.listdir(LOG_DIR)):
        if file.endswith(".json"):
            date = file.replace(".json", "")
            with open(os.path.join(LOG_DIR, file), "r", encoding="utf-8") as f:
                entries = json.load(f)
            logs_data.append({"date": date, "entries": entries})
    logs_data.sort(key=lambda x: x["date"], reverse=True)
    return render_template("logs.html", logs=logs_data)


# ------------------------
# メイン
# ------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
