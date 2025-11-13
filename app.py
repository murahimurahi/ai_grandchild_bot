import os
from flask import Flask, render_template, request, jsonify, make_response
from openai import OpenAI

# ---------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------
app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------------------------------------------------------------------
# ルート
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------------------------------------------------------------
# 会話処理（孫が祖父にやさしく話すゆうくん）
# ---------------------------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")

    # --- Chat返答（穏やかな孫トーン） ---
    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたは優しく思いやりのある孫『ゆうくん』です。"
                        "話す相手はおじいちゃんです。"
                        "いつも明るく穏やかに、おじいちゃんを安心させるように話してください。"
                        "声のトーンは落ち着いていて、笑顔が伝わるような柔らかさを意識してください。"
                        "語尾に『だよ』『ね！』『よ！』などを使っても構いませんが、"
                        "無理につけず、自然な流れで1回程度にとどめてください。"
                        "全体的にあたたかく、ゆっくりと優しいテンポで話してください。"
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        reply_text = chat_response.choices[0].message.content.strip()
    except Exception as e:
        print("Chatエラー:", e)
        return jsonify({"reply": "ごめんね。ちょっと調子が悪いみたい。", "audio_url": None})

    # --- 音声生成 ---
    os.makedirs("static", exist_ok=True)
    audio_path = f"static/output.mp3"

    try:
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="fable",  # 優しく明るい少年声
            input=reply_text
        ) as response:
            response.stream_to_file(audio_path)
        print("音声生成成功: fable")
    except Exception as e:
        print("音声生成エラー:", e)
        return jsonify({"reply": reply_text, "audio_url": None})

    # --- キャッシュ防止＋ランダムURL付与 ---
    response = make_response(jsonify({
        "reply": reply_text,
        "audio_url": f"/{audio_path}?v={os.urandom(4).hex()}"
    }))
    response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------------
# 起動設定
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
