/* =============================
   要素取得
============================= */
const messagesDiv = document.getElementById("messages");
const voiceLogsDiv = document.getElementById("voice-logs");
const sendBtn = document.getElementById("sendBtn");
const textInput = document.getElementById("textInput");
const voiceBtn = document.getElementById("voiceBtn");

let recognition;

/* =============================
   音声認識
============================= */
if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.lang = "ja-JP";
    recognition.continuous = false;
    recognition.interimResults = false;

    // 音声結果を受け取ったら送信
    recognition.onresult = function(event) {
        const text = event.results[0][0].transcript;
        sendText(text);
    };
}

// 手動でマイク開始（5秒認識ではなく1文認識）
voiceBtn.onclick = () => {
    try { recognition.start(); } catch (e) {
        console.warn("音声認識エラー:", e);
    }
};


/* =============================
   送信処理
============================= */
sendBtn.onclick = () => {
    const text = textInput.value.trim();
    if (text) sendText(text);
};

// Enter キーで送信
textInput.addEventListener("keydown", e => {
    if (e.key === "Enter") {
        e.preventDefault();
        sendBtn.click();
    }
});


/* =============================
   サーバーへ送信
============================= */
function sendText(text) {
    addMessage("user", text);
    textInput.value = "";

    fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text })
    })
    .then(r => r.json())
    .then(data => {
        addMessage("bot", data.reply);

        // 音声ログがある場合追加
        if (data.voice) addVoiceLog(data.voice);
    })
    .catch(err => console.error("APIエラー:", err));
}


/* =============================
   UI：メッセージ描画
============================= */
function addMessage(type, text) {
    const div = document.createElement("div");
    div.className = `message ${type}`;
    div.innerText = text;

    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}


/* =============================
   UI：音声ログ追加＋自動再生
============================= */
function addVoiceLog(url) {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.src = url;
    audio.className = "voice-log-item";

    voiceLogsDiv.appendChild(audio);
    voiceLogsDiv.scrollTop = voiceLogsDiv.scrollHeight;

    // === 🔥 自動再生 ===
    setTimeout(() => {
        audio.play().catch(err => {
            console.warn("自動再生がブロックされました:", err);
        });
    }, 150);
}
