import socket
import json
import threading

# Настройки сети
UDP_IP = "172.16.248.189" # Замените на IP сервера (который узнали через ping)
UDP_PORT = 9000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
user_token = None # Сюда сохраним токен после регистрации

# Функция для фонового приема сообщений
def receive_messages():
    global user_token
    print("[Система] Поток приема сообщений запущен...")
    while True:
        try:
            # Ждем данные от сервера
            data, addr = sock.recvfrom(65535) 
            message_json = json.loads(data.decode('utf-8'))
            
            # Очищаем строку ввода, чтобы сообщение не перемешалось с текстом ввода
            # \r возвращает курсор в начало строки
            print(f"\n\n[Новое сообщение] {message_json.get('from', 'Unknown')}: {message_json.get('text', '')}")
            print("Кому отправить (ник): ", end="", flush=True)
            
        except Exception as e:
            print(f"\n[Ошибка приема]: {e}")

def send_and_receive(data):
    """Отправка данных и ожидание подтверждения от сервера"""
    try:
        json_bytes = json.dumps(data).encode('utf-8')
        sock.sendto(json_bytes, (UDP_IP, UDP_PORT))
        
        # Для регистрации нам все еще нужно дождаться ответа (токена)
        # Но для обычных сообщений сервер может просто ответить "ok"
        sock.settimeout(None) 
        data_res, addr = sock.recvfrom(65535)
        return json.loads(data_res.decode('utf-8'))
    except socket.timeout:
        return None
    except Exception as e:
        print(f"Ошибка сети: {e}")
        return None

# ================= ЭТАП 1: РЕГИСТРАЦИЯ =================
my_nick = input("Введите ваш никнейм для регистрации: ")
reg_data = {"cmd": "register", "nick": my_nick}

print("Регистрация...")
reg_response = send_and_receive(reg_data)

if reg_response and "token" in reg_response:
    user_token = reg_response["token"]
    print(f"Регистрация успешна! Ваш токен: {user_token}")
else:
    print("Не удалось зарегистрироваться.")
    exit()

# ================= ЭТАП 2: ЗАПУСК ФОНОВОГО ПРИЕМА =================
# Создаем отдельный поток, который будет работать параллельно с основным циклом
receiver_thread = threading.Thread(target=receive_messages, daemon=True)
receiver_thread.start()

# ================= ЭТАП 3: ОБМЕН СООБЩЕНИЯМИ =================
print("\n--- Режим чата запущен ---")
print("Для выхода введите 'exit'")

while True:
    target_nick = input("\nКому отправить (ник): ")
    if target_nick.lower() == 'exit':
        break
        
    msg_text = input("Введите текст сообщения: ")
    if msg_text.lower() == 'exit':
        break

    chat_data = {
        "cmd": "send",
        "token": user_token,
        "to": target_nick,
        "text": msg_text
    }

    # Отправляем сообщение. Мы не ждем ответа через send_and_receive, 
    # так как подтверждение или ответ придет в поток receive_messages
    sock.sendto(json.dumps(chat_data).encode('utf-8'), (UDP_IP, UDP_PORT))
    print("Отправлено!")

print("Завершение работы.")
