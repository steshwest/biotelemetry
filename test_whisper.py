import whisper

print("Загрузка модели Whisper... (это может занять время при первом запуске)")
model = whisper.load_model("tiny") # Используем самую маленькую модель для скорости
print("Модель загружена! Whisper готов к работе.")