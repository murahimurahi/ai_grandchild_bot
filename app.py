import os
import json
import datetime
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

# ------------------------
# Flask設定
# ------------------------
app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ------------------------
# Google Drive 永続保存設定
# ------------------------
SERVICE_ACCOUNT_FILE = "service_account.json"  # ← あなたの認証ファイル名
FOLDER_NAME = "おはなし横丁ログ"

# サービスアカウント認証
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/drive.file"]
)
drive_service = build("drive", "v3", credentials=creds)

# フォルダ確認 or 作成
def get_or_create_folder():
    results = drive_service.files().list(
        q=f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces="drive"
    ).execute()
    items = results.get("files", [])
    if items:
        return items[0]["id"]
    file_metadata = {"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}
    folder = drive_service.files().create(body=file_metadata, fields="id").execute()
    return folder.get("id")

FOLDER_ID = get_or_create_folder()

# ------------------------
# ローカル保存用
# ------------------------
LOG_DIR = "/tmp/logs"
AUDIO_DIR = "static/audio"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)


# ------------------------
# 会話保存 & Drive同期
# ------------------------
def save_conversation(user_msg, ai_reply, audio_file):
    today = datetime.date.today().isoformat()
    file_path = os.path.join(LOG_DIR, f"{today}.json")

    # 既存読み込み or 新規作成
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []
    data.append({"user": user_msg, "yuukun": ai_reply, "audio_file": audio_file})
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Google Driveにアップロード／更新
    results = drive_service.files().list(
        q=f"name='{today}.json' and '{FOLDER_ID}' in parents and trashed=false",
        spaces="drive"
    ).execute()
    items = results.get("files", [])

    media = MediaFileUpload(file_path, mimetype="application/json", resumable=True)

    if items:
        # 上書き
        drive_service.files().update(fileId=items[0]["id"], media_body=media).execute()
    else:
        # 新規作成
        file_metadata = {"name": f"{today}.json", "parents": [FOLDER_ID]}
        drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()


# ------------------------
# トップページ
# ------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ------------------------
# 会話API
# ------------------------
@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    message = data.get("message", "")

    # --- AI応答生成 ---
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは小学5年生の優しい孫『ゆうくん』です。"
                    "聞き手は大切な年上の家族です。"
                    "ただし「おじいちゃん」「おばあちゃん」とは呼ばず、"
                    "自然で温かい言葉づかいで話してください。"
                    "話しかけるように一文ずつ丁寧に。"
                    "相手が安心できるよう、穏やかで思いやりのあるトーンで返答します。"
                    "感情的な補足説明や括弧の文章は使わず、自然な会話文のみを返します。"
                )
            },
            {"role": "user", "content": message}
        ]
    )
    reply_text = response.choices[0].message.content.strip()

    # --- 音声生成 ---
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="fable",
        input=reply_text
    )

    audio_filename = f"{datetime.datetime.now().strftime('%H%M%S')}.mp3"
    audio_path = os.path.join(AUDIO_DIR, audio_filename)
    with open(audio_path, "wb") as f:
        f.write(speech.read())

    # --- 保存処理 ---
    save_conversation(message, reply_text, audio_filename)

    return jsonify({"reply": reply_text, "audio_url": f"/{audio_path}"})


# ------------------------
# ログ表示
# ------------------------
@app.route("/logs")
def logs():
    logs_data = []

    # Google Drive上のファイルを一覧取得
    results = drive_service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        spaces="drive"
    ).execute()
    items = results.get("files", [])

    for file in sorted(items, key=lambda x: x["name"], reverse=True):
        file_id = file["id"]
        request_dl = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_dl)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        entries = json.loads
