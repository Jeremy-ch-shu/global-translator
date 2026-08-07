import pyaudio
import numpy as np
from faster_whisper import WhisperModel
from loguru import logger
import threading
import queue

class LiveCaption:
    """实时语音识别与翻译"""
    
    def __init__(self, model_size: str = 'base', device: str = 'cpu'):
        """
        model_size: tiny, base, small, medium, large
        """
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        self.audio_queue = queue.Queue()
        self.is_running = False
        self.translation_callback = None
    
    def start_capture(self, callback=None):
        """开始捕获系统音频"""
        self.is_running = True
        self.translation_callback = callback
        
        # Windows使用WASAPI loopback捕获系统音频[reference:26]
        # 这里使用PyAudio作为示例
        self.audio_thread = threading.Thread(target=self._audio_loop)
        self.audio_thread.start()
        
        # 启动识别线程
        self.recognition_thread = threading.Thread(target=self._recognition_loop)
        self.recognition_thread.start()
        
        logger.info("实时语音识别已启动")
    
    def _audio_loop(self):
        """音频捕获循环"""
        p = pyaudio.PyAudio()
        
        # 使用WASAPI loopback捕获系统音频[reference:27]
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024,
            input_host_api_specific_stream_info=p.get_host_api_info_by_index(0)
        )
        
        while self.is_running:
            data = stream.read(1024, exception_on_overflow=False)
            audio_array = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            self.audio_queue.put(audio_array)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    def _recognition_loop(self):
        """语音识别循环"""
        audio_buffer = []
        
        while self.is_running:
            try:
                chunk = self.audio_queue.get(timeout=0.1)
                audio_buffer.append(chunk)
                
                # 积累足够音频后识别（约2秒）
                if len(audio_buffer) >= 30:  # 30 * 1024 samples
                    audio_data = np.concatenate(audio_buffer)
                    audio_buffer = []
                    
                    # 使用Whisper识别[reference:28]
                    segments, _ = self.model.transcribe(audio_data, language="en")
                    
                    for segment in segments:
                        text = segment.text
                        logger.info(f"识别: {text}")
                        
                        if self.translation_callback:
                            self.translation_callback(text)
                            
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"识别错误: {e}")
    
    def stop(self):
        """停止捕获"""
        self.is_running = False
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join(timeout=2)
        if hasattr(self, 'recognition_thread'):
            self.recognition_thread.join(timeout=2)
        logger.info("实时语音识别已停止")