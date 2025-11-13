import os
import json
import datetime
import threading
from datetime import timedelta, timezone
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

# ---------------------------------------------------------------------
# Google Drive 認証設定
# ---------------------------------------------------------------------
SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=credentials)

ROOT_FOLDER_NAME = "おはなし横丁ログ"

# ---------------------------------------------------------------------
# フォルダ取得または作成
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


# ---------------------------------------------------------------------
# ルートフォルダと日付フォルダ作成
# ---------------------------------------------------------------------
ROOT_ID = get_or_create_folder(ROOT_FOLDER_NAME)


def get_today_folder():
    today = datetime.date.today().strftime("%Y-%m-%d")
    return get_or_create_folder(today, ROOT_ID)


# ---------------------------------------------------------------------
# 30日以上前のフォルダを削除（自動ローテーション）
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# Drive保存（バックグラウンドで実行）
# ---------------------------------------------------------------------
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

        cleanup_old_folders()  # 自動クリーンアップ
    except Exception as e:
        print("⚠️ Drive保存エラー:", e)
        # ローカルにバックアップ
        try:
            os.makedirs("data", exist_ok=True)
            backup_path = os.path.join("data", "backup.json")
            with open(backup_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"message": message, "reply": reply_text}, ensure_ascii=False) + "\n")
        except Exception as e2:
            print("⚠️ バックアップ失敗:", e2)


# ---------------------------------------------------------------------
# トップページ
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------
# 会話API（JST時刻・自然な会話対応）
# ---------------------------------------------------------------------
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

    # ChatGPT応答
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.9,
        messages=[
            {
                "role": "system",
                "content": (
                    f"あなたは小学5年生の『ゆうくん』です。"
                    f"相手は大人の家族です。"
                    f"現在の日本の日時は {current_time}（{weekday}）です。"
                    "自然で優しく、親しみを持った口調で話してください。"
                    "『おじいちゃん』『おばあちゃん』などの呼称は使わないでください。"
                    "返答は会話調で自然な長さにし、同じ言葉を繰り返さずに話します。"
                    "必要に応じて今の時刻や日付も含めて答えてください。"
                ),
            },
            {"role": "user", "content": message},
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

    # Drive保存をバックグラウンドで実行
    threading.Thread(target=save_to_drive_async, args=(message, reply_text)).start()

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
