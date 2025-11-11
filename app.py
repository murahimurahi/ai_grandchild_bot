import os
from flask import Flask, render_template, request, jsonify
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
# 会話処理
# ---------------------------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")
    character = data.get("character", "ソウタ（息子）")

    # --- AIの返答を生成 ---
    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"あなたは{character}として、60代の利用者にやさしく話します。"
                               "言葉遣いは穏やかで、家族に話すように返答してください。"
                },
                {"role": "user", "content": message}
            ]
        )
        reply_text = chat_response.choices[0].message.content.strip()
    except Exception as e:
        print("Chatエラー:", e)
        return jsonify({"reply": "ごめんね、少し調子が悪いみたい。", "audio_url": None})

    # --- キャラ別音声タイプ（全員対応ボイス） ---
    if character == "みさちゃん（孫娘）":
        voice_type = "shimmer"   # 明るい女性声
    elif character == "ゆうくん（孫息子）":
        voice_type = "verse"     # 若い男性声
    else:
        voice_type = "alloy"     # 落ち着いた男性声（息子）

    # --- 音声生成（安定モデル） ---
    os.makedirs("static", exist_ok=True)
    audio_path = "static/output.mp3"

    try:
        speech_response = client.audio.speech.create(
            model="gpt-4o-mini-tts",   # 安定稼働モデル
            voice=voice_type,
            input=reply_text
        )

        with open(audio_path, "wb") as f:
            f.write(speech_response.content)

        print(f"音声生成成功: {voice_type}")

    except Exception as e:
        print("音声生成エラー:", e)
        return jsonify({"reply": reply_text, "audio_url": None})

    # --- 正常レスポンス返却 ---
    return jsonify({
        "reply": reply_text,
        "audio_url": f"/{audio_path}"
    })

# ---------------------------------------------------------------------
# 起動設定（Render / ローカル両対応）
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
