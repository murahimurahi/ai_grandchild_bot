import os
import json
import io
import requests
import datetime
import logging
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# -----------------------------
# Render環境変数
# -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX")
GOOGLE_APPLICATION_CREDENTIALS = "/etc/secrets/service_account.json"

client = OpenAI(api_key=OPENAI_API_KEY)

# ===========================================================
# Google Drive ログ保存（quota error 対策版）
# ===========================================================
def save_to_drive_log(user_text, reply_text):
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_APPLICATION_CREDENTIALS,
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        service = build("drive", "v3", credentials=creds)

        today = datetime.date.today().strftime("%Y-%m-%d")
        filename = f"conversation_{today}.txt"

        query = f"name='{filename}' and mimeType='text/plain'"
        results = service.files().list(
            q=query, spaces="drive", fields="files(id)"
        ).execute()
        items = results.get("files", [])

        content = f"👤User: {user_text}\n🤖Yuu: {reply_text}\n"

        if items:
            file_id = items[0]["id"]
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode("utf-8")),
                mimetype="text/plain",
                resumable=False
            )
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {"name": filename, "mimeType": "text/plain"}
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode("utf-8")),
                mimetype="text/plain",
                resumable=False
            )
            service.files().create(
                body=file_metadata,
                media_body=media
            ).execute()

    except Exception as e:
        logging.error(f"Driveログ保存エラー: {e}")

# ===========================================================
# OpenWeather（天気API）
# ===========================================================
def get_weather(user_text="東京"):
    try:
        import re
        city_match = re.search(r"(.+?)の天気", user_text)
        city = city_match.group(1) if city_match else "東京"

        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}"
            f"&units=metric&lang=ja"
        )
        res = requests.get(url, timeout=6)
        data = res.json()

        if data.get("cod") != 200:
            return f"{city}の天気情報が見つからなかったよ。"

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]

        return f"今の{city}の天気は{desc}、気温は{temp:.1f}度だよ！"

    except Exception as e:
        logging.error(f"天気取得エラー: {e}")
        return "天気情報を取得できなかったよ。"

# ===========================================================
# Custom Google Search（最新版・snippet/title対応）
# ===========================================================
def google_search(query):
    try:
        url = (
            "https://www.googleapis.com/customsearch/v1"
            f"?key={GOOGLE_SEARCH_API_KEY}"
            f"&cx={GOOGLE_SEARCH_CX}"
            f"&q={query}"
            f"&num=1"
            f"&lr=lang_ja"
        )

        res = requests.get(url, timeout=8)
        data = res.json()

        items = data.get("items")
        if not items:
            return None

        top = items[0]
        snippet = top.get("snippet")
        title = top.get("title")

        return snippet or title

    except Exception as e:
        logging.error(f"検索エラー: {e}")
        return None

# ===========================================================
# 総理大臣
# ===========================================================
def get_prime_minister():
    result = google_search("日本の総理大臣")
    if result:
        return f"調べてみたよ！いまは {result}"
    return "ごめんね、うまく調べられなかったよ。"

# ===========================================================
# Flask ルート
# ===========================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "").strip()

    # ▼ 特殊キーワード処理
    if any(k in user_text for k in ["天気", "気温"]):
        reply_text = get_weather(user_text)

    elif any(k in user_text for k in ["総理", "首相"]):
        reply_text = get_prime_minister()

    elif any(k in user_text for k in ["大統領", "アメリカ", "米国"]):
        result = google_search("アメリカの大統領")
        if result:
            reply_text = f"調べてみたよ！{result}"
        else:
            reply_text = "ごめんね、うまく調べられなかったよ。"

    else:
        # ▼ 通常会話（毎回新しいセッション → 繰り返しバグ対策）
        prompt = (
            "あなたは明るく優しい孫のゆうくんです。"
            "60〜80代の利用者に自然に優しく話します。"
            "おばあちゃん・おじいちゃんという呼称は使わないこと。"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text}
            ]
        )
        reply_text = response.choices[0].message.content.strip()

    # ▼ Google Drive にログ保存
    save_to_drive_log(user_text, reply_text)

    # ▼ 音声生成
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=reply_text
    )
    audio_path = "static/output.mp3"
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
