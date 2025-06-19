from bson import ObjectId
from pymongo.database import Database
from typing import List, Optional

from ..dependencies import get_database
from ..models.agent_chat_model import ChatMessageInDB, ChatMessageCreate
from ..logs.logger import setup_logger

logger  = setup_logger("GoD AI Chatbot: Agent Chat Query", "app.log")

async def create_chat_message(message: ChatMessageCreate, db: Database) -> ChatMessageInDB:
    try:
        message_dict = message.dict()
        logger.info("Inserting message to DB")
        db.chat_messages_with_bot.insert_one(message_dict)
        logger.info("Message inserted to DB successfully.")
        return ChatMessageInDB(**message_dict)
    except Exception as e:
        logger.error("Error inserting message to DB: ", e)
        raise e
    
async def get_chat_history_with_agent(conversation_id: str, db: Database) -> List[ChatMessageInDB]:
    try:
        logger.info("Fetching chat history with agent")
        cursor = db.chat_messages_with_bot.find({"conversation_id": conversation_id}).sort("created_at", 1)
        
        return [ChatMessageInDB(**message) for message in cursor]
    except Exception as e:
        logger.error("Error fetching chat history with agent: ", e)
        raise e
    
async def get_message_by_id(message_id: str, db: Database) -> Optional[dict]:
    try:
        logger.info("Fetching message by id", message_id)
        message = db.chat_messages_with_bot.find_one({"_id": ObjectId(message_id)})
        return message
    except Exception as e:
        logger.error("Error fetching message by id: ", e)
        raise e
    
async def get_conversations_by_user(user_id: str, db: Database) -> List[dict]:
    try:
        pipeline = [
        {
            "$match": {"user_id": user_id}
        },
        {
            "$sort": {"created_at": 1}
        },
        {
            "$group": {
                "_id": "$conversation_id",
                "messages": {
                    "$push": {
                        "sender": "$sender",
                        "message": "$message",
                        "createdAt": "$createdAt"
                    }
                },
                "startTime": {"$min": "$createdAt"}
            }
        },
        {
            "$sort": {"startTime": -1}
        }
    ]
        logger.info("Fetching conversations by user", user_id)
        cursor = db.chat_messages_with_bot.aggregate(pipeline)
        
        return [conversation for conversation in cursor]
    except Exception as e:
        logger.error("Error fetching conversations by user: ", e)
        raise e