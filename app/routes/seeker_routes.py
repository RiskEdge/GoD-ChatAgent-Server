from fastapi import APIRouter, HTTPException, Depends
from pymongo.database import Database

from ..logs.logger import setup_logger
from ..dependencies import get_database
from ..db.seeker_queries import get_all_seekers, get_seeker_by_id

seeker_router = APIRouter(
    prefix="/seeker_query",
    tags=["seeker", "db"],
    responses={404: {"description": "Not found"}},
)

logger = setup_logger("GoD AI Chatbot: Seeker Route", "app.log")

@seeker_router.get("/get_all_seekers")
async def get_all_seekers(db: Database = Depends(get_database)):
    try:
        logger.info("Fetching all seekers")
        seekers = get_all_seekers(db)
        if not seekers:
            logger.error("Seekers not found")
            raise HTTPException(status_code=404, detail="Seekers not found")
        return {"seekers": seekers}
    except Exception as e:
        logger.error(f"Error getting seekers: {e}")
        return {"error": str(e)}
    
@seeker_router.get("/get_seeker/{id}")
async def get_seeker_from_id(id: str, db: Database = Depends(get_database)):
    try:
        logger.info(f"Fetching seeker with id: {id}")
        seeker = get_seeker_by_id(id, db=db)
        if not seeker:
            logger.error("Seeker not found")
            raise HTTPException(status_code=404, detail="Seeker not found")
        return {"seeker": seeker}
    except Exception as e:
        logger.error(f"Error getting seekers: {e}")
        return {"error": str(e)}