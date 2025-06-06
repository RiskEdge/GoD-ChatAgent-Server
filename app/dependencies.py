from fastapi import Request
from pymongo.database import Database

def get_database(request: Request) -> Database:
    return request.app.state.database