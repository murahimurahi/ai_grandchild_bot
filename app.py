# app.py（要点抜粋。既存のものを全置換OK）

import os, json, requests, datetime, logging
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------------------
# ニュースAPIから総理大臣に関する記事を取得
# ---------------------------------------------------------------------
def get_prime_minister_from_news():
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=jp&apiKey={NEWS_API_KEY}&pageSize=5"
        res = requests.get(url)
        data = res.json()

        articles = data.get("articles", [])
        pm_related = [a["title"] for a in articles if any(k in a["title"] for k in ["首相", "総理", "内閣"])]

        if not pm_related:
            return "最近のニュースに首相関連の記事が見つからなかったみたい。"

        context = "。".join(pm_related)
        # ChatGPTに要約させる
        prompt = f"次の日本のニュースタイトルから、現在の日本の総理大臣が誰かを推定して1文で教えてください。\n\n{context}"

        answer = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "あなたは日本の政治に詳しいアシスタントです。"},
                      {"role": "user", "content": prompt}]
        )
        return answer.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"NewsAPIエラー: {e}")
        return "ニュースを取得できませんでした。"

# ---------------------------------------------------------------------
# Flaskルート
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    user_text = request.form["message"]

    # ① 総理関連の質問ならニュース検索へ
    if "総理" in user_text or "首相" in user_text:
        reply = get_prime_minister_from_news()
    else:
        # 通常のChatGPT応答
        reply = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは明るく元気な孫のゆうくんです。自然に短く話してね。"},
                {"role": "user", "content": user_text}
            ]
        ).choices[0].message.content.strip()

    return jsonify({"reply": reply})

# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
