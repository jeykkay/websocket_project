from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import List, Any, Dict
import requests
import asyncio
from datetime import datetime

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL вашего React приложения
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def broadcast(self, data: Dict[str, Any]) -> None:
        for connection in self.active_connections:
            await connection.send_json(data)


manager = ConnectionManager()

HTML = '''
<!DOCTYPE html>
<html>
    <head>
        <title>Live Currency Rates</title>
    </head>
    <body>
        <h1>WebSocket Currency Rates</h1>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws/currency/");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages');
                var message = document.createElement('li');
                var content = document.createTextNode(event.data);
                message.appendChild(content);
                messages.appendChild(message);
            };
        </script>
    </body>
</html>
'''


@app.get('/')
async def get():
    return HTMLResponse(HTML)


@app.websocket('/ws/currency')
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def fetch_currency_rates():
    url = 'https://open.er-api.com/v6/latest/USD'
    response = requests.get(url)
    data = response.json()
    times = datetime.now().isoformat()
    if response.status_code == 200:
        rates = data['rates']
        return {
            'time': times,
            'currency': 'BYN',
            'rate': rates['BYN']
        }
    else:
        return {
            'time': times,
            'currency': 'BYN',
            'rate': None
        }


async def send_currency_update():
    while True:
        await asyncio.sleep(2)
        data = await fetch_currency_rates()
        await manager.broadcast(data)


@app.on_event('startup')
async def startup_event():
    asyncio.create_task(send_currency_update())
