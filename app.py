import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")
    character = data.get("character", "ソウタ（息子）")

    # --- テキスト返答生成 ---
    chat = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"あなたは{character}として、60代の利用者にやさしく話します。言葉遣いは穏やかで、家族に話すように返答してください。"
            },
            {"role": "user", "content": message}
        ]
    )
    reply_text = chat.choices[0].message.content.strip()

    # --- 声モデル設定（sol） ---
    if character == "みさちゃん（孫娘）":
        voice_type = "sol"
    elif character == "ゆうくん（孫息子）":
        voice_type = "verse"
    else:
        voice_type = "nova"

    # --- 音声生成（安定構文） ---
    os.makedirs("static", exist_ok=True)
    audio_path = "static/output.mp3"

    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",  # ← 安定モデル
            voice=voice_type,
            input=reply_text
        )

        # openai>=1.13.0では .content に音声バイナリが入る
        with open(audio_path, "wb") as f:
            f.write(speech.content)

    except Exception as e:
        print("音声生成エラー:", e)
        return jsonify({"reply": reply_text, "audio_url": None})

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
