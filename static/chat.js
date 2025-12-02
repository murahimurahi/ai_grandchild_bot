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

    recognition.onresult = function(event) {
        const text = event.results[0][0].transcript;
        sendText(text);
    };
}

voiceBtn.onclick = () => {
    try { recognition.start(); } catch {}
};

/* =============================
   送信
============================= */
sendBtn.onclick = () => {
    const text = textInput.value.trim();
    if (text) sendText(text);
};

textInput.addEventListener("keydown", e => {
    if (e.key === "Enter") sendBtn.click();
});

/* =============================
   メッセージ送信処理
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
        if (data.voice) addVoiceLog(data.voice);
    });
}

/* =============================
   UI描画
============================= */
function addMessage(type, text) {
    const div = document.createElement("div");
    div.className = `message ${type}`;
    div.innerText = text;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addVoiceLog(url) {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.src = url;
    audio.className = "voice-log-item";

    voiceLogsDiv.appendChild(audio);
    voiceLogsDiv.scrollTop = voiceLogsDiv.scrollHeight;
}
