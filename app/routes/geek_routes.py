from fastapi import APIRouter, HTTPException, Depends, Body
from pymongo.database import Database

from ..logs.logger import setup_logger
from ..dependencies import get_database
from ..db.geek_queries import get_all_geeks, get_geek_by_id, get_all_services
from ..utils.agent_tools import get_geeks_from_user_issue, get_subcategories_by_category_slug

from ..models.user_issue_model import UserIssueInDB

router = APIRouter(
    prefix="/geek_query",
    tags=["db", "geek"],
    responses={404: {"description": "Not found"}},
)

logger = setup_logger("GoD AI Chatbot: Geek Route", "app.log")

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
    
@router.get("/get_subcategories_from_slug/{slug}")
async def get_slug_subcategories( slug: str, db: Database = Depends(get_database)):
    try:
        logger.info(f"Fetching subcategories from slug: {slug}")
        subcategories = get_subcategories_by_category_slug(db=db, category_slug=slug)
        if not subcategories:
            logger.error("Subcategories not found")
            raise HTTPException(status_code=404, detail="Subcategories not found")
        return  subcategories
    except Exception as e:
        logger.error(f"Error getting subcategories from slug: {e}")
        return {"error": str(e)}
    
@router.post("/get_geeks_from_user_issue")
async def get_geeks_from_issue(db: Database = Depends(get_database), user_issue: UserIssueInDB = Body(...), page: int = 1, page_size: int = 5):
    try:
        logger.info("Fetching geeks from user issue")
        geeks = get_geeks_from_user_issue(db, user_issue, page=page, page_size=page_size)
        if not geeks:
            logger.error("Geeks not found")
            raise HTTPException(status_code=404, detail="Geeks not found")
        # print(f"Found {len(geeks)} geeks from user issue")
        return geeks
    except Exception as e:
        logger.error(f"Error getting geeks from user issue: {e}")
        return {"error": str(e)}