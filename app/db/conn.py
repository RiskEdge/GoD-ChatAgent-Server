from pymongo import MongoClient
import os

def db_client():
    """
    Asynchronously creates and returns a MongoClient instance connected to the MongoDB
    database specified by the MONGODB_URI environment variable.

    Returns:
        MongoClient: A client instance connected to the specified MongoDB database.
    """

    MONGODB_URI = os.environ["MONGODB_URI"]
    client = MongoClient(MONGODB_URI)
    return client