import os, json, random, datetime
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------------------------------
# 記憶データ（ユーザーごとに軽量保存）
# ------------------------------------------
MEMORY_FILE = "data/memory.json"

if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

def load_memory():
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ------------------------------------------
# 会話生成
# ------------------------------------------
def generate_reply(user_id, message):
    memory = load_memory()
    context = memory.get(user_id, "")

    prompt = f"""
あなたは優しい孫として、60〜80代の祖父母と話しています。
口調は温かく、柔らかく、親しみやすい日本語で答えてください。
今日の会話履歴:
{context}
祖父母の発言: {message}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"あなたは優しい孫です。"},
                  {"role":"user","content":prompt}],
        temperature=0.8
    )

    reply = response.choices[0].message.content.strip()

    # 記憶更新
    memory[user_id] = (context + f"\n祖父母: {message}\n孫: {reply}")[-1000:]
    save_memory(memory)
    return reply

# ------------------------------------------
# 音声生成 (OpenAI gpt-4o-mini-tts)
# ------------------------------------------
def generate_voice(text, voice="nova"):
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text
    )
    file_path = "static/reply.mp3"
    with open(file_path, "wb") as f:
        f.write(speech.read())
    return file_path

# ------------------------------------------
# Web動作デモ（Render確認用）
# ------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    data = request.get_json()
    user_id = data.get("user_id", "default")
    message = data.get("message", "")
    voice = data.get("voice", "nova")

    reply = generate_reply(user_id, message)
    audio_path = generate_voice(reply, voice)
    return jsonify({"reply": reply, "audio": audio_path})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
