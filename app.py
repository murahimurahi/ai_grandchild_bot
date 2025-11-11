import os
import json
import random
import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# -----------------------------------------------------
# 感情分析（シンプルスコア式）
# -----------------------------------------------------
def analyze_mood(text: str) -> str:
    positive = ["うれしい", "楽しい", "よかった", "ありがとう", "助かった", "最高", "幸せ"]
    negative = ["悲しい", "疲れた", "しんどい", "嫌だ", "寂しい", "むかつく", "辛い"]
    score = 0
    for w in positive:
        if w in text: score += 1
    for w in negative:
        if w in text: score -= 1

    if score > 0:
        return "😊 穏やかで前向きな気分のようですね。"
    elif score < 0:
        return "🌧 少し疲れているようです。ゆっくり休みましょう。"
    else:
        return "🙂 落ち着いた気分のようですね。"

# -----------------------------------------------------
# 話し方テンプレート
# -----------------------------------------------------
def respond_in_tone(text: str, mood: str) -> str:
    base = [
        "そうなんですね。", "それは大変でしたね。", "うんうん、わかりますよ。",
        "いい日になりそうですね。", "無理せずゆっくりいきましょう。"
    ]
    if "🌧" in mood:
        tone = [
            "無理しなくて大丈夫ですよ。", "休むのも立派なことです。", "お茶でも飲んで一息つきましょう。"
        ]
    elif "😊" in mood:
        tone = [
            "素敵ですね。", "その調子です！", "きっといい一日になりますよ。"
        ]
    else:
        tone = [
            "落ち着いた時間を過ごしてくださいね。", "焦らずマイペースで大丈夫です。"
        ]
    return random.choice(base) + " " + random.choice(tone)

# -----------------------------------------------------
# 会話ログ保存（ローカル）
# -----------------------------------------------------
def save_log(user_text, ai_reply):
    os.makedirs("logs", exist_ok=True)
    today = datetime.date.today().isoformat()
    log_file = f"logs/{today}.json"

    entry = {"time": datetime.datetime.now().strftime("%H:%M"), "user": user_text, "ai": ai_reply}
    data = []
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    data.append(entry)

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# -----------------------------------------------------
# 季節判定
# -----------------------------------------------------
def get_season():
    m = datetime.date.today().month
    if m in [3, 4, 5]:
        return "spring"
    elif m in [6, 7, 8]:
        return "summer"
    elif m in [9, 10, 11]:
        return "autumn"
    else:
        return "winter"

# -----------------------------------------------------
# ルーティング
# -----------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", season=get_season())

@app.route("/talk", methods=["POST"])
def talk():
    user_text = request.json.get("message", "")
    mood = analyze_mood(user_text)
    reply = respond_in_tone(user_text, mood)
    save_log(user_text, reply)
    return jsonify({"mood": mood, "reply": reply})

# -----------------------------------------------------
# 実行
# -----------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
