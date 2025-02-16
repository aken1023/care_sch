import os
from datetime import datetime
import logging
import traceback
import tempfile
from pydub import AudioSegment
from openai import OpenAI
import json
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    AudioMessage, AudioSendMessage,
    RichMenu, RichMenuArea, RichMenuBounds, RichMenuSize,
    PostbackAction, MessageAction, URIAction,
    QuickReply, QuickReplyButton,
    FlexSendMessage
)
from flask import Flask, request, abort, jsonify
from PIL import Image, ImageDraw, ImageFont
import requests
import numpy as np
from dotenv import load_dotenv
import redis

# 載入環境變數
load_dotenv()

# 確認環境變數是否正確載入
print("LINE_CHANNEL_ACCESS_TOKEN:", os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
print("LINE_CHANNEL_SECRET:", os.getenv('LINE_CHANNEL_SECRET'))

# Redis 連線
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_client = redis.from_url(redis_url)

# 使用環境變數
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 設定 Line Bot API
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

app = Flask(__name__)

# 健康檢查路由
@app.route("/callback", methods=['GET'])
def health_check():
    try:
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"健康檢查失敗: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/status", methods=['GET'])
def status_check():
    """詳細的狀態檢查"""
    try:
        # 檢查 Line Bot API Token
        line_bot_api.get_bot_info()
        # 檢查 OpenAI API Key
        client.models.list()
        # 檢查 Redis 連線
        redis_client.ping()
        
        return jsonify({
            "status": "healthy",
            "services": {
                "line_bot": "connected",
                "openai": "connected",
                "redis": "connected"
            },
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"狀態檢查失敗: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/", methods=['GET'])
def root():
    return jsonify({
        "status": "ok",
        "message": "Service is running"
    }), 200

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def transcribe_audio(audio_file_path):
    """使用 OpenAI Whisper API 將音訊檔案轉換為文字"""
    try:
        logger.info(f"開始處理音訊檔案: {audio_file_path}")
        
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"找不到音訊檔案: {audio_file_path}")
            
        file_size = os.path.getsize(audio_file_path)
        logger.info(f"音訊檔案大小: {file_size} bytes")
        
        with open(audio_file_path, "rb") as audio_file:
            logger.info("開始呼叫 Whisper API")
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="zh"
            )
            
        logger.info("語音轉文字成功完成")
        return response.text

    except Exception as e:
        logger.error(f"語音轉文字失敗: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def save_transcription_log(log_data, audio_file_path):
    """保存轉錄記錄和語音檔案"""
    try:
        timestamp = log_data['timestamp']
        
        # 建立主要儲存目錄
        base_folder = os.path.join(os.getcwd(), 'records')
        os.makedirs(base_folder, exist_ok=True)
        
        # 建立以日期為名的子目錄
        date_folder = os.path.join(base_folder, timestamp[:8])  # YYYYMMDD
        os.makedirs(date_folder, exist_ok=True)
        
        # 建立此次記錄的目錄
        record_folder = os.path.join(date_folder, timestamp[9:])  # HHMMSS
        os.makedirs(record_folder, exist_ok=True)
        
        # 保存音訊檔案
        audio_extension = os.path.splitext(audio_file_path)[1]
        new_audio_path = os.path.join(record_folder, f'audio{audio_extension}')
        import shutil
        shutil.copy2(audio_file_path, new_audio_path)
        logger.info(f"音訊檔案已保存: {new_audio_path}")
        
        # 保存原始文字
        raw_text_path = os.path.join(record_folder, 'raw_text.txt')
        with open(raw_text_path, 'w', encoding='utf-8') as f:
            f.write(log_data['raw_transcription'])
        logger.info(f"原始文字已保存: {raw_text_path}")
        
        # 保存整理後的報告
        report_path = os.path.join(record_folder, 'report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(log_data['formatted_report'])
        logger.info(f"整理後報告已保存: {report_path}")
        
        # 保存完整記錄
        log_path = os.path.join(record_folder, 'record.json')
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        logger.info(f"完整記錄已保存: {log_path}")
        
        return {
            'audio_file': new_audio_path,
            'raw_text': raw_text_path,
            'report': report_path,
            'record': log_path
        }
            
    except Exception as e:
        logger.error(f"記錄保存失敗: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio_message(event):
    """處理音訊訊息"""
    try:
        logger.info("開始處理音訊訊息")
        
        # 取得音訊內容
        message_content = line_bot_api.get_message_content(event.message.id)
        logger.info(f"已取得音訊內容，訊息ID: {event.message.id}")
        
        # 建立臨時檔案
        with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            audio_path = tf.name
        logger.info(f"已儲存音訊檔案至: {audio_path}")
        
        # 轉換音訊
        raw_text = transcribe_audio(audio_path)
        logger.info("音訊轉換完成")
        
        # 使用 ChatGPT 處理
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """你是一位專業的護理紀錄轉換助手。
請將輸入的口語記錄轉換為正式的護理交接報告。"""},
                {"role": "user", "content": raw_text}
            ],
            temperature=0.3
        )
        
        formatted_report = response.choices[0].message.content
        logger.info("報告生成完成")
        
        # 儲存記錄
        log_data = {
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'audio_file': audio_path,
            'raw_transcription': raw_text,
            'formatted_report': formatted_report,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'line_user_id': event.source.user_id
        }
        
        save_paths = save_transcription_log(log_data, audio_path)
        logger.info(f"記錄已儲存: {save_paths}")
        
        # 回傳處理結果
        messages = [
            TextSendMessage(text="原始轉錄文字：\n" + raw_text),
            TextSendMessage(text="整理後報告：\n" + formatted_report)
        ]
        line_bot_api.reply_message(event.reply_token, messages)
        logger.info("已回傳處理結果")
        
    except Exception as e:
        logger.error(f"處理音訊訊息時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"處理音訊時發生錯誤，請稍後再試。\n錯誤訊息：{str(e)}")
        )
    finally:
        # 清理臨時檔案
        if 'audio_path' in locals():
            try:
                os.remove(audio_path)
                logger.info(f"已清理臨時檔案: {audio_path}")
            except Exception as e:
                logger.error(f"清理臨時檔案時發生錯誤: {str(e)}")

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"收到訊息：{text}")
    )

def delete_all_rich_menu():
    """刪除所有現有的 Rich Menu"""
    try:
        logger.info("正在獲取 Rich Menu 列表...")
        rich_menu_list = line_bot_api.get_rich_menu_list()
        
        for rich_menu in rich_menu_list:
            logger.info(f"正在刪除 Rich Menu: {rich_menu.rich_menu_id}")
            line_bot_api.delete_rich_menu(rich_menu.rich_menu_id)
            
        logger.info("所有 Rich Menu 已刪除")
    except Exception as e:
        logger.error(f"刪除 Rich Menu 時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())

def create_rich_menu():
    """建立主選單"""
    try:
        rich_menu_to_create = RichMenu(
            size=RichMenuSize(width=2500, height=1686),
            selected=True,
            name="主選單",
            chat_bar_text="開啟選單",
            areas=[
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=MessageAction(label='使用說明', text='使用說明')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                    action=MessageAction(label='上傳資料', text='上傳資料')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1666, y=0, width=834, height=843),
                    action=MessageAction(label='查看記錄', text='查看記錄')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=843, width=833, height=843),
                    action=MessageAction(label='文字記錄', text='文字記錄')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=843, width=833, height=843),
                    action=MessageAction(label='語音記錄', text='語音記錄')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1666, y=843, width=834, height=843),
                    action=MessageAction(label='設定', text='設定')
                )
            ]
        )
        
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu_to_create)
        
        # 生成並上傳圖片
        image_path = create_rich_menu_image()  # 使用原本的主選單圖片生成函數
        with open(image_path, 'rb') as f:
            line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)
        
        return rich_menu_id
        
    except Exception as e:
        logger.error(f"建立主選單時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def create_rich_menu_image():
    """生成 Rich Menu 圖片"""
    try:
        logger.info("開始生成 Rich Menu 圖片")
        
        # 建立目錄
        os.makedirs('static/images', exist_ok=True)
        
        # 定義按鈕資訊
        buttons = [
            {
                'text': '使用說明',
                'color': '#FF6B6B'  # 溫暖的紅色
            },
            {
                'text': '上傳資料',
                'color': '#4ECDC4'  # 清新的藍綠色
            },
            {
                'text': '查看記錄',
                'color': '#45B7D1'  # 天空藍
            },
            {
                'text': '文字記錄',
                'color': '#96CEB4'  # 薄荷綠
            },
            {
                'text': '語音記錄',
                'color': '#FF8B94'  # 粉紅色
            },
            {
                'text': '設定',
                'color': '#7C8DA5'  # 灰藍色
            }
        ]
        
        # 創建主圖片
        width = 2500
        height = 1686
        image = Image.new('RGB', (width, height), '#FFFFFF')
        draw = ImageDraw.Draw(image)
        
        # 繪製圓形按鈕
        for i in range(6):
            row = i // 3
            col = i % 3
            
            center_x = 416 + (col * 833)
            center_y = 421 + (row * 843)
            radius = 300
            
            # 繪製主圓形
            circle_bbox = [
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius
            ]
            draw.ellipse(circle_bbox, fill=buttons[i]['color'])
            
            try:
                font = ImageFont.truetype("simsun.ttc", 100)
            except:
                try:
                    font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 100)
                except:
                    font = ImageFont.load_default()
            
            # 繪製文字
            text = buttons[i]['text']
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            
            # 將文字位置上移
            text_y = center_y - 30  # 上移文字位置
            
            # 文字外框
            outline_color = '#000000'
            outline_width = 4
            for offset_x, offset_y in [(x,y) for x in range(-outline_width, outline_width+1) 
                                            for y in range(-outline_width, outline_width+1)]:
                draw.text(
                    (center_x - text_width/2 + offset_x, text_y + offset_y),
                    text,
                    font=font,
                    fill=outline_color
                )
            
            # 主要文字
            draw.text(
                (center_x - text_width/2, text_y),
                text,
                font=font,
                fill='#FFFFFF'
            )
        
        # 保存圖片
        image_path = 'static/images/rich_menu.png'
        image.save(image_path, 'PNG')
        logger.info(f"Rich Menu 圖片已生成: {image_path}")
        
        return image_path
        
    except Exception as e:
        logger.error(f"生成 Rich Menu 圖片時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def send_response_with_rich_menu(event, messages):
    """發送回應並確保顯示 Rich Menu"""
    try:
        # 發送訊息
        line_bot_api.reply_message(event.reply_token, messages)
        
        # 確保 Rich Menu 顯示
        user_id = event.source.user_id
        try:
            # 檢查是否已有 Rich Menu
            current_rich_menu = line_bot_api.get_rich_menu_id_of_user(user_id)
            if not current_rich_menu:
                # 如果沒有，重新設定 Rich Menu
                rich_menu_id = create_rich_menu()
                line_bot_api.link_rich_menu_to_user(user_id, rich_menu_id)
        except Exception as e:
            logger.error(f"設定 Rich Menu 時發生錯誤: {str(e)}")
            
    except Exception as e:
        logger.error(f"發送回應時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())

def create_view_records_rich_menu():
    """建立查看記錄的 Rich Menu"""
    try:
        rich_menu_to_create = RichMenu(
            size=RichMenuSize(width=2500, height=1686),
            selected=True,
            name="查看記錄選單",
            chat_bar_text="查看記錄選單",
            areas=[
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=MessageAction(label='今日記錄', text='查看今日記錄')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                    action=MessageAction(label='本週記錄', text='查看本週記錄')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1666, y=0, width=834, height=843),
                    action=MessageAction(label='搜尋記錄', text='搜尋記錄')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=843, width=833, height=843),
                    action=MessageAction(label='全部記錄', text='查看全部記錄')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=843, width=833, height=843),
                    action=MessageAction(label='返回主選單', text='返回主選單')
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1666, y=843, width=834, height=843),
                    action=MessageAction(label='新增記錄', text='文字記錄')
                )
            ]
        )
        
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu_to_create)
        
        # 生成並上傳圖片
        image_path = create_view_records_rich_menu_image()
        with open(image_path, 'rb') as f:
            line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)
            
        return rich_menu_id
        
    except Exception as e:
        logger.error(f"建立查看記錄 Rich Menu 時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def create_view_records_rich_menu_image():
    """生成查看記錄的 Rich Menu 圖片"""
    try:
        # 建立目錄
        os.makedirs('static/images', exist_ok=True)
        
        # 定義按鈕資訊
        buttons = [
            {
                'text': '今日記錄',
                'color': '#4ECDC4'  # 青綠色
            },
            {
                'text': '本週記錄',
                'color': '#45B7D1'  # 天空藍
            },
            {
                'text': '搜尋記錄',
                'color': '#96CEB4'  # 薄荷綠
            },
            {
                'text': '全部記錄',
                'color': '#FF8B94'  # 粉紅色
            },
            {
                'text': '返回主選單',
                'color': '#7C8DA5'  # 灰藍色
            },
            {
                'text': '新增記錄',
                'color': '#FF6B6B'  # 溫暖的紅色
            }
        ]
        
        # 創建主圖片
        width = 2500
        height = 1686
        image = Image.new('RGB', (width, height), '#FFFFFF')
        draw = ImageDraw.Draw(image)
        
        # 繪製按鈕
        for i in range(6):
            row = i // 3
            col = i % 3
            
            center_x = 416 + (col * 833)
            center_y = 421 + (row * 843)
            radius = 300
            
            # 繪製主圓形
            circle_bbox = [
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius
            ]
            draw.ellipse(circle_bbox, fill=buttons[i]['color'])
            
            try:
                font = ImageFont.truetype("simsun.ttc", 100)
            except:
                try:
                    font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 100)
                except:
                    font = ImageFont.load_default()
            
            # 繪製文字
            text = buttons[i]['text']
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            
            # 將文字位置上移
            text_y = center_y - 30
            
            # 文字外框
            outline_color = '#000000'
            outline_width = 4
            for offset_x, offset_y in [(x,y) for x in range(-outline_width, outline_width+1) 
                                            for y in range(-outline_width, outline_width+1)]:
                draw.text(
                    (center_x - text_width/2 + offset_x, text_y + offset_y),
                    text,
                    font=font,
                    fill=outline_color
                )
            
            # 主要文字
            draw.text(
                (center_x - text_width/2, text_y),
                text,
                font=font,
                fill='#FFFFFF'
            )
        
        # 保存圖片
        image_path = 'static/images/view_records_rich_menu.png'
        image.save(image_path, 'PNG')
        
        return image_path
        
    except Exception as e:
        logger.error(f"生成查看記錄 Rich Menu 圖片時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    # 確保使用環境變數中的 PORT
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port)

# 檢查 Rich Menu 狀態
rich_menu_list = line_bot_api.get_rich_menu_list()
for menu in rich_menu_list:
    logger.info(f"Found Rich Menu: {menu.rich_menu_id}")

# 檢查預設 Rich Menu
default_menu = line_bot_api.get_default_rich_menu()
logger.info(f"Default Rich Menu: {default_menu}") 