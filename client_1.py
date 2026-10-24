import cv2
import socket
import numpy as np
import threading
from cryptography.fernet import Fernet
import requests # Добавь в импорты

# --- НАСТРОЙКИ ---
# В реальной жизни этот ключ должен приходить с вашего сервера вместе с токеном!
# Для теста создадим один общий ключ для обоих клиентов.
# Чтобы сгенерировать новый ключ, можно использовать Fernet.generate_key()
SECRET_KEY = b'u6X_D7C_7Z6S4hL6p-Xp8j_C8Y_C7G5J6vS8Z8_L5k0=' 
cipher = Fernet(SECRET_KEY)

TARGET_IP = "10.168.180.181" # id of cli_2
TARGET_PORT = 5005
MY_PORT = 5006

def get_session_key(user_id, room_id):
    """Запрос ключа шифрования у сервера"""
    url = f"http://192.168.56.1:8000/auth/get_token" # change to TARGET_IP серверного пк
    payload = {"user_id": user_id, "room_id": room_id}
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        # Предположим, сервер теперь возвращает {'token': '...', 'session_key': '...'}
        return data['session_key'].encode() 
    else:
        print("Ошибка авторизации! Ключ не получен.")
        return None

def receive_video(cipher):
    """Прием, расшифровка и отображение видео"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", MY_PORT))
    
    print(f"Ожидание ЗАШИФРОВАННОГО видео на порту {MY_PORT}...")
    
    while True:
        try:
            # 1. Получаем зашифрованный пакет
            encrypted_packet, _ = sock.recvfrom(65536)
            
            # 2. РАСШИФРОВКА
            # Если ключ не совпадет или данные будут повреждены, возникнет ошибка
            decrypted_data = cipher.decrypt(encrypted_packet)
            
            # 3. Декодирование из байтов в изображение
            data = np.frombuffer(decrypted_data, dtype=np.uint8)
            frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
            
            if frame is not None:
                cv2.imshow("OTHER CAM 1", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except Exception as e:
            print(f"Ошибка расшифровки или приема: {e}")
            # Если пришел пакет от «хакера» без ключа, программа не вылетит, 
            # а просто проигнорирует этот пакет.

def send_video(cipher):
    """Захват, сжатие, шифрование и отправка видео"""
    cap = cv2.VideoCapture(0)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Отправка ЗАШИФРОВАННОГО видео на {TARGET_IP}:{TARGET_PORT}...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.resize(frame, (320, 240))
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        
        # --- ШИФРОВАНИЕ ---
        # Превращаем обычные байты картинки в зашифрованный криптограмм
        encrypted_buffer = cipher.encrypt(buffer.tobytes())
        
        # Отправляем зашифрованные данные
        # Внимание: шифрование немного увеличивает размер пакета
        if len(encrypted_buffer) < 65535:
            sock.sendto(encrypted_buffer, (TARGET_IP, TARGET_PORT))
        else:
            print("Кадр слишком большой даже после сжатия!")
        
        cv2.imshow("MY CAM 1", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Спрашиваем у пользователя данные для входа
    u_id = input("Введите ваш ID: ")
    r_id = input("Введите ID комнаты: ")
    
    key = get_session_key(u_id, r_id)
    
    if key:
        # Теперь создаем шифратор с полученным от сервера ключом!
        cipher = Fernet(key) 
        
        t1 = threading.Thread(target=receive_video, args=(cipher,))
        t2 = threading.Thread(target=send_video, args=(cipher,))
    
        t1.start()
        t2.start()
    
        t1.join()
        t2.join()
    else:
        print("Доступ запрещен. Программа завершена.")