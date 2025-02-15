# app/models/schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import List

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: str
    difficulty: str
    priority: str
    
class Task(BaseModel):
    user_id: str
    title: str
    description: Optional[str] = None
    task_type: str
    difficulty: str
    priority: str
    completed: Optional[bool] = False
    created_at: Optional[datetime] = None

class Location(BaseModel):
    type: str
    coordinates: List[float]
    
class UserActivity(BaseModel):
    user_id: str
    energy_level: str
    location: dict
    timestamp: Optional[datetime] = None