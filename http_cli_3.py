import http.client
import json
import threading
import time
import sys

HOST = "172.20.10.2"
PORT = 8000
user_token = None

def make_request(endpoint, data_dict):
    """
    Функция, которая берет СЛОВАРЬ, конвертирует его в JSON-байты 
    и отправляет на сервер.
    """
    try:
        conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
        
        # --- ПРОЦЕСС КОНВЕРТАЦИИ ---
        # 1. Превращаем словарь (dict) в JSON-строку (str)
        json_string = json.dumps(data_dict) 
        
        # 2. Превращаем строку (str) в байты (bytes), так как сеть работает с байтами
        json_bytes = json_string.encode('utf-8')
        # ---------------------------

        # Заголовки: сообщаем серверу, что отправляем именно JSON
        headers = {
            'Content-Type': 'application/json',
            'Content-Length': str(len(json_bytes))
        }
        
        # Отправляем именно БАЙТЫ (json_bytes)
        conn.request("POST", endpoint, body=json_bytes, headers=headers)
        
        response = conn.getresponse()
        res_data = response.read().decode('utf-8')
        conn.close()
        
        if response.status == 200:
            return json.loads(res_data)
        else:
            print(f"Ошибка сервера {response.status}: {res_data}")
            return None
    except Exception as e:
        print(f"Ошибка сети: {e}")
        return None

def receive_messages():
    global user_token
    while True:
        if user_token:
            # Передаем словарь, функция make_request сама его конвертирует в JSON
            res = make_request("/inbox", {"token": user_token})
            if res and isinstance(res, list):
                for msg in res:
                    sys.stdout.write(f"\r\x1b[K[Новое сообщение] {msg.get('from')}: {msg.get('text')}\n")
                    sys.stdout.write("Кому отправить (ник): ")
                    sys.stdout.flush()
        time.sleep(2)

# ================= ЭТАП 1: РЕГИСТРАЦИЯ =================
my_nick = input("Введите ваш никнейм: ").strip()
# Создаем обычный словарь
reg_data = {"cmd": "register", "nick": my_nick}

print("Регистрация...")
# make_request внутри сделает: reg_data -> JSON-строка -> байты
reg_res = make_request("/register", reg_data)

if reg_res and "token" in reg_res:
    user_token = reg_res["token"]
    print(f"Успешно! Токен: {user_token}")
else:
    print("Ошибка регистрации.")
    sys.exit()

# ================= ЭТАП 2: ЗАПУСК ПРИЕМА =================
receiver_thread = threading.Thread(target=receive_messages, daemon=True)
receiver_thread.start()

# ================= ЭТАП 3: ОТПРАВКА =================
print("\n--- Режим HTTP-чата запущен ---")
while True:
    target_nick = input("\nКому отправить (ник): ").strip()
    if target_nick.lower() == 'exit': break
        
    msg_text = input("Введите текст: ").strip()
    if msg_text.lower() == 'exit': break

    # Создаем обычный словарь
    send_data = {
        "cmd": "send",
        "token": user_token,
        "to": target_nick,
        "text": msg_text
    }

    # make_request внутри сделает: send_data -> JSON-строка -> байты
    res = make_request("/send", send_data)
    if res:
        print("Сообщение отправлено!")

print("Завершение работы.")
