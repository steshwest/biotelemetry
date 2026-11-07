import socket
import pyaudio
import time

# НАСТРОЙКИ
SERVER_IP = "127.0.0.1"
AUDIO_SERVER_PORT = 7000
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

def test_send():
    print("--- Запуск теста отправки аудио ---")
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        print(f"Отправка сырых данных на {SERVER_IP}:{AUDIO_SERVER_PORT}...")
        print("Говорите в микрофон... (Ctrl+C для выхода)")
        
        count = 0
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            sock.sendto(data, (SERVER_IP, AUDIO_SERVER_PORT))
            count += 1
            if count % 100 == 0:
                print(f"Отправлено {count} пакетов...")
                
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
    except KeyboardInterrupt:
        print("Остановка...")

if __name__ == "__main__":
    test_send()