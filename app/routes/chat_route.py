from fastapi import APIRouter, HTTPException, Depends
from pymongo.database import Database

from ..logs.logger import setup_logger
from ..dependencies import get_database
from ..db.agent_chat_queries import get_chat_history_with_agent, get_conversations_by_user

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
            return chat_history
        else:
            logger.error("Chat history not found")
            return []
    except Exception as e:
        logger.error(f"Error fetching chat history with agent: {e}")
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
        logger.error(f"Error fetching conversation: {e}")
        raise HTTPException(status_code=500, detail="Error fetching conversation")
    
@chat_router.delete("/delete/{conversation_id}")
async def delete_conversation(conversation_id: str, db: Database = Depends(get_database)):
    try:
        logger.info(f"Deleting conversation with id: {conversation_id}")
        result = db.chat_messages_with_bot.delete_many({"conversation_id": conversation_id})
        if result.deleted_count > 0:
            logger.info(f"Conversation with id {conversation_id} deleted successfully")
            return {"message": f"Conversation with id {conversation_id} deleted successfully"}
        else:
            logger.error(f"Conversation with id {conversation_id} not found")
            raise HTTPException(status_code=404, detail=f"Conversation with id {conversation_id} not found")
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail="Error deleting conversation")
