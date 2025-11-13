import os
from flask import Flask, render_template, request, jsonify, make_response
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

    # --- Chat返答 ---
    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたは明るく元気な孫息子『ゆうくん』です。"
                        "60代のおじいちゃんに笑顔でやさしく話します。"
                        "自然な明るさで話し、語尾に『だよ！』『ね！』などを"
                        "不自然に繰り返さず、自然な会話として使ってください。"
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        reply_text = chat_response.choices[0].message.content.strip()
    except Exception as e:
        print("Chatエラー:", e)
        return jsonify({"reply": "ごめんね、おじいちゃん。", "audio_url": None})

    # --- 音声生成（同期） ---
    os.makedirs("static", exist_ok=True)
    audio_path = f"static/output.mp3"

    try:
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="fable",
            input=reply_text
        ) as response:
            response.stream_to_file(audio_path)
        print("音声生成成功: fable")
    except Exception as e:
        print("音声生成エラー:", e)
        return jsonify({"reply": reply_text, "audio_url": None})

    # --- キャッシュを完全に無効化 ---
    response = make_response(jsonify({
        "reply": reply_text,
        "audio_url": f"/{audio_path}?v={os.urandom(4).hex()}"  # ランダムIDでキャッシュ防止
    }))
    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
