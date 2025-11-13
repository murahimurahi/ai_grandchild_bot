import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

    # --- AIの返答を生成 ---
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

    # --- 音声生成（明るく自然な声で） ---
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="nova",  # 現状一番自然で安定している男性少年系トーン
        input=f"明るく元気に、優しく語尾を伸ばして話してください。{reply_text}"
    )

    # --- 音声を保存 ---
    audio_path = "static/output.mp3"
    os.makedirs("static", exist_ok=True)
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
