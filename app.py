import os, json, datetime, logging, requests
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GOOGLE_CREDENTIALS_PATH = "/etc/secrets/ohanashi-yokocho-service.json"

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------------------
# Google Drive 接続設定（ログ保存）
# ---------------------------------------------------------------------
def get_drive_service():
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        logging.error(f"Drive接続エラー: {e}")
        return None

def save_conversation(user_text, reply_text, audio_path=None):
    try:
        service = get_drive_service()
        if not service:
            logging.warning("Google Driveサービスが未接続。スキップします。")
            return

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        filename = f"conversation_{today}.txt"
        tmp_path = f"/tmp/{filename}"

        with open(tmp_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] あなた: {user_text}\n")
            f.write(f"ゆうくん: {reply_text}\n\n")

        file_metadata = {"name": filename, "mimeType": "text/plain"}
        media = MediaFileUpload(tmp_path, mimetype="text/plain")
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    except Exception as e:
        logging.error(f"ログ保存エラー: {e}")

# ---------------------------------------------------------------------
# 天気取得（OpenWeather）
# ---------------------------------------------------------------------
def get_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Tokyo&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
        data = requests.get(url).json()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"今の東京の天気は{desc}、気温は{temp:.1f}度だよ！"
    except Exception as e:
        logging.error(f"天気取得エラー: {e}")
        return "天気情報を取得できなかったよ。"

# ---------------------------------------------------------------------
# NewsAPIで時事（総理など）取得
# ---------------------------------------------------------------------
def get_prime_minister_from_news():
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=jp&apiKey={NEWS_API_KEY}&pageSize=8"
        res = requests.get(url)
        data = res.json()

        articles = data.get("articles", [])
        pm_related = [a["title"] for a in articles if any(k in a["title"] for k in ["首相", "総理", "内閣"])]

        if not pm_related:
            return "最近のニュースに総理の記事が見当たらないけど、今は高市早苗さんが総理だよ。"

        context = "。".join(pm_related)
        prompt = f"次の日本のニュースタイトルから、現在の日本の総理大臣を1文で教えてください。\n\n{context}"

        answer = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは時事に詳しい日本人の孫です。"},
                {"role": "user", "content": prompt}
            ]
        )
        return answer.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"NewsAPIエラー: {e}")
        return "ニュースの取得に失敗しちゃった。"

# ---------------------------------------------------------------------
# Flaskルート
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    user_text = request.form["message"].strip()

    # 特定ワードに応じて処理分岐
    if "天気" in user_text:
        reply_text = get_weather()
    elif "総理" in user_text or "首相" in user_text:
        reply_text = get_prime_minister_from_news()
    elif "何時" in user_text or "時間" in user_text:
        now = datetime.datetime.now().strftime("%H時%M分")
        reply_text = f"今は{now}だよ！"
    elif "何日" in user_text or "曜日" in user_text:
        now = datetime.datetime.now()
        reply_text = f"今日は{now.strftime('%Y年%m月%d日')}、{['月','火','水','木','金','土','日'][now.weekday()]}曜日だよ。"
    else:
        reply_text = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは明るく元気で思いやりのある孫のゆうくんです。おじいちゃん・おばあちゃんという言葉は使わず、自然体で優しく話します。"},
                {"role": "user", "content": user_text}
            ]
        ).choices[0].message.content.strip()

    # ログ保存
    save_conversation(user_text, reply_text)

    return jsonify({"reply": reply_text})

@app.route("/logs")
def logs_page():
    return render_template("logs.html")

# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
