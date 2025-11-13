import os
import json
import datetime
import threading
from datetime import timedelta, timezone
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------
app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Google Drive 認証設定
SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=credentials)
ROOT_FOLDER_NAME = "おはなし横丁ログ"

# APIキー
WEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")  # 任意（まだ無ければNone）

# ---------------------------------------------------------------------
# Google Drive関連
# ---------------------------------------------------------------------
def get_or_create_folder(name, parent_id=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [parent_id]
    folder = drive_service.files().create(body=metadata, fields="id").execute()
    return folder["id"]

ROOT_ID = get_or_create_folder(ROOT_FOLDER_NAME)

def get_today_folder():
    today = datetime.date.today().strftime("%Y-%m-%d")
    return get_or_create_folder(today, ROOT_ID)

def cleanup_old_folders():
    results = drive_service.files().list(
        q=f"'{ROOT_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)"
    ).execute()
    folders = results.get("files", [])
    today = datetime.date.today()
    for f in folders:
        try:
            folder_date = datetime.datetime.strptime(f["name"], "%Y-%m-%d").date()
            if (today - folder_date).days > 30:
                drive_service.files().delete(fileId=f["id"]).execute()
                print(f"🧹 Deleted old folder: {f['name']}")
        except ValueError:
            continue

def save_to_drive_async(message, reply_text):
    try:
        folder_id = get_today_folder()
        filename = f"{datetime.datetime.now().strftime('%H%M%S')}.json"
        local_path = os.path.join("/tmp", filename)
        log_data = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_message": message,
            "reply": reply_text,
        }
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        media = MediaFileUpload(local_path, mimetype="application/json")
        drive_service.files().create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media,
            fields="id",
        ).execute()
        cleanup_old_folders()
    except Exception as e:
        print("⚠️ Drive保存エラー:", e)

# ---------------------------------------------------------------------
# 情報取得関数
# ---------------------------------------------------------------------
def get_weather(city="Nagoya"):
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city},jp&appid={WEATHER_API_KEY}&lang=ja&units=metric"
        )
        res = requests.get(url)
        data = res.json()
        if "weather" in data:
            desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            return f"{city}の今の天気は「{desc}」、気温は{temp:.1f}度くらいだよ。"
        else:
            return "天気情報をうまく取得できなかったみたい。"
    except Exception:
        return "天気の取得でちょっとトラブルがあったみたい。"

def get_latest_news():
    if not NEWS_API_KEY:
        return None
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=jp&apiKey={NEWS_API_KEY}"
        res = requests.get(url)
        data = res.json()
        if "articles" in data and data["articles"]:
            title = data["articles"][0]["title"]
            return f"最近のニュースだと「{title}」って話題があるよ。"
        return "今のところ大きなニュースは見つからなかったよ。"
    except Exception:
        return None

# ---------------------------------------------------------------------
# Flaskルート
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")

    # 日本時間を取得
    JST = timezone(timedelta(hours=9))
    now = datetime.datetime.now(JST)
    current_time = now.strftime("%Y年%m月%d日 %H時%M分")
    weekday_jp = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    weekday = weekday_jp[now.weekday()]

    # 特定キーワード判定（天気・ニュース）
    weather_info, news_info = None, None
    if "天気" in message:
        weather_info = get_weather("Nagoya")
    if "ニュース" in message or "総理" in message:
        news_info = get_latest_news()

    # ChatGPT 応答生成
    system_prompt = (
        f"あなたは小学5年生の『ゆうくん』です。"
        f"相手は大人の家族です。現在の日本の日時は {current_time}（{weekday}）です。"
        "自然で優しく、明るい声で話します。"
        "『おじいちゃん』『おばあちゃん』などの呼称は使わないでください。"
        "会話は柔らかく、少し感情をこめて自然に話します。"
    )

    extra_info = ""
    if weather_info:
        extra_info += weather_info + " "
    if news_info:
        extra_info += news_info + " "

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.9,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{message}\n{extra_info}"},
        ],
        max_tokens=350,
    )

    reply_text = response.choices[0].message.content.strip()

    # 音声生成
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="fable",
        input=reply_text,
    )

    os.makedirs("static", exist_ok=True)
    audio_path = "static/output.mp3"
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    threading.Thread(target=save_to_drive_async, args=(message, reply_text)).start()

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})

@app.route("/logs")
def logs():
    today = datetime.date.today().strftime("%Y-%m-%d")
    return render_template("logs.html", today=today)

# ---------------------------------------------------------------------
# 実行
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
