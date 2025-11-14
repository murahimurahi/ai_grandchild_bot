const messagesDiv = document.getElementById("messages");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const voiceBtn = document.getElementById("voiceBtn");
const voiceLogArea = document.getElementById("voice-log-area");

// --------------------------
// メッセージ追加
// --------------------------
function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = "message";
    div.innerHTML = `<strong>${sender}：</strong> ${text}`;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// --------------------------
// 送信処理
// --------------------------
function sendText(text) {
    addMessage("あなた", text);
    textInput.value = "";

    fetch("/api/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
        addMessage("ゆうくん", data.reply);

        if (data.voice_url) {
            const audio = document.createElement("audio");
            audio.controls = true;
            audio.src = data.voice_url;
            voiceLogArea.appendChild(audio);
        }
    });
}

sendBtn.onclick = () => {
    if (textInput.value.trim() !== "") {
        sendText(textInput.value.trim());
    }
};

textInput.addEventListener("keydown", e => {
    if (e.key === "Enter") sendBtn.click();
});

// --------------------------
// 音声入力（手動）
// --------------------------
if ('webkitSpeechRecognition' in window) {
    const rec = new webkitSpeechRecognition();
    rec.lang = "ja-JP";
    rec.continuous = false;
    rec.interimResults = false;

    voiceBtn.onclick = () => {
        rec.start();
    };

    rec.onresult = function(event) {
        const text = event.results[0][0].transcript;
        sendText(text);
    };
}
