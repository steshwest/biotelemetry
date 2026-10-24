import socket

# Настройки сети
UDP_IP = "0.0.0.0"  # Слушать все доступные сетевые интерфейсы
UDP_PORT = 5005      # Порт должен быть открыт в брандмауэре

# Создаем сокет: AF_INET (IPv4), SOCK_DGRAM (UDP)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Привязываем сокет к адресу и порту
sock.bind((UDP_IP, UDP_PORT))

print(f"Сервер запущен. Ожидание сообщений на порту {UDP_PORT}...")

while True:
    # Получаем данные (буфер 1024 байта) - 65535?
    # data — само сообщение, addr — адрес и порт отправителя
    # data, addr = sock.recvfrom(1024)
    data, addr = sock.recvfrom(65535)
    
    message = data.decode('utf-8')
    print(f"Получено сообщение от {addr}: {message}")
    
    # Опционально: отправляем ответ отправителю
    response = "Сообщение получено!".encode('utf-8')
    sock.sendto(response, addr)
