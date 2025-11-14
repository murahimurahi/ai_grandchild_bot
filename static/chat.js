const messages = document.getElementById("messages");
const voiceLogs = document.getElementById("voice-logs");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const voiceBtn = document.getElementById("voiceBtn");

// ----------------------
// メッセージ描画
// ----------------------
function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = "message";
    div.innerHTML = `<strong>${sender}：</strong> ${text}`;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

// ----------------------
// 音声ログを追加
// ----------------------
function addVoice(url) {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.src = url;
    voiceLogs.appendChild(audio);
    voiceLogs.scrollTop = voiceLogs.scrollHeight;
}

// ----------------------
// サーバー送信
// ----------------------
function sendText(text) {
    addMessage("あなた", text);

    fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
        addMessage("ゆうくん", data.reply);

        if (data.voice_url) {
            addVoice(data.voice_url);
        }
    });

    textInput.value = "";
}

// 送信ボタン
sendBtn.onclick = () => {
    const text = textInput.value.trim();
    if (text !== "") sendText(text);
};

textInput.addEventListener("keydown", e => {
    if (e.key === "Enter") sendBtn.click();
});

// ----------------------
// 音声認識
// ----------------------
let recognition = null;

if ("webkitSpeechRecognition" in window) {
    recognition = new webkitSpeechRecognition();
    recognition.lang = "ja-JP";
    recognition.continuous = false;

    recognition.onresult = function(event) {
        const text = event.results[0][0].transcript;
        sendText(text);
    };
}

voiceBtn.onclick = () => {
    if (recognition) recognition.start();
};
