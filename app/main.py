# app/main.py
from fastapi import FastAPI, HTTPException
from app.database.mongodb import db
from app.models.schemas import Task, UserActivity
from datetime import datetime
from app.ml.models import MLProcessor
ml_processor = MLProcessor()

app = FastAPI(title="TimeBloom API")

@app.get("/")
async def root():
    return {"message": "Welcome to TimeBloom API"}

@app.post("/tasks/")
async def create_task(task: Task):
    try:
        task_dict = task.dict()
        result = db.tasks.insert_one(task_dict)
        task_dict["_id"] = str(result.inserted_id)
        return task_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{user_id}")
async def get_user_tasks(user_id: str):
    try:
        tasks = list(db.tasks.find({"user_id": user_id}))
        # Convert ObjectId to string for JSON serialization
        for task in tasks:
            task["_id"] = str(task["_id"])
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/activity/{user_id}")
async def get_user_activity(user_id: str):
    try:
        activities = list(db.user_activity.find({"user_id": user_id}))
        for activity in activities:
            activity["_id"] = str(activity["_id"])
        return activities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/activity/")
async def log_activity(activity: UserActivity):
    try:
        # Convert activity to dict and add timestamp
        activity_dict = activity.dict()
        current_time = datetime.now()
        activity_dict["timestamp"] = current_time
        
        # Save to database
        result = db.user_activity.insert_one(activity_dict)
        activity_dict["_id"] = str(result.inserted_id)
        
        # Process activity for ML recommendations
        try:
            await ml_processor.process_new_activity(activity_dict)
        except Exception as e:
            print(f"ML Processing error: {e}")
            # Continue even if ML processing fails
            
        return activity_dict
    except Exception as e:
        print(f"Error in log_activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    try:
        recommendations = await ml_processor.get_recommendations(user_id)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))   
    
         