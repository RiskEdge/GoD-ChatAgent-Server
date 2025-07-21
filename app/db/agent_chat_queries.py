from bson import ObjectId
from pymongo.database import Database
from typing import List, Optional

from ..models.helper import PyObjectId
from ..models.agent_chat_model import ChatMessageInDB, ChatConversationCreate, ChatMessageBase
from ..logs.logger import setup_logger

logger  = setup_logger("GoD AI Chatbot: Agent Chat Query", "app.log")

# async def create_chat_message(message: ChatMessageCreate, db: Database) -> ChatMessageInDB:
#     try:
#         message_dict = message.dict()
#         logger.info("Inserting message to DB")
#         db.chat_messages_with_bot.insert_one(message_dict)
#         logger.info("Message inserted to DB successfully.")
#         return ChatMessageInDB(**message_dict)
#     except Exception as e:
#         logger.error("Error inserting message to DB: ", e)
#         raise e
    
async def append_message_to_convo(user_id: str, conversation_id: str, message: ChatMessageBase, db: Database) -> ChatMessageBase:
    try:
        logger.info("Appending message to conversation")
        db.chat_messages_with_bot.update_one(
            {"conversation_id": conversation_id}, 
            {
                "$setOnInsert": {"user_id": user_id},
            # {"$setOnInsert": {"user_id": ObjectId(user_id)}},
            "$push": {"chat_messages": message.dict()}},
        upsert=True)
        logger.info("Message appended to conversation successfully.")
        return ChatMessageBase(**message.dict())
    except Exception as e:
        logger.error("Error inserting message to DB: ", e)
        raise e
  
  
def parse_chat_message_in_db(doc) -> ChatMessageInDB:
    # if "_id" in doc:
        # doc["_id"] = str(doc["_id"])  # ObjectId -> str

    # Parse each chat message
    doc["chat_messages"] = [ChatMessageBase(**msg) for msg in doc["chat_messages"]]

    return ChatMessageInDB(**doc)
  
async def get_chat_history_with_agent(conversation_id: str, db: Database) -> List[ChatMessageInDB]:
    try:
        logger.info("Fetching chat history with agent")
        chat_history = []
        cursor = db.chat_messages_with_bot.find({"conversation_id": conversation_id})
        if cursor:
            logger.info("Chat history fetched successfully")
            for doc in cursor:
                print(doc)
                parsed_doc = parse_chat_message_in_db(doc)
                chat_history.append(parsed_doc)
        # print(cursor)
            return chat_history
        else:
            return []
    except Exception as e:
        logger.error(f"Error fetching chat history with agent: {e}")
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