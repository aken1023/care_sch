// 檢查瀏覽器支援
if (!window.MediaRecorder) {
    alert('此瀏覽器不支援錄音功能');
}

let mediaStream = null;
let audioContext = null;
let mediaRecorder = null;
let audioChunks = [];

// 檢測是否在 LINE 內建瀏覽器中
function isLineInAppBrowser() {
    return /Line/i.test(navigator.userAgent);
}

// 檢測是否為移動設備
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// 取得適合的瀏覽器建議
function getBrowserSuggestion() {
    if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
        return 'Safari';
    } else if (/Android/.test(navigator.userAgent)) {
        return 'Chrome';
    }
    return '系統預設瀏覽器';
}

// 顯示使用外部瀏覽器的提示
function showBrowserSuggestion() {
    const browserName = getBrowserSuggestion();
    const message = `
        <div style="text-align: center; padding: 20px;">
            <h3 style="color: #e74c3c;">請使用外部瀏覽器</h3>
            <p>LINE 內建瀏覽器不支援錄音功能，請使用 ${browserName} 開啟此網頁。</p>
            <button onclick="openInExternalBrowser()" style="
                padding: 10px 20px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                margin-top: 10px;
            ">在${browserName}中開啟</button>
        </div>
    `;
    
    document.body.innerHTML = message;
}

// 在外部瀏覽器中開啟
function openInExternalBrowser() {
    const currentUrl = window.location.href;
    if (isMobileDevice()) {
        if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
            window.location.href = `googlechrome://${currentUrl}`;
            setTimeout(() => {
                window.location.href = currentUrl;
            }, 2000);
        } else {
            window.location.href = currentUrl;
        }
    }
}

// 初始化錄音
async function initializeRecorder() {
    try {
        // 1. 請求麥克風權限
        mediaStream = await navigator.mediaDevices.getUserMedia({ 
            audio: true,
            video: false
        });
        
        console.log('成功獲得麥克風權限');
        
        // 2. 建立音訊內容
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // 3. 建立基本的錄音器
        mediaRecorder = new MediaRecorder(mediaStream);
        
        // 4. 設定數據處理
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        return true;
    } catch (error) {
        console.error('初始化錄音失敗:', error);
        document.getElementById('recordingStatus').textContent = 
            `初始化失敗: ${error.message}`;
        return false;
    }
}

// 開始錄音
function startRecording() {
    try {
        audioChunks = [];
        mediaRecorder.start();
        console.log('開始錄音');
    } catch (error) {
        console.error('開始錄音失敗:', error);
        document.getElementById('recordingStatus').textContent = 
            `開始錄音失敗: ${error.message}`;
    }
}

// 停止錄音
function stopRecording() {
    return new Promise((resolve, reject) => {
        try {
            mediaRecorder.onstop = async () => {
                try {
                    const audioBlob = new Blob(audioChunks);
                    await uploadAudio(audioBlob);
                    resolve();
                } catch (error) {
                    reject(error);
                }
            };
            
            mediaRecorder.stop();
        } catch (error) {
            reject(error);
        }
    });
}

// 上傳音訊
async function uploadAudio(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob);

    try {
        const response = await fetch('/care-record/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`上傳失敗: ${response.status}`);
        }

        const result = await response.json();
        if (result.success) {
            displayReport(result.report);
            document.getElementById('recordingStatus').textContent = '上傳成功';
        } else {
            throw new Error(result.error || '上傳失敗');
        }
    } catch (error) {
        console.error('上傳錯誤:', error);
        document.getElementById('recordingStatus').textContent = 
            `上傳失敗: ${error.message}`;
        throw error;
    }
}

// 在頁面載入時檢查瀏覽器
document.addEventListener('DOMContentLoaded', async () => {
    if (isLineInAppBrowser()) {
        showBrowserSuggestion();
        return;
    }

    const recordButton = document.getElementById('recordButton');
    const recordingStatus = document.getElementById('recordingStatus');
    
    // 檢查瀏覽器支援
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        recordingStatus.textContent = '您的瀏覽器不支援錄音功能';
        recordButton.disabled = true;
        return;
    }

    let isRecording = false;

    try {
        const initialized = await initializeRecorder();
        if (!initialized) {
            recordButton.disabled = true;
            return;
        }

        recordButton.addEventListener('click', async () => {
            if (!isRecording) {
                startRecording();
                recordButton.classList.add('recording');
                recordingStatus.textContent = '錄音中...';
                isRecording = true;
            } else {
                recordingStatus.textContent = '處理中...';
                recordButton.classList.remove('recording');
                try {
                    await stopRecording();
                    isRecording = false;
                } catch (error) {
                    console.error('錄音處理失敗:', error);
                    recordingStatus.textContent = '錄音處理失敗';
                }
            }
        });

        recordingStatus.textContent = '準備就緒';
        console.log('錄音功能初始化完成');
    } catch (error) {
        console.error('設定錄音功能時發生錯誤:', error);
        recordingStatus.textContent = `錄音功能設定失敗: ${error.message}`;
        recordButton.disabled = true;
    }
}); 