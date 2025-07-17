from ..logs.logger import setup_logger
from typing import List

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure
# from ..models.brand_model import Brand
# from ..models.sub_category import SubCategory
from ..models.service_category import CategoryBase

logger = setup_logger("GoD AI Chatbot: Agent Tools", "app.log")

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