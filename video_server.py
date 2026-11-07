import cv2
import socket
import numpy as np
import requests
from cryptography.fernet import Fernet

# --- НАСТРОЙКИ ---
MAIN_SERVER_URL = "http://127.0.0.1:8000"
LISTEN_PORT = 6000        # Порт, на который приходят данные от клиента
FORWARD_PORT = 5005       # Порт клиента-получателя (Пациента)
FORWARD_IP = "127.0.0.1"  # IP клиента-получателя

# ПРОВЕРКА OpenCV: Загружаем детектор лиц сразу при старте
try:
    # Загружаем стандартный файл каскадов OpenCV
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if face_cascade.empty():
        raise IOError("Не удалось загрузить файл каскадов. Проверьте установку opencv-python.")
    print("✅ Детектор лиц успешно загружен!")
except Exception as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
    exit()

class VideoAnalyticsServer:
    def __init__(self):
        self.rooms_keys = {} # {room_id: cipher_object}

    def register_room(self, room_id, user_id):
        """Запрашивает ключ комнаты у главного сервера через API"""
        try:
            url = f"{MAIN_SERVER_URL}/auth/get_token"
            payload = {"user_id": user_id, "room_id": room_id}
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                key = response.json()['session_key'].encode()
                self.rooms_keys[room_id] = Fernet(key)
                print(f"✅ Ключ для комнаты {room_id} получен!")
                return True
        except Exception as e:
            print(f"❌ Ошибка связи с главным сервером: {e}")
        return False

    def process_stream(self):
        """Цикл приема, анализа и пересылки видео"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", LISTEN_PORT))
        print(f"🚀 Video Server запущен. Слушаю порт {LISTEN_PORT}...")
        print(f"Пересылаю данные на {FORWARD_IP}:{FORWARD_PORT}")

        while True:
            try:
                # 1. Принимаем зашифрованный пакет от клиента
                data, addr = sock.recvfrom(65536)
                
                if not self.rooms_keys:
                    continue
                
                # Берем первый доступный ключ для теста
                cipher = list(self.rooms_keys.values())[0]
                
                # 2. Расшифровка
                decrypted_data = cipher.decrypt(data)
                frame = cv2.imdecode(np.frombuffer(decrypted_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                
                # В случае ошибки имдекода (например, битый пакет)
                if frame is None:
                    continue
                
                # 3. АНАЛИЗ: Трекинг лица через Haar Cascades
                # Переводим в ч/б (серый цвет), так как каскады работают только с ним
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                
                # Рисуем рамки вокруг всех найденных лиц
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, "Face Detected", (x, y - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # 4. Пересылка результата дальше
                _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                encrypted_buffer = cipher.encrypt(buffer.tobytes())
                sock.sendto(encrypted_buffer, (FORWARD_IP, FORWARD_PORT))
                
            except Exception as e:
                # Печатаем ошибку, но не останавливаем сервер
                print(f"⚠️ Ошибка при обработке кадра: {e}")

if __name__ == "__main__":
    server = VideoAnalyticsServer()
    
    print("--- Авторизация Video Server ---")
    r_id = input("Введите ID комнаты для анализа: ")
    u_id = input("Введите ваш ID (например, video_admin): ")
    
    if server.register_room(r_id, u_id):
        server.process_stream()
    else:
        print("❌ Ошибка: Не удалось авторизоваться на главном сервере. Проверьте, запущен ли server.py")