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
from .db.agent_chat_queries import get_chat_history_with_agent, append_message_to_convo
from .db.user_issue_queries import create_user_issue
from .utils.ws_connection import ConnectionManager
from .utils.agent_setup import ChatAssistantChain
from .utils.issue_extractor import IssueExtractor
from .utils.agent_tools import get_geeks_from_user_issue

from .models.user_issue_model import UserIssueCreate
from .models.agent_chat_model import ChatMessageBase, MessageSender

from .routes.geek_routes import router as db_router
from .routes.seeker_routes import seeker_router
from .routes.chat_route import chat_router
import warnings
# from pymongo.errors import UserWarning

# Suppress the specific CosmosDB warning
warnings.filterwarnings("ignore")

app = FastAPI()
logger = setup_logger("GoD AI Chatbot: Server", "app.log")


origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://god-chatagent-client-production.up.railway.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ws_connection = ConnectionManager()

agent_last_question = {}

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

@app.websocket("/chat/{user_id}")
async def chat(websocket: WebSocket, user_id: str, conversation_id: str, page: int, page_size: int = 5):
    logger.info("Chat with agent initiated.")
    await ws_connection.connect(websocket)
    
    extractor = IssueExtractor()
    print("CONVERSATION ID: ", conversation_id)
    # conversation_id = str(uuid.uuid4())
    
    # callback_handler = WebSocketCallbackHandler(websocket, ws_connection)
    # assistant = ChatAssistantChain(callback_handler=callback_handler)
    assistant = ChatAssistantChain(db_instance=app.state.database)
    
    try:
        while True:
            try:
                query = await ws_connection.receive_message(websocket)
                logger.info(f"Received message: {query}")
                
                # Creating user message from the pydantic model
                user_message = ChatMessageBase(
                    sender=MessageSender.USER,
                    message=query
                )
                await append_message_to_convo(user_id, conversation_id, user_message, app.state.database)
                logger.info("User message saved to DB.")
                
                # CHECK FOR COMPLETION TRIGGER
                # If the agent;s last message was the confirmation prompt and user says 'yes'
                last_question = agent_last_question.get(conversation_id)
                print("LAST QUESTION: ", last_question)
                if last_question and "Is this summary correct?" in last_question and query.lower() == "yes":
                    logger.info("Processing the chat and extracting details...")
                    
                    # A. fetch the full conversation history
                    logger.info('fetching the chat hisotry from database...')
                    history = await get_chat_history_with_agent(conversation_id, app.state.database)
                    transcript = "\n".join([f"{msg.sender.value}: {msg.message}" for msg in history[0].chat_messages])
                    
                    # B. use the extractor to get structured data
                    logger.info("extracting details from conversation history...")
                    extracted_data = await extractor.extract_issue_details(
                        transcript=transcript,
                        user_id=user_id,
                        conversation_id=conversation_id
                    )
                    
                    await ws_connection.send_message(json.dumps({'response': "Your issue is being processed and we'll find a suitable geek for you shortly.", 'options': None}), websocket)
                    
                    # C. create the user issue from the extracted data
                    logger.info("creating user issue from extracted data...")
                    issue = UserIssueCreate(**extracted_data)
                    await create_user_issue(issue, app.state.database)
                    logger.info("User issue saved to DB.")
                    
                    try:
                        logger.info("Fetching geeks from user issue")                   
                        geeks = get_geeks_from_user_issue(app.state.database, issue, page=page, page_size=page_size)
                        logger.info("Geeks fetched: ", geeks)
                        if geeks: 
                            await ws_connection.send_message(json.dumps({'response': f"Please select a Geek to proceed", 'options': [geek.model_dump(by_alias=True) for geek in geeks]}), websocket)
                        else:
                            await ws_connection.send_message(json.dumps({"response": "No suitable geeks found", "options":None}), websocket)
                    except Exception as e:
                        logger.error(f"Error fetching geeks from user issue: {e}")
                    
                    # D. Clean up and close the connection
                    del agent_last_question[conversation_id]
                    break # Exit the while loop to close the socket
                
                response = await assistant.run(query)
                await ws_connection.send_message(response['response'], websocket)
                agent_response_text = response.get("response", "Sorry, something went wrong.")
                # print("AGENT RESPONSE TEXT: ", agent_response_text)
                # logger.info(f"AI response: {response['response']}")
                # logger.info(f" TYPE AI response: {type(response['response'])}")
                
                # Store the agent's question for the next loop
                agent_last_question[conversation_id] = agent_response_text

                # 4. Save agent message to DB
                logger.info("Saving agent message to DB...")
                agent_message = ChatMessageBase(
                    sender=MessageSender.BOT,
                    message=agent_response_text
                )
                await append_message_to_convo(user_id, conversation_id, agent_message, app.state.database)
                logger.info("Agent message saved to DB.")
            except asyncio.TimeoutError:
                await ws_connection.send_message(websocket, "Session timed out due to inactivity.")
                await ws_connection.disconnect(websocket)
                logger.error(f"WebSocket Session timed out due to inactivity.")
    except WebSocketDisconnect:
        if conversation_id in agent_last_question:
            del agent_last_question[conversation_id]
        ws_connection.disconnect(websocket)
        logger.error(f"Client {user_id} disconnected.")
    except Exception as e:
        ws_connection.disconnect(websocket)
        logger.error(f"Error during chat: {e}")
        await websocket.close()
                
             
app.include_router(db_router)
app.include_router(seeker_router)
app.include_router(chat_router)