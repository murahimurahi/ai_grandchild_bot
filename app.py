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

    # --- AIが返す会話文 ---
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"あなたは{character}として60代の利用者にやさしく会話します。言葉遣いは親しみやすく、ゆっくり落ち着いたトーンで。"
            },
            {"role": "user", "content": message}
        ]
    )
    reply_text = response.choices[0].message.content

    # --- キャラクターごとに声を切り替え ---
    if character == "みさちゃん（孫娘）":
        voice_type = "verse"      # 柔らかく明るい女の子
    elif character == "ゆうくん（孫息子）":
        voice_type = "nova"       # 少年っぽい声
    else:
        voice_type = "alloy"      # 低めのイケボ（息子）

    # --- 音声生成（TTS） ---
    tts = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice_type,
        input=reply_text
    )

    # --- 音声ファイル保存 ---
    audio_path = "static/output.mp3"
    with open(audio_path, "wb") as f:
        f.write(tts.audio)

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
