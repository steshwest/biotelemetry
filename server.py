import uuid
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Dict, Optional
from cryptography.fernet import Fernet

app = FastAPI(title="Telemedicine Secure Gateway")

# Имитация базы данных в памяти
# rooms = { "room_id": {"status": "open/closed", "token": "...", "participants": ["doctor_id", "patient_id"]} }
rooms: Dict[str, dict] = {}
# tokens = { "token": "room_id" }
tokens: Dict[str, str] = {}

class RoomRequest(BaseModel):
    doctor_id: str
    patient_id: str

class TokenRequest(BaseModel):
    user_id: str
    room_id: str

# --- Хендлеры (Эндпоинты) ---

@app.post("/room/open")
async def open_room(request: RoomRequest):
    """
    Создает приватную комнату для врача и пациента.
    Генерирует уникальный ID комнаты и секретный токен доступа.
    """
    room_id = str(uuid.uuid4())
    access_token = str(uuid.uuid4())
    session_key = Fernet.generate_key() # Генерируем случайный ключ для этой сессии
    
    
    rooms[room_id] = {
        "status": "open",
        "token": access_token,
        "key": session_key, # Сохраняем ключ в данные комнаты
        "participants": [request.doctor_id, request.patient_id]
    }
    
    # Связываем токен с комнатой для быстрой проверки
    tokens[access_token] = room_id
    
    return {
        "message": "Room created successfully",
        "room_id": room_id,
        "access_token": access_token,
        "session_key": session_key.decode() # Отдаем ключ клиенту (в виде строки)
    }

@app.post("/room/close/{room_id}")
async def close_room(room_id: str):
    """
    Закрывает комнату. После этого доступ по токену будет аннулирован.
    """
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    rooms[room_id]["status"] = "closed"
    # Удаляем токен из активных
    token = rooms[room_id]["token"]
    if token in tokens:
        del tokens[token]
        
    return {"message": f"Room {room_id} is now closed"}

@app.post("/auth/get_token")
async def get_token(request: TokenRequest):
    """
    Функционал раздачи токенов. 
    Токен выдается, только если пользователь является участником этой комнаты.
    """
    if request.room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room does not exist")
    
    room = rooms[request.room_id]
    
    if room["status"] == "closed":
        raise HTTPException(status_code=403, detail="Room is closed")
    
    if request.user_id not in room["participants"]:
        raise HTTPException(status_code=403, detail="User is not authorized for this room")
    
    return {
        "user_id": request.user_id,
        "token": room["token"],
        "session_key": room["key"].decode() # Отправляем ключ, декодированный в строку

    }

@app.get("/room/status/{room_id}")
async def check_room(room_id: str, authorization: Optional[str] = Header(None)):
    """
    Проверка доступа в комнату с использованием токена.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Token missing")
    
    # Проверяем, существует ли токен и ведет ли он в эту комнату
    if authorization not in tokens or tokens[authorization] != room_id:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    
    return {"status": "Access granted", "room_id": room_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)