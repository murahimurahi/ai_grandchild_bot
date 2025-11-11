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

    # --- AIの返答を生成 ---
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"あなたは{character}として、60代の利用者にやさしく話します。言葉遣いは穏やかで、家族に話すように返答してください。"
            },
            {"role": "user", "content": message}
        ]
    )
    reply_text = response.choices[0].message.content

    # --- キャラ別音声タイプ ---
    if character == "みさちゃん（孫娘）":
        voice_type = "verse"
    elif character == "ゆうくん（孫息子）":
        voice_type = "nova"
    else:
        voice_type = "alloy"

    # --- 音声生成（新API対応） ---
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice_type,
        input=reply_text
    )

    audio_path = "static/output.mp3"
    with open(audio_path, "wb") as f:
        f.write(speech.read())  # ← ここが変更点！

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
