from fastapi import APIRouter, HTTPException, Depends
from pymongo.database import Database

from ..logs.logger import setup_logger
from ..dependencies import get_database
from ..db.queries import get_all_geeks, get_geek_by_id, get_all_services

router = APIRouter(
    prefix="/db_query",
    tags=["db"],
    responses={404: {"description": "Not found"}},
)

logger = setup_logger("GoD AI Chatbot: DB Query", "app.log")

@router.get("/get_all_geeks")
async def get_geeks_all(db: Database = Depends(get_database)):
    try:
        logger.info("Fetching all geeks")
        geeks = get_all_geeks(db)
        print(len(geeks))
        if not geeks:
            logger.error("Geeks not found")
            raise HTTPException(status_code=404, detail="Geeks not found")
        return {"geeks": geeks}
    except Exception as e:  
        logger.error(f"Error getting geeks: {e}")
        return {"error": str(e)}
    
@router.get("/get_geek/{id}")
async def get_geek_from_id(id: str, db: Database = Depends(get_database)):
    try:
        logger.info(f"Fetching geek with id: {id}")
        geek = get_geek_by_id(id, db=db)
        if not geek:
            logger.error("Geek not found")
            raise HTTPException(status_code=404, detail="Geek not found")
        return {"geek": geek}
    except Exception as e:  
        logger.error(f"Error getting geeks: {e}")
        return {"error": str(e)}
    
@router.get("/get_service_categories")
async def get_service_categories(db: Database = Depends(get_database)):
    try:
        logger.info("Fetching available service categories")
        categories = get_all_services(db)
        if not categories:  
            logger.error("Service categories not found")
            raise HTTPException(status_code=404, detail="Service categories not found")
        return {"categories": categories}
    except Exception as e:
        logger.error(f"Error getting service categories: {e}")
        return {"error": str(e)}