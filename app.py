import os, json
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MEMORY_FILE = "data/memory.json"

# ------------------------
# メモリ操作（呼び名の保存・取得）
# ------------------------
def get_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_memory(data):
    os.makedirs("data", exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ------------------------
# ルート
# ------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ------------------------
# 会話処理
# ------------------------
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
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )
        reply_text = response.choices[0].message.content

    # キャラ別音声タイプ
    if character == "みさちゃん（孫娘）":
        voice_type = "verse"
    elif character == "ゆうくん（孫息子）":
        voice_type = "alloy"
    else:
        voice_type = "nova"

    # 音声生成
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice_type,
        input=reply_text
    )

    os.makedirs("static", exist_ok=True)
    audio_path = "static/output.mp3"
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
