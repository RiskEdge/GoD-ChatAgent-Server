from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


import asyncio
import os
import time
import json
import dotenv

dotenv.load_dotenv()

from .logs.logger import setup_logger
from .db.conn import db_client
from .db.queries import get_geek_by_id, get_all_geeks, get_geeks
from .models.geek_model import GeekBase
from .ws_connection import ConnectionManager, WebSocketCallbackHandler
from .agent_setup import ChatAssistantChain

from .routes.db_routes import router as db_router


app = FastAPI()
logger = setup_logger("GoD AI Chatbot: Server", "app.log")

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ws_connection = ConnectionManager()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Incoming request: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception(f"Unhandled exception occured: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal Server Error"})
    
    process_time = (time.time() - start_time)*1000
    logger.info(f"Completed in {process_time:.2f}ms - Status Code: {response.status_code}")
    
    return response

@app.on_event("startup")
def startup_db_client():
    app.mongodb_client = db_client()
    app.state.database = app.mongodb_client[os.environ["DB_NAME"]]
    print("Connnected to MongoDB database.")
    
@app.on_event("shutdown")
def shutdown_db_client():
    app.mongodb_client.close()
    print("Disconnected from MongoDB database.")

@app.get("/")
async def index():
    logger.info("Root route hit")
    return JSONResponse(status_code=200, content={"message": "Hello World!"})

@app.websocket("/chat")
async def chat(websocket: WebSocket):
    logger.info("Chat with agent initiated.")
    await ws_connection.connect(websocket)
    
    callback_handler = WebSocketCallbackHandler(websocket, ws_connection)
    assistant = ChatAssistantChain(callback_handler=callback_handler)
    
    try:
        while True:
            try:
                query = await ws_connection.receive_message(websocket)
                logger.info(f"Received message: {query}")
                response = await assistant.run(query)
                await ws_connection.send_message(json.dumps(response), websocket)
                logger.info(f"AI response: {response}")
            except asyncio.TimeoutError:
                await ws_connection.send_message(websocket, "Session timed out due to inactivity.")
                await ws_connection.disconnect(websocket)
                logger.error(f"WebSocket Session timed out due to inactivity.")
    except WebSocketDisconnect:
        ws_connection.disconnect(websocket)
        logger.error("Error: WebSocket disconnected.")
    except Exception as e:
        ws_connection.disconnect(websocket)
        logger.error(f"Error during chat: {e}")
        await websocket.close()
                
             
app.include_router(db_router)