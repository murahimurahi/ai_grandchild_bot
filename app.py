import os
import pathlib
import openai
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# ---------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------
BASE_DIR = pathlib.Path(__file__).resolve().parent
app = Flask(__name__)
CORS(app)

openai.api_key = os.environ.get("OPENAI_API_KEY")

# ---------------------------------------------------------------------
# キャラクターごとの音声タイプ設定
# ---------------------------------------------------------------------
def get_voice_type(character: str):
    if character == "みさちゃん（孫娘）":
        return "verse"  # 明るい女性
    elif character == "ゆうくん（孫息子）":
        return "alloy"  # 少年
    else:
        return "nova"   # 落ち着いた男性（息子）

# ---------------------------------------------------------------------
# トーク処理
# ---------------------------------------------------------------------
@app.route("/speak", methods=["POST"])
def speak():
    data = request.get_json()
    text = data.get("text", "")
    character = data.get("character", "みさちゃん（孫娘）")
    voice_type = get_voice_type(character)

    prompt = f"{character}として、おじいちゃんにやさしく返事してください。「{text}」に返すように。"
    speech_file_path = BASE_DIR / "static" / "audio" / "output.mp3"
    speech_file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # OpenAI音声生成
        response = openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=voice_type,
            input=f"こんにちは、おじいちゃん！{text}についてお話しできてうれしいです。"
        )
        with open(speech_file_path, "wb") as f:
            f.write(response.read())

        message = "こんにちは、おじいちゃん！お元気ですか？今日は何か楽しいことがありましたか？"
        return jsonify({
            "message": message,
            "audio_url": "/static/audio/output.mp3"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------
# ルート
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
