import os, threading
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/")
def index():
    return render_template("index.html")

def generate_speech_async(text):
    """音声生成を別スレッドで実行"""
    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="nova",
            input=text
        )
        os.makedirs("static", exist_ok=True)
        audio_path = "static/output.mp3"
        with open(audio_path, "wb") as f:
            f.write(speech.read())
    except Exception as e:
        print("音声生成エラー:", e)

@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")

    # --- AI応答生成 ---
    chat_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは明るく元気な孫息子『ゆうくん』です。"
                    "60代のおじいちゃんに笑顔で優しく話します。"
                    "自然で明るい話し方にしてください。"
                    "語尾に『だよ』『ね！』『よ！』などを付けてもかまいませんが、"
                    "わざとらしく何度も繰り返さず、自然な会話として使ってください。"
                    "前回と同じ話題を繰り返さず、毎回少し違う表現で答えてください。"
                    "全体的にテンポよく、聞いていて元気をもらえるようなトーンで話してください。"
                )
            },
            {"role": "user", "content": message}
        ]
    )

    reply_text = chat_response.choices[0].message.content.strip()

    # --- 音声は別スレッドで生成 ---
    threading.Thread(target=generate_speech_async, args=(reply_text,)).start()

    return jsonify({"reply": reply_text, "audio_url": "/static/output.mp3"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
