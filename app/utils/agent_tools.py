from ..logs.logger import setup_logger
from typing import List
from typing import Optional
from pydantic import BaseModel
import math
import re

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure

from ..models.user_issue_model import UserIssueInDB
from ..models.geek_model import GeekBase
from ..models.service_category import CategoryBase

logger = setup_logger("GoD AI Chatbot: Agent Tools", "app.log")

class AggregatedGeekOutput(GeekBase):
    primarySkillName: Optional[str] = None
    secondarySkillsNames: Optional[List[str]] = None
    
class PaginatedGeekResponse(BaseModel):
    geeks: List[AggregatedGeekOutput] = []
    total: int
    limit: int = 5
    page: int = 1
    pages: int
    user_issue: UserIssueInDB

def get_categories(db: Database) -> List[str]:
    """
    Fetches a list of category names from the database.

    Returns:
        List[str]: list of category names
    """
    try:
        categories_collection = db.categories
        category_docs = categories_collection.find({}, {"title": 1, "_id": 0})

        category_names = [doc['title'] for doc in category_docs if 'title' in doc]

        logger.info(f"Found {len(category_names)} categories")
        return category_names

    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise
    except OperationFailure as e:
        logger.error(f"MongoDB operation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise

# --- Function to fetch subcategories ---
def get_subcategories_by_category_slug(db: Database, category_slug: str) -> List[str]:
    """
    Fetches a list of subcategory names associated with a given category slug from the database.
    """
    if not category_slug:
        raise ValueError("Category slug cannot be empty.")

    category_slug = category_slug.lower()

    try:
        categories_collection = db.categories
        subcategories_collection = db.subcategories

        category_doc = categories_collection.find_one({"slug": category_slug})

        if not category_doc:
            logger.info(f"Category with slug '{category_slug}' not found.")
            return []

        try:
            category = CategoryBase.model_validate(category_doc)
        except Exception as e:
            logger.error(f"Error validating category document from DB: {e}")
            return []

        if not category.subCategories:
            logger.info(f"Category '{category.title}' has no subcategories.")
            return []

        subcategory_ids = category.subCategories
        object_ids_for_query = [ObjectId(sub_id) for sub_id in subcategory_ids]

        sub_category_docs = subcategories_collection.find(
            {"_id": {"$in": object_ids_for_query}},
            {"title": 1, "_id": 0}
        )

        subcategory_names = [doc['title'] for doc in sub_category_docs if 'title' in doc]

        logger.info(f"Found subcategories for '{category_slug}': {subcategory_names}")
        return subcategory_names

    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise
    except OperationFailure as e:
        logger.error(f"MongoDB operation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise

def get_brands_by_category_slug(db: Database, category_slug: str) -> List[str]:
    """
    Fetches a list of brand names associated with a given category slug from the database.

    Args:
        db: The MongoDB database client.
        category_slug: The slug of the parent category.

    Returns:
        A list of brand names. Returns an empty list if the category is not found
        or has no brands associated.

    Raises:
        ConnectionFailure: If there's an issue connecting to the MongoDB database.
        OperationFailure: If a database operation fails.
        ValueError: If the category_slug is empty or invalid.
    """
    if not category_slug:
        raise ValueError("Category slug cannot be empty.")

    category_slug = category_slug.lower()

    try:
        categories_collection = db.categories
        brands_collection = db.brands

        # 1. Find the parent category by its slug to get its ID
        category_doc = categories_collection.find_one({"slug": category_slug})

        if not category_doc:
            logger.info(f"Category with slug '{category_slug}' not found for brand lookup.")
            return []

        # Validate and get the category's ObjectId
        try:
            category_id = CategoryBase.model_validate(category_doc).id
        except Exception as e:
            logger.error(f"Error validating category document from DB for brand lookup: {e}")
            return []

        if not category_id:
            logger.warning(f"Category '{category_slug}' found but its ID is missing. Cannot fetch brands.")
            return []

        # 2. Find brands associated with this category ID
        # Project only the 'name' field
        brand_docs = brands_collection.find(
            {"category": ObjectId(category_id)}, # Ensure ObjectId type for the query
            {"name": 1, "_id": 0} # Project only the name field
        )

        # 3. Extract brand names
        brand_names = [doc['name'] for doc in brand_docs if 'name' in doc]

        logger.info(f"Found brands for category '{category_slug}': {brand_names}")
        return brand_names

    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise
    except OperationFailure as e:
        logger.error(f"MongoDB operation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching brands: {e}")
        raise
    
def get_geeks_from_user_issue(db: Database, user_issue: UserIssueInDB, page: int = 1, page_size: int = 5) -> PaginatedGeekResponse:
    """
    Finds suitable geeks based on a user issue.

    Args:
        user_issue: The UserIssueInDB object representing the user's problem.

    Returns:
        A list of suitable GeekBase objects.
    """
    
    logger.info(f"Fetching geeks for user issue: {user_issue.id}")
    query = {}
    skill_ids = []
    
    geeks_collection = db.geeks
    categories_collection = db.categories
    subcategories_collection = db.subcategories
    
    try:
        user = db.users.find_one({"_id": ObjectId(user_issue.user_id)})
        print(user)
        if not user:
            logger.warning(f"No user found with id {user_issue.user_id}")
            return {"error": f"No user found with id {user_issue.user_id}"}
    except Exception as e:
        logger.error(f"Error fetching user's address: {e}")
        return {"error": str(e)}

    # 1. Match Category and Subcategory with Skills
    if user_issue.category_details and user_issue.category_details.category:
        category_name = user_issue.category_details.category
        subcategory_name = user_issue.category_details.subcategory

        # Find skill ID for the category
        category_skill = categories_collection.find_one({"title": category_name})
        if category_skill:
            skill_ids.append(category_skill["_id"])

        # Find skill ID for the subcategory if it exists and is different from category
        if subcategory_name and subcategory_name != category_name:
            subcategory_skill = subcategories_collection.find_one({"title": subcategory_name})
            if subcategory_skill:
                skill_ids.append(subcategory_skill["_id"])

    if skill_ids:
        # Geeks must have either primarySkill or any of secondarySkills matching the issue's skills
        query["$or"] = [
            {"primarySkill": {"$in": skill_ids}},
            {"secondarySkills": {"$in": skill_ids}}
        ]


    skip_amount = (page - 1) * page_size
    if skip_amount < 0:
        skip_amount = 0
    
    #Construct pipeline
    pipeline = []
    
    if query:
        pipeline.append({"$match": query})
        
    if user.get("address") and user_issue.modeOfService != "Online" and not user_issue.location:  
        city = user["address"].get("city")
        state = user["address"].get("state")

        # Only add $match if at least one is present
        if city or state:
            or_conditions = []
            if city:
                or_conditions.append({"address.city": city})
            if state:
                or_conditions.append({"address.state": state})

            pipeline.append({"$match": {"$or": or_conditions}})
            
    if user_issue.modeOfService != "Online" and user_issue.location:
        tokens = re.split(r'\W+', user_issue.location)
        
        tokens = [t for t in tokens if t]
        
        if tokens:
            for token in tokens:
                if user_issue.location:
                    pipeline.append({"$match": {
                        "$or": [
                                {"address.line1": {"$regex": re.escape(token), "$options": "i"}},
                                {"address.line2": {"$regex": re.escape(token), "$options": "i"}},
                                {"address.city":  {"$regex": re.escape(token), "$options": "i"}},
                                {"address.state": {"$regex": re.escape(token), "$options": "i"}},
                                {"address.pin": {"$regex": re.escape(token), "$options": "i"}},
                                ]
                    }})
        
    pipeline.extend(
            [
        {
            '$lookup': {
                'from': 'categories', 
                'localField': 'primarySkill', 
                'foreignField': '_id', 
                'as': 'primarySkillName'
            }
        }, {
            '$lookup': {
                'from': 'categories', 
                'localField': 'secondarySkills', 
                'foreignField': '_id', 
                'as': 'secondarySkillsNames'
            }
        }, {
            '$project': {
                '_id': 1,
                "fullName": 1, # <--- MUST BE INCLUDED
                    "authProvider": 1,
                    # "email": 1, # <--- MUST BE INCLUDED
                    "mobile": 1, # <--- MUST BE INCLUDED
                    "isEmailVerified": 1,
                    "isPhoneVerified": 1,
                    "profileImage": 1,
                    "description": 1,
                    "modeOfService": 1,
                    "availability": 1,
                    "rateCard": 1,
                    "primarySkill": 1,
                'primarySkillName': {
                    '$arrayElemAt': [
                        '$primarySkillName.title', 0
                    ]
                }, 
                'secondarySkillsNames': '$secondarySkillsNames.title',
                "reviews": 1,
                "services": 1,
                    "type": 1, # <--- MUST BE INCLUDED
            }
        # },
        }, {
            '$facet': {
                'geeks': [
                    {'$skip': skip_amount},
                    {'$limit': page_size}
                ],
                'totalCount': [
                    {'$count': 'count'}
                ]
            }
        }
    ]   )
    
    # print(pipeline)

    try:
        # 4. Execute the query
        data = list(geeks_collection.aggregate(pipeline)) if pipeline else geeks_collection.find(query)
        geeks = data[0]['geeks']
        total = data[0]['totalCount'][0]['count']
        
        
    except Exception as e:
        logger.error(f"Error fetching geeks from user issue: {e}")
        raise
    
    try:
        geek_data = {
            "geeks": list(geeks),
            "total": total,
            "limit": page_size,
            "page": page,
            "pages": math.ceil(total/page_size),
            "user_issue": user_issue
        }
        suitable_geeks = PaginatedGeekResponse(**geek_data)
    except Exception as e:
        logger.error(f"Error creating AggregatedGeekOutput objects from suitable geeks data: {e}")
        raise

    return suitable_geeks
