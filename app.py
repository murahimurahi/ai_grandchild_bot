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

    # --- AIの返答（明るく元気なゆうくん） ---
    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたは明るく元気な孫息子『ゆうくん』として話します。"
                        "60代のおじいちゃんに、笑顔で優しく語りかけてください。"
                        "語尾は軽く跳ねる感じで、テンションは高め、"
                        "ときどき『えへへ』『うん！』『だよ！』などを混ぜて自然に話してください。"
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        reply_text = chat_response.choices[0].message.content.strip()
    except Exception as e:
        print("Chatエラー:", e)
        return jsonify({
            "reply": "ごめんね、おじいちゃん。ちょっと調子が悪いみたい。",
            "audio_url": None
        })

    # --- 元気な声質（fableが明るめ） ---
    voice_type = "fable"

    # --- 音声生成 ---
    os.makedirs("static", exist_ok=True)
    audio_path = "static/output.mp3"

    try:
        speech_response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=voice_type,
            input=reply_text
        )

        with open(audio_path, "wb") as f:
            f.write(speech_response.content)

        print(f"音声生成成功: {voice_type}")

    except Exception as e:
        print("音声生成エラー:", e)
        return jsonify({
            "reply": reply_text,
            "audio_url": None
        })

    return jsonify({
        "reply": reply_text,
        "audio_url": f"/{audio_path}"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
