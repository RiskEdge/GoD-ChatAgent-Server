from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI


import asyncio
import os
import time
import json
import dotenv
from bson import ObjectId

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
    "https://god-chatagent-client-production.up.railway.app",
    "https://god-ui.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ws_connection = ConnectionManager()
client = OpenAI()

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


@app.post("/tts")
async def tts(request: dict):
    text = request.get("text")
    voice = request.get("voice", "verse")

    try:
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text,
            response_format="wav",
            instructions='Voice Affect: Calm, composed, and reassuring. Competent and in control, instilling trust.\n\nTone: Sincere, empathetic, with genuine concern for the customer and understanding of the situation.\n\nPacing: Slower during the apology to allow for clarity and processing. Faster when offering solutions to signal action and resolution.\n\nEmotions: Calm reassurance, empathy, and gratitude.\n\nPronunciation: Clear, precise: Ensures clarity, especially with key details.'
        )

        # response is a streaming response, so we can yield chunks
        audio_bytes = response.read()  # blocking full read (for simple case)

        return Response(
            content=audio_bytes,
            media_type="audio/wav"
        )

    except Exception as e:
        return {"error": str(e)}

@app.websocket("/chat/{user_id}")
async def chat(websocket: WebSocket, user_id: str, conversation_id: str):
    logger.info("Chat with agent initiated.")
    await ws_connection.connect(websocket)
    
    extractor = IssueExtractor()
    
    assistant = ChatAssistantChain(db_instance=app.state.database)
    
    try:
        while True:
            try:
                query = await ws_connection.receive_message(websocket)
                logger.info(f"Received message: {query}")
                
                try:
                    query = json.loads(query)
                    # is_continuation = query['action'] == "continue_conversation"
                    if isinstance(query, dict) and query.get('action') == "continue_conversation":
                        is_continuation = True
                    else:
                        is_continuation = False
                except json.JSONDecodeError:
                    query = str(query)
                    is_continuation = False
                
                if not is_continuation:
                    # Creating user message from the pydantic model
                    user_message = ChatMessageBase(
                        sender=MessageSender.USER,
                        message=str(query)
                    )
                    await append_message_to_convo(user_id, conversation_id, user_message, app.state.database)
                    logger.info("User message saved to DB.")
                    
                    # CHECK FOR COMPLETION TRIGGER
                    # If the agent;s last message was the confirmation prompt and user says 'yes'
                    last_question = agent_last_question.get(conversation_id)
                    print("LAST QUESTION: ", last_question)
                    if last_question and "Is this summary correct?" in last_question and str(query).lower() == "yes":
                        logger.info("Processing the chat and extracting details...")
                        
                        # A. fetch the full conversation history
                        logger.info('fetching the chat hisotry from database...')
                        history = await get_chat_history_with_agent(conversation_id, app.state.database)
                        transcript = "\n".join([f"{msg.sender.value}: {msg.message}" for msg in history[0].chat_messages])
                        
                        # B. use the extractor to get structured data
                        logger.info("extracting details from conversation history...")
                        extracted_data = await extractor.extract_issue_details(
                            transcript=transcript,
                            user_id=ObjectId(user_id),
                            conversation_id=conversation_id
                        )
                        
                        await ws_connection.send_message(json.dumps({'response': "Your issue is being processed and we'll find a suitable geek for you shortly.", 'options': None}), websocket)
                        
                        # C. create the user issue from the extracted data
                        logger.info("creating user issue from extracted data...")
                        issue = UserIssueCreate(**extracted_data)
                        issue_in_db = await create_user_issue(issue, app.state.database)
                        logger.info("User issue saved to DB.")
                        
                        try:
                            logger.info(f"Fetching geeks from user issue: {issue}")                   
                            geeks = get_geeks_from_user_issue(app.state.database, issue_in_db, page=1, page_size=5)
                            logger.info(f"Geeks fetched: {len(geeks.geeks)}")
                            if geeks: 
                                await ws_connection.send_message(json.dumps({'response': f"Please select a Geek to proceed", 'options': [geeks.model_dump_json()]}), websocket)
                            else:
                                await ws_connection.send_message(json.dumps({"response": "No suitable geeks found", "options":None}), websocket)
                        except Exception as e:
                            logger.error(f"Error fetching geeks from user issue: {e}")
                        
                        # D. Clean up and close the connection
                        del agent_last_question[conversation_id]
                        break # Exit the while loop to close the socket
                
                    response = await assistant.run(str(query))
                    
                else:
                    response = await assistant.run(json.dumps(query['chat_history']))
                    
                await ws_connection.send_message(response['response'], websocket)
                agent_response_text = response.get("response", "Sorry, something went wrong.")
                # print("AGENT RESPONSE TEXT: ", agent_response_text)
                
                # Store the agent's question for the next loop
                agent_last_question[conversation_id] = agent_response_text

                # 4. Save agent message to DB
                logger.info("Saving agent message to DB...")
                agent_message = ChatMessageBase(
                    sender=MessageSender.BOT,
                    message=json.loads(agent_response_text)["response"]
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