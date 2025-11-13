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

    # --- Chat返答（相手指定なしVer.） ---
    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたは明るく元気な少年『ゆうくん』です。"
                        "誰に対してもやさしく自然に話しかけ、"
                        "フレンドリーで親しみやすい口調で返答してください。"
                        "語尾に『だよ！』『ね！』などを使ってもかまいませんが、"
                        "不自然にならないよう控えめに使い、"
                        "全体的にテンポよく自然な会話にしてください。"
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        reply_text = chat_response.choices[0].message.content.strip()
    except Exception as e:
        print("Chatエラー:", e)
        return jsonify({"reply": "ごめん、ちょっと調子が悪いみたい。", "audio_url": None})

    # --- 音声生成 ---
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

    # --- キャッシュ無効化＆ランダムURLで再読み込み防止 ---
    response = make_response(jsonify({
        "reply": reply_text,
        "audio_url": f"/{audio_path}?v={os.urandom(4).hex()}"
    }))
    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
