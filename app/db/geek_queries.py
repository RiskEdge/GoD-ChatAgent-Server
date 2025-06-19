from pymongo.database import Database
from bson import ObjectId
from typing import Optional, List, Dict, Any

from ..models.geek_model import GeekBase, IndividualGeek, CorporateGeek  
from ..models.service_category import CategoryBase
from ..logs.logger import setup_logger

logger = setup_logger("GoD AI Chatbot: Geek Query", "app.log")

def get_geeks(
    db,
    geek_type: Optional[str] = None,
    primary_skill: Optional[str] = None,
    brand: Optional[str] = None,
    min_yoe: Optional[int] = None,
    mode_of_service: Optional[str] = None,
    is_verified: Optional[bool] = None,
    limit: int = 10,
    skip: int = 0
) -> List[GeekBase]:
    """
    Query Geek documents from MongoDB with optional filters.

    Args:
        db: The pymongo database instance.
        geek_type: Optional filter for geek type ('Individual' or 'Corporate').
        primary_skill: Optional filter for primary skill ObjectId as a string.
        brand: Optional filter for brand ObjectId as a string.
        min_yoe: Optional minimum years of experience.
        mode_of_service: Optional filter for mode of service.
        is_verified: Optional filter for verification status (applicable to CorporateGeek).
        limit: Number of records to return.
        skip: Number of records to skip.

    Returns:
        List of GeekBase instances matching the filters.
    """
    query: Dict[str, Any] = {}

    if geek_type:
        query["type"] = geek_type

    if primary_skill:
        try:
            query["primarySkill"] = ObjectId(primary_skill)
        except Exception as e:
            raise ValueError(f"Invalid primary_skill ObjectId: {primary_skill}") from e

    if brand:
        try:
            query["brandsServiced"] = ObjectId(brand)
        except Exception as e:
            raise ValueError(f"Invalid brand ObjectId: {brand}") from e

    if min_yoe is not None:
        query["yoe"] = {"$gte": min_yoe}

    if mode_of_service:
        query["modeOfService"] = mode_of_service

    if is_verified is not None:
        query["isVerified"] = is_verified

    cursor = db.geeks.find(query).skip(skip).limit(limit)

    results = []
    for doc in cursor:
        geek_type = doc.get("type")
        if geek_type == "Individual":
            geek = IndividualGeek(**doc)
        elif geek_type == "Corporate":
            geek = CorporateGeek(**doc)
        else:
            geek = GeekBase(**doc)
        results.append(geek)

    return results


def get_geek_by_id(geek_id: str, db: Database) -> Optional[GeekBase]:
    try:
        logger.info("Fetching geek by id: ", geek_id)
        geek = db.geeks.find_one({"_id": ObjectId(geek_id)})
        if geek:
            geek_type = geek.get("type")
            if geek_type == "Individual":
                logger.info(f"Found individual geek with id: {geek_id}")
                return IndividualGeek(**geek)
            elif geek_type == "Corporate":
                logger.info(f"Found corporate geek with id: {geek_id}")
                return CorporateGeek(**geek)
            else:
                return GeekBase(**geek)
        logger.error(f"Geek with id {geek_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error fetching geek by id {geek_id}: {e}")
        return None

def get_all_geeks(db: Database) -> List[GeekBase]:
    try:
        logger.info("Fetching all geeks")
        cursor = db.geeks.find()
        results = []
        for doc in cursor:
            geek_type = doc.get("type")
            if geek_type == "Individual":
                geek = IndividualGeek(**doc)
            elif geek_type == "Corporate":
                geek = CorporateGeek(**doc)
            else:
                geek = GeekBase(**doc)
            results.append(geek)
        return results
    except Exception as e:
        logger.error(f"Error fetching all geeks: {e}")
        return []

def get_all_services(db: Database) -> List[CategoryBase]:
    try:
        logger.info("Fetching all service categories")
        cursor = db.categories.find()
        results = []
        for doc in cursor:
            results.append(CategoryBase(**doc))
        return results
    except Exception as e:
        logger.error(f"Error fetching all service categories: {e}")
        return []
