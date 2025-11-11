import os
import threading
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_speech_async(text, path, voice="fable"):
    """音声生成を別スレッドで実行"""
    try:
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text
        ) as response:
            response.stream_to_file(path)
        print(f"音声生成完了: {path}")
    except Exception as e:
        print("音声生成エラー:", e)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")
    audio_path = "static/output.mp3"

    # --- Chat返答（即時） ---
    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたは明るく元気な孫息子『ゆうくん』です。"
                        "60代のおじいちゃんに笑顔で話し、"
                        "テンポよく明るく返してください。"
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        reply_text = chat_response.choices[0].message.content.strip()
        print("返答生成成功")
    except Exception as e:
        print("Chatエラー:", e)
        return jsonify({"reply": "ごめんね、おじいちゃん。", "audio_url": None})

    # --- 音声生成を並列実行 ---
    threading.Thread(target=generate_speech_async, args=(reply_text, audio_path, "fable")).start()

    # --- 返答は即返す（体感テンポUP） ---
    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
