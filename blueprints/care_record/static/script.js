// 在檔案開頭添加 marked 函式庫
let markedInitialized = false;

// 載入 marked 函式庫
function loadMarked() {
    return new Promise((resolve, reject) => {
        if (markedInitialized) {
            resolve();
            return;
        }

        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
        script.onload = () => {
            markedInitialized = true;
            resolve();
        };
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let timerInterval;
let startTime;

const recordButton = document.getElementById('recordButton');
const recordingStatus = document.getElementById('recordingStatus');
const timer = document.getElementById('timer');
const progressBar = document.getElementById('progressBar');
const processingStatus = document.getElementById('processingStatus');
const reportResult = document.getElementById('reportResult');

// 報告編輯功能
const editReportBtn = document.getElementById('editReportBtn');
const saveReportBtn = document.getElementById('saveReportBtn');
const sendEmailBtn = document.getElementById('sendEmailBtn');

// 檢查 HTTPS
if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
    window.location.href = 'https://' + window.location.hostname + window.location.pathname;
}

// 格式化報告顯示
async function formatReport(report) {
    try {
        // 等待 marked 載入完成
        await loadMarked();

        // 設定 marked 選項
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: true,
            mangle: false
        });

        // 將 Markdown 轉換為 HTML
        const htmlContent = marked.parse(report);

        // 添加自定義樣式
        const formattedContent = htmlContent
            .replace(/<h2/g, '<h2 class="report-section-title"')
            .replace(/\[警告\]/g, '<span class="report-warning">[警告]</span>')
            .replace(/\[提醒\]/g, '<span class="report-info">[提醒]</span>')
            .replace(/【.*?】/g, match => `<span class="report-highlight">${match}</span>`);

        return formattedContent;
    } catch (error) {
        console.error('格式化報告時發生錯誤：', error);
        return report; // 如果發生錯誤，返回原始文本
    }
}

// 更新計時器顯示
function updateTimer() {
    const currentTime = new Date().getTime();
    const elapsedTime = new Date(currentTime - startTime);
    const minutes = elapsedTime.getMinutes().toString().padStart(2, '0');
    const seconds = elapsedTime.getSeconds().toString().padStart(2, '0');
    timer.textContent = `${minutes}:${seconds}`;
}

// 開始錄音
async function startRecording() {
    try {
        // 請求麥克風權限時顯示安全提示
        recordingStatus.textContent = '請在瀏覽器的安全提示中允許使用麥克風';
        
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100
            }
        });

        // 檢查支援的音訊格式
        let mimeType = 'audio/webm';
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
            mimeType = 'audio/webm;codecs=opus';
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
            mimeType = 'audio/mp4';
        } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
            mimeType = 'audio/ogg';
        }

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: mimeType,
            audioBitsPerSecond: 128000
        });
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: mimeType });
            await uploadAudio(audioBlob);
        };

        mediaRecorder.onerror = (event) => {
            console.error('錄音錯誤：', event.error);
            alert('錄音過程中發生錯誤：' + event.error.message);
            stopRecording();
        };
        
        audioChunks = [];
        mediaRecorder.start(1000); // 每秒產生一個數據片段
        isRecording = true;
        
        // 更新 UI
        recordButton.classList.add('recording');
        recordButton.innerHTML = '<i class="fas fa-stop"></i>';
        recordingStatus.textContent = '正在錄音...';
        timer.classList.remove('d-none');
        
        // 開始計時
        startTime = new Date().getTime();
        timerInterval = setInterval(updateTimer, 1000);
        
    } catch (error) {
        console.error('錄音錯誤：', error);
        if (error.name === 'NotAllowedError') {
            alert('無法啟動錄音功能：麥克風存取被拒絕。請在瀏覽器設定中允許使用麥克風。');
        } else if (error.name === 'NotFoundError') {
            alert('無法啟動錄音功能：找不到麥克風裝置。');
        } else if (error.name === 'NotSupportedError') {
            alert('您的瀏覽器不支援錄音功能，請使用最新版本的 Chrome、Firefox 或 Safari。');
        } else {
            alert('錄音功能發生錯誤：' + error.message);
        }
        recordingStatus.textContent = '錄音功能初始化失敗';
    }
}

// 停止錄音
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        isRecording = false;
        
        // 更新 UI
        recordButton.classList.remove('recording');
        recordButton.innerHTML = '<i class="fas fa-microphone"></i>';
        recordingStatus.textContent = '處理中...';
        clearInterval(timerInterval);
        
        // 顯示處理狀態
        processingStatus.classList.remove('d-none');
        progressBar.classList.remove('d-none');
    }
}

// 上傳音訊檔案
async function uploadAudio(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    
    try {
        const response = await fetch('/care-record/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // 使用新的格式化函數處理報告
            const formattedReport = await formatReport(data.report);
            reportResult.innerHTML = formattedReport;
            
            recordingStatus.textContent = '準備就緒';
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('上傳錯誤：', error);
        recordingStatus.textContent = '處理失敗';
        alert('處理過程中發生錯誤：' + error.message);
    } finally {
        processingStatus.classList.add('d-none');
        progressBar.classList.add('d-none');
        timer.classList.add('d-none');
    }
}

// 註冊事件監聽器
recordButton.addEventListener('click', () => {
    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
});

editReportBtn.addEventListener('click', () => {
    reportResult.contentEditable = true;
    reportResult.focus();
    editReportBtn.classList.add('d-none');
    saveReportBtn.classList.remove('d-none');
});

saveReportBtn.addEventListener('click', () => {
    reportResult.contentEditable = false;
    editReportBtn.classList.remove('d-none');
    saveReportBtn.classList.add('d-none');
});

// 發送郵件功能
sendEmailBtn.addEventListener('click', async () => {
    const handoverFrom = document.getElementById('handoverFrom').value;
    const handoverTo = document.getElementById('handoverTo').value;
    const report = reportResult.textContent;

    if (!handoverFrom || !handoverTo) {
        alert('請填寫交接人和接班人資訊');
        return;
    }

    try {
        sendEmailBtn.disabled = true;
        sendEmailBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>發送中...';

        const response = await fetch('/care-record/send_email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                handoverFrom,
                handoverTo,
                report,
                email: 'aken1023@gmail.com'
            })
        });

        if (!response.ok) {
            throw new Error('發送失敗');
        }

        const result = await response.json();
        alert('報告已成功發送至信箱！');
    } catch (error) {
        console.error('發送郵件錯誤：', error);
        alert('發送郵件時發生錯誤，請稍後再試');
    } finally {
        sendEmailBtn.disabled = false;
        sendEmailBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>發送報告至信箱';
    }
});

// 更新系統時間顯示
function updateCurrentTime() {
    const now = new Date();
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    const timeString = now.toLocaleString('zh-TW', options);
    const currentTimeElement = document.getElementById('currentTime');
    if (currentTimeElement) {
        currentTimeElement.textContent = timeString;
    }
}

// 更新報告時間戳記
function updateReportTimestamp() {
    const now = new Date();
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    const timeString = now.toLocaleString('zh-TW', options);
    const timestampElement = document.querySelector('.report-timestamp');
    if (timestampElement) {
        timestampElement.textContent = timeString;
    }
}

// 初始化時間顯示
document.addEventListener('DOMContentLoaded', function() {
    // 初始化系統時間
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    // 初始化報告時間戳記
    updateReportTimestamp();
    
    // 監聽報告內容變化
    const reportContent = document.querySelector('.report-content');
    if (reportContent) {
        const observer = new MutationObserver(updateReportTimestamp);
        observer.observe(reportContent, { 
            childList: true, 
            characterData: true, 
            subtree: true 
        });
    }
}); 