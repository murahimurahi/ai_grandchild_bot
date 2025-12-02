const chatBox = document.getElementById("chat-box");
const input = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const voiceBtn = document.getElementById("voice-btn");
const voiceArea = document.getElementById("voice-log-area");

// メッセージ追加
function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = "msg";
    div.innerHTML = `<strong>${sender}</strong>：${text}`;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// 音声ログ追加＋自動再生
function addVoice(url) {
    const audio = document.createElement("audio");
    audio.src = url;
    audio.controls = true;
    audio.autoplay = true;
    audio.className = "voice-item";
    voiceArea.appendChild(audio);
}

// 送信処理
function sendMessage(text) {
    addMessage("あなた", text);

    fetch("/api/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({text})
    })
    .then(r => r.json())
    .then(data => {
        addMessage("ゆうくん", data.reply);
        addVoice(data.voice);
    });
}

sendBtn.onclick = () => {
    const t = input.value.trim();
    if (t) sendMessage(t);
    input.value = "";
};

input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendBtn.click();
});

// 音声入力
if ("webkitSpeechRecognition" in window) {
    const rec = new webkitSpeechRecognition();
    rec.lang = "ja-JP";
    rec.continuous = false;
    rec.interimResults = false;

    voiceBtn.onclick = () => rec.start();

    rec.onresult = e => {
        const t = e.results[0][0].transcript;
        sendMessage(t);
    };
}
