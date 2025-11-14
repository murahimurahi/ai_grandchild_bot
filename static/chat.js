const chatWindow = document.getElementById("chatWindow");
const sendBtn = document.getElementById("sendBtn");
const voiceBtn = document.getElementById("voiceBtn");

// -----------------------
// メッセージを追加
// -----------------------
function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = "chat-message";
    div.innerHTML = `<strong>${sender}：</strong> ${text}`;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// -----------------------
// サーバーへ送信
// -----------------------
function sendText(text) {
    if (!text || text.trim() === "") return;

    addMessage("あなた", text);

    fetch("/api/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
        addMessage("ゆうくん", data.reply);

        if (data.voice_url) {
            appendVoiceLog(data.voice_url);
        }
    });
}

// -----------------------
// 手動入力
// -----------------------
sendBtn.onclick = () => {
    const inputBox = document.getElementById("textInput");
    const text = inputBox.value;
    sendText(text);
    inputBox.value = "";
};

// Enterキー対応
document.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        sendBtn.click();
    }
});

// -----------------------
// 音声入力
// -----------------------
let recognition;

if ("webkitSpeechRecognition" in window) {
    recognition = new webkitSpeechRecognition();
    recognition.lang = "ja-JP";
    recognition.interimResults = false;

    recognition.onresult = function(event) {
        const text = event.results[0][0].transcript;
        sendText(text);
    };
}

voiceBtn.onclick = () => {
    if (recognition) {
        recognition.start();
    }
};

// -----------------------
// 音声ログ
// -----------------------
function appendVoiceLog(url) {
    const box = document.getElementById("voiceLogs");
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.src = url;
    audio.style.width = "100%";
    audio.style.marginTop = "10px";
    box.appendChild(audio);
}
