from pymongo.database import Database
from bson import ObjectId
from typing import Optional, List

from ..models.seeker_model import SeekerBase
from ..logs.logger import setup_logger

logger = setup_logger("GoD AI Chatbot: Seeker Query", "app.log")

def get_seeker_by_id(seeker_id: str, db: Database) -> Optional[SeekerBase]:
    try:
        logger.info(f"Fetching seeker by id: {seeker_id}")
        seeker = db.users.find({"_id": ObjectId(seeker_id)})
        if seeker:
            logger.info(f"Found seeker with id: {seeker_id}")
            return SeekerBase(**seeker)
        else:
            logger.info(f"Seeker with id {seeker_id} not found")
            return None
    except Exception as e:
        logger.error(f"Error fetching seeker by id {seeker_id}: {e}")
        raise e
    
def get_all_seekers(db: Database) -> List[SeekerBase]:
    try:
        logger.info("Fetching all seekers")
        seekers = db.users.find()
        logger.info("Fetched all seekers")
        return [SeekerBase(**seeker) for seeker in seekers]
    except Exception as e:
        logger.error(f"Error fetching all seekers: {e}")
        raise e
