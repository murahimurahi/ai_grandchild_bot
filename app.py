import os, json, datetime
from flask import Flask, render_template, request, jsonify, make_response
from openai import OpenAI

# ---------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------
app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

LOG_DIR = "data/logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ---------------------------------------------------------------------
# 季節背景の自動判定
# ---------------------------------------------------------------------
@app.route("/")
def index():
    month = datetime.datetime.now().month
    if month in [3, 4, 5]:
        season = "spring"
    elif month in [6, 7, 8]:
        season = "summer"
    elif month in [9, 10, 11]:
        season = "autumn"
    else:
        season = "winter"
    return render_template("index.html", season=season)

# ---------------------------------------------------------------------
# 会話処理
# ---------------------------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")

    # 💬 トーン設定：やさしい孫トーン（相手指定なし）
    try:
        chat_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたは優しく思いやりのある少年『ゆうくん』です。"
                        "誰に対しても明るく穏やかに、相手が安心できるように話してください。"
                        "声のトーンは落ち着いていて、笑顔が伝わるような柔らかさを意識して
