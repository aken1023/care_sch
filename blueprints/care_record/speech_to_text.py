import speech_recognition as sr
from pydub import AudioSegment
import os
import time
import sys
from datetime import datetime
from openai import OpenAI
import httpx
import threading
import itertools
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 使用環境變數
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    http_client=httpx.Client(
        timeout=httpx.Timeout(300.0, connect=60.0),  # 增加超時時間到 300 秒
        follow_redirects=True,
        transport=httpx.HTTPTransport(retries=3)  # 使用正確的重試機制
    )
)

# 進度動畫類
class ProgressAnimation:
    def __init__(self, description="處理中"):
        self.description = description
        self.done = False
        self.animation = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])

    def animate(self):
        while not self.done:
            sys.stdout.write(f'\r{self.description} {next(self.animation)} ')
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * (len(self.description) + 2) + '\r')
        sys.stdout.flush()

    def start(self):
        self.thread = threading.Thread(target=self.animate)
        self.thread.start()

    def stop(self):
        self.done = True
        if hasattr(self, 'thread'):
            self.thread.join()

def check_dependencies():
    print("=== 檢查系統環境 ===")
    try:
        print("檢查 FFmpeg...")
        from pydub.utils import which
        if which("ffmpeg") is None:
            print("錯誤：找不到 FFmpeg！")
            print("請確保已安裝 FFmpeg 並添加到系統環境變數中")
            print("下載地址：https://ffmpeg.org/download.html")
            return False
        print("FFmpeg 檢查通過")
        
        # 檢查 OpenAI API Key
        if not client.api_key:
            print("錯誤：找不到 OpenAI API Key")
            return False
        print("OpenAI API Key 檢查通過")
        
        return True
    except Exception as e:
        print(f"環境檢查時發生錯誤：{str(e)}")
        return False

def convert_m4a_to_wav(m4a_path):
    print("\n=== 開始進行音訊檔案轉換 ===")
    print(f"原始檔案：{m4a_path}")
    
    # 檢查檔案是否存在
    if not os.path.exists(m4a_path):
        raise FileNotFoundError(f"找不到音訊檔案：{m4a_path}")
    
    try:
        progress = ProgressAnimation("正在讀取音訊檔案")
        progress.start()
        
        # 讀取M4A檔案
        audio = AudioSegment.from_file(m4a_path, format="m4a")
        
        progress.stop()
        print(f"\n音訊檔案資訊：")
        duration_seconds = len(audio) / 1000
        print(f"- 時長：{duration_seconds:.2f} 秒")
        print(f"- 聲道數：{audio.channels}")
        print(f"- 取樣率：{audio.frame_rate} Hz")
        
        # 轉換為WAV格式
        progress = ProgressAnimation("正在轉換為WAV格式")
        progress.start()
        
        wav_path = "temp_audio.wav"
        audio.export(wav_path, format="wav")
        
        progress.stop()
        print(f"\nWAV檔案已儲存至：{wav_path}")
        
        return wav_path
        
    except Exception as e:
        if 'progress' in locals():
            progress.stop()
        print(f"\n音訊轉換過程中發生錯誤：{str(e)}")
        print("可能原因：")
        print("1. FFmpeg 未正確安裝")
        print("2. 音訊檔案格式不正確或已損壞")
        print("3. 系統權限不足")
        raise

def transcribe_with_whisper(audio_path):
    """使用 OpenAI Whisper 模型進行語音辨識"""
    try:
        with open(audio_path, "rb") as audio_file:
            progress = ProgressAnimation("正在使用 OpenAI Whisper 進行語音辨識")
            progress.start()
            
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="zh"
            )
            
            progress.stop()
            return response.text
    except Exception as e:
        if 'progress' in locals():
            progress.stop()
        print(f"\nWhisper 辨識錯誤：{str(e)}")
        raise

def generate_care_report(transcribed_text):
    """使用 OpenAI 生成照護報告"""
    max_retries = 3
    retry_delay = 5  # 重試延遲時間（秒）
    
    for attempt in range(max_retries):
        try:
            progress = ProgressAnimation("正在生成照護報告")
            progress.start()
            
            prompt = f"""
請根據以下的語音轉錄內容，生成一份結構完整的照護報告。

報告格式要求：
1. 基本資訊
   - 記錄時間：自動生成
   - 記錄護理師：從內容識別或標註「未指明」

2. 病患狀況摘要
   - 主要症狀和體徵
   - 生命徵象（若有提及）
   - 意識狀態
   - 整體狀況評估

3. 照護執行紀錄
   - 已完成的照護項目（條列式）
   - 用藥紀錄（若有）
   - 特殊處置（若有）
   - 飲食/營養狀況

4. 特殊觀察重點
   - 需要持續追蹤的症狀
   - 異常指標
   - 行為/情緒觀察
   - 風險評估

5. 後續照護建議
   - 待執行事項
   - 注意事項
   - 交班重點
   - 後續追蹤重點

請使用以下格式：
# 照護紀錄報告
[自動帶入現在時間]

## 一、基本資訊
[內容]

## 二、病患狀況摘要
[內容]

## 三、照護執行紀錄
[內容]

## 四、特殊觀察重點
[內容]

## 五、後續照護建議
[內容]

轉錄內容：
{transcribed_text}

請以專業的醫療照護報告格式輸出，使用繁體中文，確保內容清晰易讀，重點明確。如果某些資訊未在轉錄內容中提及，請標註「未提供相關資訊」。
"""
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "你是一位專業的醫療照護報告撰寫者，擅長將口語記錄整理成結構化的照護報告。你會確保報告的專業性、完整性和可讀性。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                timeout=300  # 設定 API 調用超時時間為 300 秒
            )
            
            progress.stop()
            return response.choices[0].message.content
            
        except Exception as e:
            progress.stop()
            print(f"\n第 {attempt + 1} 次嘗試生成報告失敗：{str(e)}")
            if attempt < max_retries - 1:
                print(f"等待 {retry_delay} 秒後重試...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指數退避
            else:
                print("\n已達到最大重試次數，生成報告失敗")
                raise

def speech_to_text(audio_path):
    try:
        print("\n=== 開始進行語音轉文字 ===")
        
        # 將M4A轉換為WAV檔案
        wav_path = convert_m4a_to_wav(audio_path)
        
        print("\n開始進行語音辨識...")
        start_time = time.time()
        
        # 使用 Whisper 進行辨識
        transcribed_text = transcribe_with_whisper(wav_path)
        
        print("\n=== 語音辨識完成 ===")
        print("\n原始轉換結果：")
        print("-" * 50)
        print(transcribed_text)
        print("-" * 50)
        
        # 使用 OpenAI 生成照護報告
        care_report = generate_care_report(transcribed_text)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print("\n=== 報告生成完成 ===")
        print(f"總處理時間：{processing_time:.2f} 秒")
        print("\n照護報告：")
        print("-" * 50)
        print(care_report)
        print("-" * 50)
        
        # 取得當前時間作為檔案名稱的一部分
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 將結果寫入文字檔
        progress = ProgressAnimation("正在儲存報告")
        progress.start()
        
        output_text_file = f"照護報告_{timestamp}.txt"
        with open(output_text_file, "w", encoding="utf-8") as f:
            f.write(f"原始檔案：{audio_path}\n")
            f.write(f"處理時間：{processing_time:.2f} 秒\n")
            f.write("-" * 50 + "\n\n")
            f.write("=== 原始轉錄內容 ===\n")
            f.write(transcribed_text + "\n\n")
            f.write("=== 整理後的照護報告 ===\n")
            f.write(care_report)
        
        progress.stop()
        print(f"\n結果已儲存至：{os.path.abspath(output_text_file)}")
        
    except Exception as e:
        print(f"發生錯誤：{str(e)}")
        print("錯誤類型：", type(e).__name__)
        import traceback
        print("詳細錯誤訊息：")
        print(traceback.format_exc())
    finally:
        # 清理暫時檔案
        progress = ProgressAnimation("正在清理暫時檔案")
        progress.start()
        if os.path.exists(wav_path):
            os.remove(wav_path)
        progress.stop()
        print("\n處理完成！")

if __name__ == "__main__":
    print("=== 語音轉文字暨照護報告生成程式啟動 ===")
    print("Python版本：", sys.version)
    print("目前工作目錄：", os.getcwd())
    
    # 檢查必要的環境依賴
    if not check_dependencies():
        print("環境檢查失敗，程式終止")
        sys.exit(1)
    
    # 設定音訊檔案路徑
    audio_file = r"C:\Users\aken1\OneDrive\文档\112091522.m4a"
    print(f"\n處理檔案：{audio_file}")
    
    # 執行轉換和報告生成
    speech_to_text(audio_file)