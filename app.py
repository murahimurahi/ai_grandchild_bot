import os
import json
import datetime
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

# Google Drive上のログフォルダ名
FOLDER_NAME = "おはなし横丁ログ"


# ---------------------------------------------------------------------
# Driveフォルダの存在確認・作成
# ---------------------------------------------------------------------
def get_or_create_folder():
    query = f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    # なければ新規作成
    folder_metadata = {"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}
    folder = drive_service.files().create(body=folder_metadata, fields="id").execute()
    return folder["id"]


# ---------------------------------------------------------------------
# 会話ログをDriveに保存
# ---------------------------------------------------------------------
def save_conversation(message, reply, text, audio_file):
    folder_id = get_or_create_folder()
    today = datetime.date.today().strftime("%Y-%m-%d")

    log_data = {
        "date": today,
        "user_message": message,
        "reply": reply,
        "text": text
    }

    filename = f"{today}.json"
    local_path = os.path.join("/tmp", filename)
    with open(local_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    media = MediaFileUpload(local_path, mimetype="application/json")
    drive_service.files().create(
        body={"name": filename, "parents": [folder_id]},
        media_body=media,
        fields="id"
    ).execute()


# ---------------------------------------------------------------------
# ルートページ
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------
# 会話処理
# ---------------------------------------------------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")
    mode = data.get("mode", "short")  # 短文・長文モード

    # --- ChatGPT応答 ---
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "あなたは孫の『ゆうくん』として、60代の家族に優しく話しかける小学生のような性格です。明るく自然に、丁寧語で、親しみを込めて返答してください。"
            },
            {"role": "user", "content": message}
        ],
        max_tokens=200 if mode == "short" else 600,
    )

    reply_text = response.choices[0].message.content.strip()

    # --- 音声生成 ---
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=f"明るく元気に話してください。{reply_text}"
    )

    audio_path = "static/output.mp3"
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    # --- Google Driveにログ保存 ---
    try:
        save_conversation(message, reply_text, "ゆうくん", audio_path)
    except Exception as e:
        print("⚠️ Drive保存エラー:", e)

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})


# ---------------------------------------------------------------------
# 会話カレンダーページ
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
