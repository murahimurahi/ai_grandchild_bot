import os
import json
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

app = Flask(__name__)

# ---------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")

# データフォルダを自動生成
os.makedirs(DATA_DIR, exist_ok=True)

# memory.json が存在しない場合に自動作成
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

# OpenAIクライアント初期化
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------------------
# トップページ
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------------------------------------------------------------
# 話しかけAPI
# ---------------------------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.get_json()
    user_text = data.get("text", "")
    speaker = data.get("speaker", "みさちゃん")

    if not user_text:
        return jsonify({"error": "empty input"}), 400

    # 過去ログ読み込み
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)

    # キャラクター別プロンプト
    if speaker == "みさちゃん":
        prompt = f"あなたは7歳の孫娘『みさちゃん』として、優しく無邪気な口調で話してください。返答は短く自然に。ユーザーの発言：「{user_text}」"
        voice = "verse"
    elif speaker == "ゆうくん":
        prompt = f"あなたは10歳の孫息子『ゆうくん』として、少し元気で素直な男の子のように返答してください。返答は短く自然に。ユーザーの発言：「{user_text}」"
        voice = "nova"
    else:
        prompt = f"あなたは30代の息子『ソウタ』として、落ち着いた低い声で優しく返答してください。返答は短く自然に。ユーザーの発言：「{user_text}」"
        voice = "alloy"

    # OpenAI テキスト生成
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}]
    )
    ai_reply = completion.choices[0].message.content.strip()

    # 会話記録を保存
    memory.append({"user": user_text, "ai": ai_reply})
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory[-30:], f, ensure_ascii=False, indent=2)  # 最新30件保持

    # 音声ファイル生成
    tts = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=ai_reply
    )
    audio_path = os.path.join("static", "reply.mp3")
    with open(audio_path, "wb") as f:
        f.write(tts.read())

    return jsonify({"reply": ai_reply, "audio": f"/static/reply.mp3"})

# ---------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
