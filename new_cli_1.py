import cv2
import socket
import numpy as np
import threading
from cryptography.fernet import Fernet
import requests
import pyaudio  # Добавлен для работы со звуком
import time

# --- НАСТРОЙКИ ---
SERVER_IP = "127.0.0.1"
VIDEO_SERVER_PORT = 6000
AUDIO_SERVER_PORT = 7000

# Порты, на которые серверы будут пересылать нам данные ОБРАТНО
MY_VIDEO_PORT = 5005
MY_AUDIO_PORT = 5005 # Для простоты можно использовать разные или один с разными протоколами

# Настройки аудио
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000 # Whisper любит 16кГц

def get_session_key(user_id, room_id):
    url = f"http://{SERVER_IP}:8000/auth/get_token"
    payload = {"user_id": user_id, "room_id": room_id}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()['session_key'].encode()
    except Exception as e:
        print(f"Ошибка сети: {e}")
    return None

def receive_video(cipher):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", MY_VIDEO_PORT))
    print(f"Ожидание видео на {MY_VIDEO_PORT}...")
    while True:
        try:
            encrypted_packet, _ = sock.recvfrom(65536)
            decrypted_data = cipher.decrypt(encrypted_packet)
            data = np.frombuffer(decrypted_data, dtype=np.uint8)
            frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if frame is not None:
                cv2.imshow("OTHER CAM 1", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
        except Exception as e:
            print(f"Ошибка видео-приема: {e}")

def send_video(cipher):
    cap = cv2.VideoCapture(0)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Отправка видео на {SERVER_IP}:{VIDEO_SERVER_PORT}...")
    while True:
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.resize(frame, (320, 240))
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        encrypted_buffer = cipher.encrypt(buffer.tobytes())
        if len(encrypted_buffer) < 65535:
            sock.sendto(encrypted_buffer, (SERVER_IP, VIDEO_SERVER_PORT))
        cv2.imshow("MY CAM 1", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release()

def receive_audio(cipher):
    """Прием аудио от аудио-сервера и воспроизведение"""
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", MY_AUDIO_PORT))
    print(f"Ожидание аудио на {MY_AUDIO_PORT}...")
    
    while True:
        try:
            encrypted_packet, _ = sock.recvfrom(65536)
            decrypted_audio = cipher.decrypt(encrypted_packet)
            stream.write(decrypted_audio)
        except Exception as e:
            print(f"Ошибка аудио-приема: {e}")

def send_audio(cipher):
    """Захват микрофона, шифрование и отправка на аудио-сервер"""
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, 
                        channels=CHANNELS, 
                        rate=RATE, 
                        input=True, 
                        frames_per_buffer=CHUNK)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"Отправка аудио на {SERVER_IP}:{AUDIO_SERVER_PORT}...")
        
        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                encrypted_audio = cipher.encrypt(data)
                sock.sendto(encrypted_audio, (SERVER_IP, AUDIO_SERVER_PORT))
            except Exception as e:
                print(f"Ошибка при чтении/отправке аудио: {e}")
                break
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ЗАПУСКА АУДИО: {e}")
        import traceback
        traceback.print_exc() # Это выведет полную причину падения в консоль

if __name__ == "__main__":
    u_id = input("Введите ваш ID: ")
    r_id = input("Введите ID комнаты: ")
    
    key = get_session_key(u_id, r_id)
    if key:
        cipher = Fernet(key)
        
        # Создаем 4 потока для полноценной связи
        threads = [
            threading.Thread(target=receive_video, args=(cipher,)),
            threading.Thread(target=send_video, args=(cipher,)),
            threading.Thread(target=receive_audio, args=(cipher,)),
            threading.Thread(target=send_audio, args=(cipher,))
        ]
        
        for t in threads:
            t.daemon = True # Чтобы потоки закрылись при выходе из main
            t.start()
        
        print("Система запущена. Нажмите Ctrl+C для выхода.")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            print("Завершение работы...")
    else:
        print("Доступ запрещен.")