import os
import json
from datetime import datetime
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# -------------------------
# 天気取得
# -------------------------
def get_weather(user_text):
    try:
        import re
        m = re.search(r"(.*)の天気", user_text)
        city = m.group(1) if m else "名古屋"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
        r = requests.get(url)
        data = r.json()

        if data.get("cod") != 200:
            return f"{city}の天気は見つかりませんでした。"

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"{city}の天気は {desc}、気温は {temp:.1f} 度のようですよ。"

    except:
        return "天気情報を取得できませんでした。"


# -------------------------
# ChatGPT（丁寧語のゆうくん）
# -------------------------
def ai_reply(user_text):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "あなたは優しい孫の“ゆうくん”として、必ず丁寧語で話してください。相手をおじいちゃん・おばあちゃんとは呼ばず『あなた』と呼びます。"
            },
            {"role": "user", "content": user_text}
        ]
    }

    r = requests.post(url, headers=headers, json=payload)
    return r.json()["choices"][0]["message"]["content"]


# -------------------------
# TTS（音声生成）※今回の最重要修正ポイント
# -------------------------
def generate_voice(text, filename):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"     # ← これが抜けていると音声が生成されません
    }
    payload = {
        "model": "gpt-4o-mini-tts",
        "voice": "verse",
        "input": text
    }

    r = reque
