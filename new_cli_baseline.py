import cv2
import socket
import numpy as np
import threading
import requests
import pyaudio
from cryptography.fernet import Fernet

# =============================================================================
# НАСТРОЙКИ СЕТИ (Для теста на одном ПК)
# =============================================================================
# 1. Главный сервер (Авторизация)
MAIN_SERVER_URL = "http://127.0.0.1:8000"

# 2. Видео-сервер (Аналитика лиц)
VIDEO_SERVER_IP = "127.0.0.1"
VIDEO_SERVER_PORT = 6000

# 3. Аудио-сервер (STT + Цензура)
AUDIO_SERVER_IP = "127.0.0.1"
AUDIO_SERVER_PORT = 7000

# 4. Прямая связь с собеседником (Куда прилетают ответы от серверов)
# Если ты Клиент 1: TARGET_PORT_VIDEO=5005, MY_PORT_VIDEO=5006
# Если ты Клиент 2: TARGET_PORT_VIDEO=5006, MY_PORT_VIDEO=5005
TARGET_IP = "127.0.0.1"
MY_PORT_VIDEO = 5006   # Мой порт для приема видео
TARGET_PORT_VIDEO = 5005 # Порт собеседника для видео

MY_PORT_AUDIO = 7006   # Мой порт для приема аудио
TARGET_PORT_AUDIO = 7005 # Порт собеседника для аудио

# Настройки звука
CHUNK = 1024            # Размер порции аудио-данных
FORMAT = pyaudio.paInt16 # 16-битный звук
CHANNELS = 1            # Моно
RATE = 44100            # Частота дискретизации 44.1 кГц
# =============================================================================

def get_session_key(user_id, room_id):
    """Запрос ключа шифрования у главного сервера"""
    url = f"{MAIN_SERVER_URL}/auth/get_token"
    payload = {"user_id": user_id, "room_id": room_id}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data['session_key'].encode()
    except Exception as e:
        print(f"Ошибка сети: {e}")
    return None

# --- ВИДЕО БЛОК ---

def send_video(cipher):
    """Захват, сжатие, шифрование и отправка видео на ВИДЕО-СЕРВЕР"""
    cap = cv2.VideoCapture(0)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("🎥 Видео-поток отправлен на анализ...")
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.resize(frame, (320, 240))
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        
        # Шифруем и отправляем на VIDEO_SERVER (порт 6000)
        encrypted_buffer = cipher.encrypt(buffer.tobytes())
        sock.sendto(encrypted_buffer, (VIDEO_SERVER_IP, VIDEO_SERVER_PORT))
        
        cv2.imshow("My Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()

def receive_video(cipher):
    """Прием, расшифровка и отображение видео от ВИДЕО-СЕРВЕРА"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", MY_PORT_VIDEO))
    print(f"📺 Ожидание видео на порту {MY_PORT_VIDEO}...")
    
    while True:
        try:
            data, _ = sock.recvfrom(65536)
            decrypted_data = cipher.decrypt(data)
            frame = cv2.imdecode(np.frombuffer(decrypted_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                cv2.imshow("Partner Video (Analyzed)", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
        except: pass

# --- АУДИО БЛОК ---

def send_audio(cipher):
    """Захват звука, шифрование и отправка на АУДИО-СЕРВЕР"""
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("🎤 Аудио-поток отправлен на анализ...")
    
    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            # Шифруем звук и отправляем на AUDIO_SERVER (порт 7000)
            encrypted_audio = cipher.encrypt(data)
            sock.sendto(encrypted_audio, (AUDIO_SERVER_IP, AUDIO_SERVER_PORT))
        except Exception as e:
            print(f"Ошибка записи звука: {e}")
            break
    
    stream.stop_stream()
    stream.close()
    p.terminate()

def receive_audio(cipher):
    """Прием, расшифровка и воспроизведение аудио от АУДИО-СЕРВЕРА"""
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", MY_PORT_AUDIO))
    print(f"🎧 Ожидание аудио на порту {MY_PORT_AUDIO}...")
    
    while True:
        try:
            data, _ = sock.recvfrom(65536)
            decrypted_audio = cipher.decrypt(data)
            stream.write(decrypted_audio) # Воспроизведение в динамики
        except: pass

# --- ГЛАВНЫЙ ЗАПУСК ---

if __name__ == "__main__":
    u_id = input("Введите ваш ID: ")
    r_id = input("Введите ID комнаты: ")
    
    key = get_session_key(u_id, r_id)
    
    if key:
        cipher = Fernet(key)
        print("✅ Авторизация успешна! Запуск всех потоков...")
        
        # Создаем потоки для видео
        t_v_send = threading.Thread(target=send_video, args=(cipher,))
        t_v_recv = threading.Thread(target=receive_video, args=(cipher,))
        
        # Создаем потоки для аудио
        t_a_send = threading.Thread(target=send_audio, args=(cipher,))
        t_a_recv = threading.Thread(target=receive_audio, args=(cipher,))
        
        # Запускаем всё одновременно
        t_v_send.start()
        t_v_recv.start()
        t_a_send.start()
        t_a_recv.start()
        
        print("Система работает. Нажмите 'q' в окне видео для выхода.")
        t_v_send.join()
    else:
        print("❌ Доступ запрещен.")