import os
import json
import datetime
import threading
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------
app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Google Drive 設定
SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=credentials)
FOLDER_NAME = "おはなし横丁ログ"

# ---------------------------------------------------------------------
# Driveフォルダ取得または作成
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
# Drive保存（別スレッドで非同期実行）
# ---------------------------------------------------------------------
def save_to_drive_async(message, reply_text):
    try:
        today = datetime.date.today().strftime("%Y-%m-%d")
        log_data = {
            "date": today,
            "user_message": message,
            "reply": reply_text,
        }
        filename = f"{today}.json"
        local_path = os.path.join("/tmp", filename)

        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        media = MediaFileUpload(local_path, mimetype="application/json")
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
# 会話処理（高速・同期音声対応）
# ---------------------------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")

    # --- ChatGPT 応答（短く自然に） ---
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.8,
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは小学5年生の『ゆうくん』です。"
                    "相手は大人の家族ですが、"
                    "『おじいちゃん』『おばあちゃん』などの呼称は使いません。"
                    "自然で優しく、思いやりのある話し方で、"
                    "一文ずつ短く返答してください。"
                    "絵文字や記号は使わず、口調は穏やかで明るく。"
                )
            },
            {"role": "user", "content": message}
        ],
        max_tokens=150,
    )

    reply_text = response.choices[0].message.content.strip()

    # --- 音声生成（同期実行・完全一致） ---
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="fable",  # 少年寄りの自然な声
        input=reply_text
    )

    audio_path = "static/output.mp3"
    with open(audio_path, "wb") as f:
        for chunk in speech.iter_bytes():  # ストリーミング書き込みで即応答
            f.write(chunk)
            f.flush()

    # --- Drive保存を別スレッドで実行（返答をブロックしない） ---
    threading.Thread(target=save_to_drive_async, args=(message, reply_text)).start()

    # --- 即レスポンス ---
    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})

# ---------------------------------------------------------------------
# ログページ
# ---------------------------------------------------------------------
@app.route("/logs")
def logs():
    today = datetime.date.today().strftime("%Y-%m-%d")
    return render_template("logs.html", today=today)

# ---------------------------------------------------------------------
# 実行
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
