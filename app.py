import os
import pathlib
import openai
from flask import Flask, request, jsonify, send_from_directory, render_template
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
        return "verse"  # 若い女性
    elif character == "ゆうくん（孫息子）":
        return "alloy"  # 少年寄り
    else:
        return "nova"   # 落ち着いた父親風

# ---------------------------------------------------------------------
# 音声生成API
# ---------------------------------------------------------------------
@app.route("/speak", methods=["POST"])
def speak():
    data = request.get_json()
    text = data.get("text", "")
    character = data.get("character", "みさちゃん（孫娘）")
    voice_type = get_voice_type(character)

    # 音声ファイル保存パス
    speech_file_path = BASE_DIR / "static" / "audio" / "output.mp3"
    speech_file_path.parent.mkdir(parents=True, exist_ok=True)

    # OpenAI TTS 音声生成
    with openai.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice=voice_type,
        input=text
    ) as response:
        response.stream_to_file(speech_file_path)

    return jsonify({"audio_url": "/static/audio/output.mp3"})

# ---------------------------------------------------------------------
# 静的ファイル
# ---------------------------------------------------------------------
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_DIR / "static", filename)

# ---------------------------------------------------------------------
# HTMLルート
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
