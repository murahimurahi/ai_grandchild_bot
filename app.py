import os
import json
import datetime
import threading
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Google Drive設定
SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=credentials)
FOLDER_NAME = "おはなし横丁ログ"

# ---------------------------------------------------------------------
# Driveフォルダ作成 or 取得
# ---------------------------------------------------------------------
def get_or_create_folder():
    query = f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    folder_metadata = {"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}
    folder = drive_service.files().create(body=folder_metadata, fields="id").execute()
    return folder["id"]

FOLDER_ID = get_or_create_folder()

# ---------------------------------------------------------------------
# Drive保存（非同期）
# ---------------------------------------------------------------------
def save_to_drive_async(message, reply_text):
    try:
        today = datetime.date.today().strftime("%Y-%m-%d")
        log_data = {"date": today, "user_message": message, "reply": reply_text}
        filename = f"{today}.json"
        path = os.path.join("/tmp", filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        media = MediaFileUpload(path, mimetype="application/json")
        drive_service.files().create(
            body={"name": filename, "parents": [FOLDER_ID]},
            media_body=media,
            fields="id"
        ).execute()
    except Exception as e:
        print("⚠️ Drive保存エラー:", e)

# ---------------------------------------------------------------------
# トップページ
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------------------------------------------------------------
# 会話API（確実に音声出る版）
# ---------------------------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")

    # --- ChatGPT応答 ---
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.8,
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは小学5年生の『ゆうくん』です。"
                    "相手は大人の家族。"
                    "自然で優しく、思いやりを持った話し方をします。"
                    "決して『おじいちゃん』『おばあちゃん』などの呼称を使いません。"
                    "返答は短く、穏やかで温かみのある一文にしてください。"
                ),
            },
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )

    reply_text = response.choices[0].message.content.strip()

    # --- 音声生成（同期方式・確実出力） ---
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="fable",
        input=reply_text,
    )

    os.makedirs("static", exist_ok=True)
    audio_path = "static/output.mp3"

    # 同期書き込み（確実にファイル生成）
    with open(audio_path, "wb") as f:
        f.write(speech.read())  # ← 安定動作版

    # --- Drive保存（別スレッド） ---
    threading.Thread(target=save_to_drive_async, args=(message, reply_text)).start()

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})

# ---------------------------------------------------------------------
@app.route("/logs")
def logs():
    today = datetime.date.today().strftime("%Y-%m-%d")
    return render_template("logs.html", today=today)

# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
