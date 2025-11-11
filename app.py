import os, json, pathlib
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from openai import OpenAI

# ---------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------
BASE_DIR = pathlib.Path(__file__).resolve().parent
app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MEMORY_FILE = BASE_DIR / "data/memory.json"

# ---------------------------------------------------------------------
# メモリ操作（呼び名の保存・取得）
# ---------------------------------------------------------------------
def get_memory():
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_memory(data):
    os.makedirs(MEMORY_FILE.parent, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------
# ルート
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------------------------------------------------------------
# 会話処理
# ---------------------------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")
    character = data.get("character", "ソウタ（息子）")

    memory = get_memory()
    nickname = memory.get("nickname")

    # 初回：呼び方を聞く
    if not nickname:
        if "おじいちゃん" in message or "おばあちゃん" in message or "さん" in message:
            memory["nickname"] = message.replace("って呼んで", "").strip("。")
            save_memory(memory)
            reply_text = f"わかった！これからは「{memory['nickname']}」って呼ぶね☺️"
        else:
            reply_text = "こんにちは！あなたのこと、なんて呼べばいい？『おじいちゃん』『おばあちゃん』、それとも別の呼び方？"
            return jsonify({"reply": reply_text})

    else:
        # 通常の会話（呼び名付き）
        system_prompt = f"あなたは{character}として、{nickname}にやさしく自然に話しかけます。"
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
            )
            reply_text = response.choices[0].message.content.strip()
        except Exception as e:
            return jsonify({"reply": f"エラーが発生しました: {e}"})

    # -----------------------------------------------------------------
    # キャラ別音声タイプ
    # -----------------------------------------------------------------
    if character == "みさちゃん（孫娘）":
        voice_type = "verse"   # 若い女性
    elif character == "ゆうくん（孫息子）":
        voice_type = "alloy"   # 若い男性
    else:
        voice_type = "nova"    # 落ち着いた男性（息子）

    # -----------------------------------------------------------------
    # 音声生成（確実に出力される最新版構文）
    # -----------------------------------------------------------------
    os.makedirs(BASE_DIR / "static", exist_ok=True)
    audio_path = BASE_DIR / "static" / "output.mp3"

    try:
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice_type,
            input=reply_text,
        ) as response:
            response.stream_to_file(audio_path)
    except Exception as e:
        return jsonify({"reply": reply_text, "audio_url": None, "error": str(e)})

    return jsonify({
        "reply": reply_text,
        "audio_url": f"/static/output.mp3"
    })

# ---------------------------------------------------------------------
# 起動
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
