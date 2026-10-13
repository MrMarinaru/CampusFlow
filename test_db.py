import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.getenv("MONGODB_URI")
db_name = os.getenv("MONGODB_DB_NAME", "classflow")

if not uri:
    raise RuntimeError("MONGODB_URI is missing from .env")

client = MongoClient(uri, serverSelectionTimeoutMS=5000)

try:
    client.admin.command("ping")
    db = client[db_name]

    print("Connected to MongoDB Atlas!")
    print("Database:", db.name)
    print("Collections:", db.list_collection_names())
finally:
    client.close()