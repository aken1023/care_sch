// 全局變數
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let timerInterval;
let startTime;

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

// 更新計時器顯示
function updateTimer() {
    const now = new Date();
    const elapsed = now - startTime;
    const minutes = Math.floor(elapsed / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    const timerElement = document.getElementById('timer');
    if (timerElement) {
        timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
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

// 開始錄音
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100
            }
        });

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await uploadAudio(audioBlob);
        };

        // 清空之前的錄音數據
        audioChunks = [];
        
        // 開始錄音
        mediaRecorder.start();
        isRecording = true;
        
        // 更新 UI
        const recordButton = document.getElementById('recordButton');
        const recordingStatus = document.getElementById('recordingStatus');
        const timer = document.getElementById('timer');
        const progressBar = document.getElementById('progressBar');
        
        if (recordButton) {
            recordButton.classList.add('recording');
            recordButton.innerHTML = '<i class="fas fa-stop fa-2x"></i>';
        }
        if (recordingStatus) {
            recordingStatus.textContent = '正在錄音...';
        }
        if (timer) {
            timer.classList.remove('d-none');
            startTime = new Date();
            timerInterval = setInterval(updateTimer, 1000);
            updateTimer();
        }
        if (progressBar) {
            progressBar.classList.remove('d-none');
        }

    } catch (error) {
        console.error('錄音錯誤：', error);
        alert('無法啟動錄音功能：' + error.message);
        const recordingStatus = document.getElementById('recordingStatus');
        if (recordingStatus) {
            recordingStatus.textContent = '錄音功能初始化失敗';
        }
    }
}

// 停止錄音
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        isRecording = false;
        
        // 更新 UI
        const recordButton = document.getElementById('recordButton');
        const recordingStatus = document.getElementById('recordingStatus');
        const timer = document.getElementById('timer');
        
        if (recordButton) {
            recordButton.classList.remove('recording');
            recordButton.innerHTML = '<i class="fas fa-microphone fa-2x"></i>';
        }
        if (recordingStatus) {
            recordingStatus.textContent = '處理中...';
        }
        if (timer) {
            clearInterval(timerInterval);
        }
        
        // 顯示處理狀態
        const processingStatus = document.getElementById('processingStatus');
        if (processingStatus) {
            processingStatus.classList.remove('d-none');
        }
    }
}

// 上傳音訊檔案
async function uploadAudio(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    
    // 添加交班護理師資訊
    const handoverFrom = document.getElementById('handoverFrom').value;
    formData.append('handoverFrom', handoverFrom || '未填寫');
    
    try {
        const response = await fetch('/care-record/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`上傳失敗：${response.status}`);
        }
        
        const data = await response.json();
        
        // 更新報告內容
        const reportContent = document.querySelector('.report-content');
        if (reportContent && data.success) {
            reportContent.innerHTML = `<div class="report-text">${data.report}</div>`;
        }
        
        // 更新狀態
        const recordingStatus = document.getElementById('recordingStatus');
        const processingStatus = document.getElementById('processingStatus');
        const progressBar = document.getElementById('progressBar');
        
        if (recordingStatus) {
            recordingStatus.textContent = '準備就緒';
        }
        if (processingStatus) {
            processingStatus.classList.add('d-none');
        }
        if (progressBar) {
            progressBar.classList.add('d-none');
        }
        
        // 更新時間戳記
        updateReportTimestamp();
        
    } catch (error) {
        console.error('上傳錯誤：', error);
        alert('處理過程中發生錯誤：' + error.message);
        
        const recordingStatus = document.getElementById('recordingStatus');
        const processingStatus = document.getElementById('processingStatus');
        if (recordingStatus) {
            recordingStatus.textContent = '處理失敗';
        }
        if (processingStatus) {
            processingStatus.classList.add('d-none');
        }
    }
}

// 當頁面載入完成時初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化系統時間
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // 初始化報告時間戳記
    updateReportTimestamp();
    
    // 設置錄音按鈕事件
    const recordButton = document.getElementById('recordButton');
    if (recordButton) {
        recordButton.addEventListener('click', () => {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        });
    }
    
    // 設置報告編輯按鈕事件
    const editReportBtn = document.getElementById('editReportBtn');
    const saveReportBtn = document.getElementById('saveReportBtn');
    const reportResult = document.getElementById('reportResult');
    
    if (editReportBtn && saveReportBtn && reportResult) {
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
            updateReportTimestamp();
        });
    }
    
    // 設置發送郵件按鈕事件
    const sendEmailBtn = document.getElementById('sendEmailBtn');
    if (sendEmailBtn) {
        sendEmailBtn.addEventListener('click', async () => {
            const handoverFrom = document.getElementById('handoverFrom').value;
            const report = reportResult.textContent;
            
            if (!handoverFrom) {
                alert('請填寫交接護理師姓名');
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
                        report,
                        email: 'aken1023@gmail.com'
                    })
                });
                
                if (!response.ok) {
                    throw new Error('發送失敗');
                }
                
                alert('報告已成功發送至信箱！');
            } catch (error) {
                console.error('發送郵件錯誤：', error);
                alert('發送郵件時發生錯誤，請稍後再試');
            } finally {
                sendEmailBtn.disabled = false;
                sendEmailBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>發送報告至信箱';
            }
        });
    }
}); 