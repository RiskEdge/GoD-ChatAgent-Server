from ..logs.logger import setup_logger
from typing import List
from typing import Optional

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
    
def get_geeks_from_user_issue(db: Database, user_issue: UserIssueInDB) -> List[dict]:
    """
    Finds suitable geeks based on a user issue.

    Args:
        user_issue: The UserIssueInDB object representing the user's problem.

    Returns:
        A list of suitable GeekBase objects.
    """
    query = {}
    skill_ids = []
    brand_id = None
    max_distance_km = 15
    
    geeks_collection = db.geeks
    categories_collection = db.categories
    subcategories_collection = db.subcategories
    brands_collection = db.brands

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

    # 2. Match Device Brand with Brands Serviced
    # if user_issue.device_details and user_issue.device_details.brand:
    #     device_brand_name = user_issue.device_details.brand
    #     brand_doc = brands_collection.find_one({"name": device_brand_name})
    #     if brand_doc:
    #         brand_id = brand_doc["_id"]
    #         if "$or" in query: # If skills query already exists, combine with an AND
    #             query["$and"] = [
    #                 query.pop("$or"),
    #                 {"brandsServiced": brand_id}
    #             ]
    #         else:
    #             query["brandsServiced"] = brand_id

    # 3. Location-based matching (if coordinates are available for user and geeks)
    # This requires geospatial indexing on the 'address.coordinates' field in your geeks collection.
    # if user_issue.purchase_info and user_issue.purchase_info.purchase_location and max_distance_km:
    #     user_latitude = None 
    #     user_longitude = None 

    #     if user_latitude is not None and user_longitude is not None:
    #         # MongoDB's $nearSphere operator for geospatial queries
    #         # Ensure you have a 2dsphere index on 'address.coordinates' in your geeks collection
    #         query["address.coordinates"] = {
    #             "$nearSphere": {
    #                 "$geometry": {
    #                     "type": "Point",
    #                     "coordinates": [user_longitude, user_latitude]
    #                 },
    #                 "$maxDistance": max_distance_km * 1000  # Convert km to meters
    #             }
    #         }
    #         # If skills or brands query already exists, combine with an AND
    #         if "$or" in query and "address.coordinates" in query:
    #              query["$and"].append(query.pop("address.coordinates"))
    #         elif "brandsServiced" in query and "address.coordinates" in query:
    #             # This logic can get complex with multiple $and/$or.
    #             # A more robust solution might involve building a list of conditions and then combining.
    #             pass # For now, let's keep it simple for demonstration.

    #Construct pipeline
    pipeline = []
    
    if query:
        pipeline.append({"$match": query})
        
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
                "email": 1, # <--- MUST BE INCLUDED
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
    }
]
    )

    # 4. Execute the query
    suitable_geeks_data = list(geeks_collection.aggregate(pipeline)) if pipeline else geeks_collection.find(query)
    # suitable_geeks = [geek_data for geek_data in suitable_geeks_data]
    suitable_geeks = [AggregatedGeekOutput(**geek_data) for geek_data in suitable_geeks_data]

    return suitable_geeks