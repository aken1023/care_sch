from flask import Blueprint, render_template, request, jsonify
import os
from datetime import datetime
import logging
from werkzeug.utils import secure_filename
from . import speech_to_text as stt

# 設定日誌
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 創建 Blueprint
care_record = Blueprint('care_record', __name__,
                       template_folder='templates',
                       static_folder='static',
                       url_prefix='/care-record')

# 確保上傳目錄存在
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@care_record.route('/')
def index():
    return render_template('care_record/index.html')

@care_record.route('/upload', methods=['POST'])
def upload_file():
    try:
        logger.info("開始處理檔案上傳請求")
        
        if 'audio' not in request.files:
            logger.error("沒有收到音訊檔案")
            return jsonify({'error': '沒有收到音訊檔案'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            logger.error("沒有選擇檔案")
            return jsonify({'error': '沒有選擇檔案'}), 400
        
        # 儲存音訊檔案
        filename = secure_filename(f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        logger.info(f"儲存檔案至: {filepath}")
        file.save(filepath)
        
        try:
            # 進行語音辨識
            logger.info("開始進行語音辨識")
            transcribed_text = stt.transcribe_with_whisper(filepath)
            logger.info("語音辨識完成")
            
            # 生成照護報告
            logger.info("開始生成照護報告")
            care_report = stt.generate_care_report(transcribed_text)
            logger.info("照護報告生成完成")
            
            return jsonify({
                'success': True,
                'transcription': transcribed_text,
                'report': care_report
            })
            
        except Exception as e:
            logger.error(f"處理過程中發生錯誤: {str(e)}")
            return jsonify({'error': f"處理過程中發生錯誤: {str(e)}"}), 500
            
        finally:
            # 清理暫存檔案
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info("暫存檔案已清理")
            except Exception as e:
                logger.error(f"清理暫存檔案時發生錯誤: {str(e)}")
                
    except Exception as e:
        logger.error(f"上傳處理過程中發生錯誤: {str(e)}")
        return jsonify({'error': f"上傳處理過程中發生錯誤: {str(e)}"}), 500

@care_record.route('/send_email', methods=['POST'])
def send_email():
    try:
        data = request.json
        
        # 創建郵件內容
        email_content = f"""
照護交接報告
時間：{datetime.now().strftime("%Y/%m/%d %H:%M")}

交接人：{data['handoverFrom']}
接班人：{data['handoverTo']}

=== 照護報告 ===
{data['report']}
"""
        
        # 這裡需要實現實際的郵件發送邏輯
        # 可以使用 SMTP 或其他郵件服務
        
        return jsonify({'success': True, 'message': '郵件發送成功'})
        
    except Exception as e:
        logger.error(f"發送郵件時發生錯誤: {str(e)}")
        return jsonify({'error': f"發送郵件時發生錯誤: {str(e)}"}), 500 