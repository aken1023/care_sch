document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const audioFile = document.getElementById('audioInput').files[0];
    if (!audioFile) {
        alert('請選擇音訊檔案');
        return;
    }
    
    const formData = new FormData();
    formData.append('audio', audioFile);
    
    try {
        const response = await fetch('/care-record/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error?.message || '上傳失敗');
        }
        
        if (result.success) {
            // 處理成功的回應
            document.getElementById('reportContent').innerHTML = result.report;
        } else {
            throw new Error(result.error || '處理失敗');
        }
        
    } catch (error) {
        console.error('上傳錯誤:', error);
        alert('上傳失敗: ' + error.message);
    }
}); 