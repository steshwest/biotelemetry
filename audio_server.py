import socket
import numpy as np
import threading
import requests
import whisper
import ollama
from cryptography.fernet import Fernet
import time

# --- НАСТРОЙКИ ---
MAIN_SERVER_URL = "http://127.0.0.1:8000"
LISTEN_PORT = 7000        # Порт для приема аудио от клиента
FORWARD_PORT = 7005       # Порт клиента-получателя
FORWARD_IP = "127.0.0.1"  # IP клиента-получателя

# Загружаем модель Whisper (tiny - самая быстрая)
print("Загрузка Whisper...")
stt_model = whisper.load_model("tiny")

class AudioAnalyticsServer:
    def __init__(self):
        self.rooms_keys = {} 
        self.audio_buffer = [] # Сюда копим данные для анализа
        self.buffer_lock = threading.Lock() # Чтобы потоки не дрались за буфер

    def register_room(self, room_id, user_id):
        try:
            url = f"{MAIN_SERVER_URL}/auth/get_token"
            payload = {"user_id": user_id, "room_id": room_id}
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                key = response.json()['session_key'].encode()
                self.rooms_keys[room_id] = Fernet(key)
                print(f"✅ Ключ аудио-комнаты {room_id} получен!")
                return True
        except Exception as e:
            print(f"❌ Ошибка связи: {e}")
        return False

    def analyze_speech(self):
        """Фоновый поток для Whisper и Ollama"""
        print("🤖 Аналитик речи запущен...")
        while True:
            time.sleep(10) # Ждем 10 секунд, пока накопится аудио
            
            with self.buffer_lock:
                if not self.audio_buffer:
                    continue
                # Копируем данные и очищаем буфер
                audio_data = np.concatenate(self.audio_buffer)
                self.audio_buffer = []
            
            try:
                # 1. Whisper: Голос -> Текст
                # (В реальном коде тут нужно сохранить массив в .wav файл, так как whisper ждет путь к файлу)
                # Для упрощения имитируем передачу массива данных
                print("🎙️ Обработка аудио-пакета через Whisper...")
                # Здесь должен быть вызов stt_model.transcribe()
                text = "Тестовая транскрипция: Пациент живет в городе Москва, телефон 89991234567" 
                
                # 2. Ollama: Текст -> Цензура
                print("🧠 Анализ текста через Ollama...")
                response = ollama.chat(model='phi3', messages=[
                    {'role': 'system', 'content': 'Ты — медицинский цензор. Замени все персональные данные (имена, города, телефоны) на [DATA REDACTED]. Замени все упоминания слова пациент и его производных на [Подопытный 30821]. Отвечай только исправленным текстом.'},
                    {'role': 'user', 'content': text},
                ])
                
                clean_text = response['message']['content']
                print(f"📄 Оригинал: {text}")
                print(f"✨ Очищено: {clean_text}")
                
            except Exception as e:
                print(f"⚠️ Ошибка анализа: {e}")

    def process_audio(self):
        """Поток проксирования звука в реальном времени"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", LISTEN_PORT))
        print(f"🚀 Audio Server запущен на порту {LISTEN_PORT}...")

        while True:
            try:
                data, addr = sock.recvfrom(65536)
                print(f"📦 Получен пакет от {addr}, размер: {len(data)} байт")
                if not self.rooms_keys: continue
                cipher = list(self.rooms_keys.values())[0]
                
                # Расшифровка
                # decrypted_audio = cipher.decrypt(data)  <-- ЗАКОММЕНТИРУЙТЕ ЭТО
                decrypted_audio = data # <-- ДОБАВЬТЕ ЭТО (временно считаем данные расшифрованными)
                
                # Сохраняем в буфер для анализа (поток-аналитик заберет это позже)
                with self.buffer_lock:
                    self.audio_buffer.append(np.frombuffer(decrypted_audio, dtype=np.int16))
                
                # Сразу пересылаем расшифрованное аудио (или снова шифруем для клиента)
                encrypted_audio = cipher.encrypt(decrypted_audio)
                sock.sendto(encrypted_audio, (FORWARD_IP, FORWARD_PORT))
                
            except Exception as e:
                print(f"⚠️ Ошибка аудио-потока: {e}")

if __name__ == "__main__":
    server = AudioAnalyticsServer()
    r_id = input("Введите ID комнаты: ")
    u_id = input("Введите ваш ID: ")
    
    if server.register_room(r_id, u_id):
        # Запускаем два потока: один для пересылки, другой для анализа
        t_proxy = threading.Thread(target=server.process_audio)
        t_analyst = threading.Thread(target=server.analyze_speech)
        
        t_proxy.start()
        t_analyst.start()