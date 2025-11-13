import os, json, requests, datetime, logging
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ---------------------------------------------------------
# 基本設定
# ---------------------------------------------------------
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX")
GOOGLE_APPLICATION_CREDENTIALS = "/etc/secrets/service_account.json"

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------
# Google Drive ログ保存（1日1ファイル）
# ---------------------------------------------------------
def save_to_drive_log(user_text, reply_text):
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_APPLICATION_CREDENTIALS,
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        service = build("drive", "v3", credentials=creds)

        today = datetime.date.today().strftime("%Y-%m-%d")
        filename = f"conversation_{today}.txt"

        # 既存ファイルを検索
        query = f"name='{filename}' and mimeType='text/plain'"
        results = service.files().list(q=query, spaces="drive", fields="files(id)").execute()
        items = results.get("files", [])

        if items:
            file_id = items[0]["id"]
            existing = service.files().get_media(fileId=file_id).execute().decode("utf-8")
            content = existing + f"\n👤User: {user_text}\n🤖Yuu: {reply_text}\n"
            service.files().update(fileId=file_id, media_body={"body": content}).execute()
        else:
            # 新規作成
            content = f"👤User: {user_text}\n🤖Yuu: {reply_text}\n"
            file_metadata = {"name": filename, "mimeType": "text/plain"}
            service.files().create(body=file_metadata, media_body={"body": content}).execute()

    except Exception as e:
        logging.error(f"Drive保存エラー: {e}")

# ---------------------------------------------------------
# 天気情報（OpenWeather）
# ---------------------------------------------------------
def get_weather(user_text="東京"):
    try:
        import re
        city_match = re.search(r"(.+?)の天気", user_text)
        city = city_match.group(1) if city_match else "東京"

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
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

# ---------------------------------------------------------
# 総理大臣・時事ニュース（Google Custom Search）
# ---------------------------------------------------------
def get_prime_minister():
    try:
        query = "日本の現在の総理大臣"
        url = (
            f"https://www.googleapis.com/customsearch/v1"
            f"?key={GOOGLE_SEARCH_API_KEY}&cx={GOOGLE_SEARCH_CX}&q={query}"
        )
        res = requests.get(url, timeout=5)
        data = res.json()

        if "items" in data:
            snippet = data["items"][0]["snippet"]
            return f"検索結果によると、{snippet}"
        else:
            return "今の総理大臣は高市早苗さんみたいだよ。"
    except Exception as e:
        logging.error(f"検索APIエラー: {e}")
        return "ニュース情報を取得できなかったけど、今は高市早苗さんが総理だと思うよ。"

# ---------------------------------------------------------
# Flask ルート
# ---------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_text = data.get("message", "")

    # ① 特殊質問（総理・天気・時間）
    if any(k in user_text for k in ["総理", "首相", "大臣"]):
        reply_text = get_prime_minister()
    elif "天気" in user_text:
        reply_text = get_weather(user_text)
    elif "時間" in user_text or "何時" in user_text:
        now = datetime.datetime.now().strftime("%H時%M分")
        reply_text = f"今は{now}だよ！"
    else:
        # 通常の会話
        prompt = (
            "あなたは明るく元気な孫のゆうくんです。"
            "60〜80代の利用者に、やさしく自然に話しかけてください。"
            "おじいちゃん・おばあちゃんという呼称は使わないでください。"
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_text}
            ]
        )
        reply_text = response.choices[0].message.content.strip()

    # Driveログ保存
    save_to_drive_log(user_text, reply_text)

    # 音声生成
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",  # ゆうくん用
        input=reply_text
    )
    audio_path = "static/output.mp3"
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})

# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
