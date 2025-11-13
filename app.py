import os, json, requests, datetime, logging, io, re
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------
# Render の環境変数
# ---------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX")
GOOGLE_APPLICATION_CREDENTIALS = "/etc/secrets/service_account.json"

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------
# Google Drive ログ保存（完全版）
# ---------------------------------
def save_to_drive_log(user_text, reply_text):
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_APPLICATION_CREDENTIALS,
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        service = build("drive", "v3", credentials=creds)

        today = datetime.date.today().strftime("%Y-%m-%d")
        filename = f"conversation_{today}.txt"

        # ファイル検索
        results = service.files().list(
            q=f"name='{filename}' and mimeType='text/plain'",
            spaces="drive",
            fields="files(id)"
        ).execute()
        items = results.get("files", [])

        text_to_add = f"\n👤User: {user_text}\n🤖Yuu: {reply_text}\n"

        if items:
            # --- 既存ファイルに追記 ---
            file_id = items[0]["id"]

            # 既存内容の取得
            req = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, req)
            done = False
            while not done:
                status, done = downloader.next_chunk()

            prev_content = fh.getvalue().decode("utf-8")
            new_content = prev_content + text_to_add

            # アップロード
            stream = io.BytesIO(new_content.encode("utf-8"))
            media = MediaIoBaseUpload(stream, mimetype="text/plain")
            service.files().update(fileId=file_id, media_body=media).execute()

        else:
            # --- 新規作成 ---
            file_metadata = {"name": filename, "mimeType": "text/plain"}
            stream = io.BytesIO(text_to_add.encode("utf-8"))
            media = MediaIoBaseUpload(stream, mimetype="text/plain")
            service.files().create(body=file_metadata, media_body=media).execute()

    except Exception as e:
        logging.error(f"Drive保存エラー: {e}")

# ---------------------------------
# 天気取得（OpenWeather）
# ---------------------------------
def get_weather(text):
    try:
        m = re.search(r"(.+?)の天気", text)
        city = m.group(1) if m else "東京"

        url = (
            f"http://api.openweathermap.org/data/2.5/weather?"
            f"q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
        )
        res = requests.get(url, timeout=5)
        data = res.json()

        if data.get("cod") != 200:
            return f"{city}の天気情報が見つからなかったよ。"

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"今の{city}の天気は{desc}、気温は{temp:.1f}度だよ！"

    except Exception as e:
        logging.error(f"天気取得エラー: {e}")
        return "天気情報を取得できなかったよ。"

# ---------------------------------
# Google検索（汎用）
# ---------------------------------
def google_search(query):
    try:
        url = (
            f"https://www.googleapis.com/customsearch/v1"
            f"?key={GOOGLE_SEARCH_API_KEY}&cx={GOOGLE_SEARCH_CX}&q={query}"
        )
        res = requests.get(url, timeout=5)
        data = res.json()

        if "items" in data:
            return data["items"][0]["snippet"]

        return "検索結果が見つからなかったよ。"

    except Exception as e:
        logging.error(f"Google検索エラー: {e}")
        return "検索に失敗したよ。"

# ---------------------------------
# 検索必要判定
# ---------------------------------
def needs_search(text):
    keywords = ["誰", "何", "いつ", "どこ", "今", "最近", "最新",
                "話題", "ニュース", "流行", "大統領", "総理", "首相"]
    return any(k in text for k in keywords)

# ---------------------------------
# Flaskルート
# ---------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    text = data.get("message", "").strip()

    # 天気
    if "天気" in text:
        reply = get_weather(text)

    # 時間
    elif "何時" in text or "時間" in text:
        now = datetime.datetime.now().strftime("%H時%M分")
        reply = f"今は{now}だよ！"

    # Google検索が必要
    elif needs_search(text):
        result = google_search(text)
        reply = f"調べてみたよ！\n{result}"

    # GPT（通常会話）
    else:
        prompt = (
            "あなたは明るく元気な孫のゆうくんです。"
            "60〜80代の利用者にやさしく自然に話してください。"
            "おじいちゃん・おばあちゃんという呼称は使わないでください。"
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ]
        )
        reply = response.choices[0].message.content.strip()

    # ログ保存
    save_to_drive_log(text, reply)

    # 音声生成
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=reply
    )
    audio_path = "static/output.mp3"
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    return jsonify({"reply": reply, "audio_url": f"/{audio_path}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
