# app/database/mongodb.py
from pymongo import MongoClient
from config import MONGODB_URI, DATABASE_NAME

client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]