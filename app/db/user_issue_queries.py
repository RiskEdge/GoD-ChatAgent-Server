from pymongo.database import Database
from typing import List, Optional
from bson import ObjectId

from ..models.user_issue_model import UserIssueCreate, UserIssueInDB
from ..logs.logger import setup_logger

logger = setup_logger("GoD AI Chatbot: User Issue Query", "app.log")

async def create_user_issue(issue: UserIssueCreate, db: Database) -> UserIssueInDB:
    try:
        issue_dict = issue.dict()
        logger.info("Inserting issue to DB")
        db.user_issues.insert_one(issue_dict)
        logger.info("Issue inserted to DB successfully.")
        return UserIssueInDB(**issue_dict)
    except Exception as e:
        logger.error("Error inserting issue to DB: ", e)
        raise e

async def get_issue_by_user(user_id: str, db: Database) -> List[UserIssueInDB]:
    try:
        issues = []
        logger.info("Fetching issues for user")
        cursor = db.user_issues.find({"user_id": ObjectId(user_id)}).sort("created_at", 1)
        for issue in cursor:
            issues.append(UserIssueInDB(**issue))
        logger.info("Issues fetched successfully")
        return issues
    except Exception as e:
        logger.error("Error fetching issues for user: ", e)
        raise e
    
async def get_issue_by_id(issue_id: str, db: Database) -> Optional[UserIssueInDB]:
    """
    Fetches a single user issue by its ID.
    """
    try:
        logger.info(f"Fetching issue by id: {issue_id}")
        document = await db.user_issues.find_one({"_id": ObjectId(issue_id)})
        if document:
            logger.info(f"Issue with id {issue_id} found")
            return UserIssueInDB(**document)
        else:
            logger.info(f"Issue with id {issue_id} not found")
            return None
    except Exception as e:
        logger.error(f"Error fetching issue by id {issue_id}: {e}")
        raise e
