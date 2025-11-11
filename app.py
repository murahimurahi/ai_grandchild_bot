# キャラクターごとに声を切り替える
if character == "みさちゃん（孫娘）":
    voice_type = "verse"   # やわらかい女の子の声
elif character == "ゆうくん（孫息子）":
    voice_type = "nova"    # 少年っぽい明るい声
else:
    voice_type = "alloy"   # 落ち着いた大人男性（父・ソウタ）

tts = client.audio.speech.create(
    model="gpt-4o-mini-tts",
    voice=voice_type,
    input=reply_text
)
