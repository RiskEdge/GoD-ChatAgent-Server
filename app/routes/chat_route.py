from fastapi import APIRouter, HTTPException, Depends
from pymongo.database import Database

from ..logs.logger import setup_logger
from ..dependencies import get_database
from ..db.agent_chat_queries import create_chat_message, get_chat_history_with_agent, get_conversations_by_user

chat_router = APIRouter(
    prefix="/chat",
    tags=["chat", "db"],
    responses={404: {"description": "Not found"}},
)

logger = setup_logger("GoD AI Chatbot: Chat Route", "app.log")

@chat_router.get("/chat_history/{conversation_id}")
async def chat_history(conversation_id: str, db: Database = Depends(get_database)):
    try:
        logger.info("Fetching chat history")
        chat_history =  await get_chat_history_with_agent(conversation_id, db)
        if chat_history:
            print(chat_history)
            logger.info("Chat history fetched successfully")
            return [{"role": message.sender, "content": message.message} for message in chat_history]
        else:
            logger.error("Chat history not found")
            return None
    except Exception as e:
        logger.error("Error fetching chat history: ", e)
        raise HTTPException(status_code=500, detail="Error fetching chat history")
    
@chat_router.get("/conversation/{user_id}")
async def get_conversation(user_id: str, db: Database = Depends(get_database)):
    try:
        logger.info("Fetching conversation")
        conversations = await get_conversations_by_user(user_id, db)
        if conversations:
            logger.info("Conversation fetched successfully")
            print(f"{len(conversations)} conversations found for user {user_id}")
            return conversations
        else:
            logger.error("Conversation not found")
            return None
    except Exception as e:
        logger.error("Error fetching conversation: ", e)
        raise HTTPException(status_code=500, detail="Error fetching conversation")