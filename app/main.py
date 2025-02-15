import os
import sys
import json
from datetime import datetime

# Our database and models
from app.database.mongodb import db
from app.models.schemas import Task, UserActivity
from app.ml.models import MLProcessor

ml_processor = MLProcessor()

def create_task(data: dict):
    """
    Equivalent of POST /tasks/
    """
    try:
        # Validate via Pydantic (optional):
        # task = Task(**data)
        # Or skip validation and trust input:
        task = data

        result = db.tasks.insert_one(task)
        task["_id"] = str(result.inserted_id)
        return {"status": "success", "data": task}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def get_user_tasks(data: dict):
    """
    Equivalent of GET /tasks/{user_id}
    """
    try:
        user_id = data.get("user_id")
        if not user_id:
            return {"status": "error", "error": "Missing user_id"}

        tasks = list(db.tasks.find({"user_id": user_id}))
        for task in tasks:
            task["_id"] = str(task["_id"])
        return {"status": "success", "data": tasks}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def get_user_activity(data: dict):
    """
    Equivalent of GET /activity/{user_id}
    """
    try:
        user_id = data.get("user_id")
        if not user_id:
            return {"status": "error", "error": "Missing user_id"}

        activities = list(db.user_activity.find({"user_id": user_id}))
        for act in activities:
            act["_id"] = str(act["_id"])
        return {"status": "success", "data": activities}
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def log_activity(data: dict):
    """
    Equivalent of POST /activity/
    """
    try:
        # Validate if needed:
        # activity = UserActivity(**data)
        activity_dict = data
        current_time = datetime.now()
        activity_dict["timestamp"] = current_time

        # Save to DB
        result = db.user_activity.insert_one(activity_dict)
        activity_dict["_id"] = str(result.inserted_id)

        # Call ML logic
        try:
            await ml_processor.process_new_activity(activity_dict)
        except Exception as e:
            print(f"ML processing error: {e}")

        return {"status": "success", "data": activity_dict}
    except Exception as e:
        print(f"Error in log_activity: {e}")
        return {"status": "error", "error": str(e)}

async def get_recommendations(data: dict):
    """
    Equivalent of GET /recommendations/{user_id}
    """
    try:
        user_id = data.get("user_id")
        if not user_id:
            return {"status": "error", "error": "Missing user_id"}

        result = await ml_processor.get_recommendations(user_id)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def parse_input():
    """
    Reads JSON from stdin (Appwrite passes event data as JSON).
    Expects an 'action' field to determine which logic to run,
    and a 'payload' dict for the relevant arguments.
    """
    try:
        raw_data = sys.stdin.read().strip()
        if not raw_data:
            return {}
        event = json.loads(raw_data)
        return event  # e.g. {"action": "...", "payload": {...}}
    except:
        return {}

def main():
    """
    Main entrypoint for our one-shot function.
    1. Parse input from stdin.
    2. Dispatch to correct function based on 'action'.
    3. Print JSON output.
    4. Exit.
    """
    event = parse_input()
    action = event.get("action")
    payload = event.get("payload", {})

    # We'll need asyncio to run our async methods
    import asyncio

    dispatch_map = {
        "create_task": create_task,
        "get_user_tasks": get_user_tasks,
        "get_user_activity": get_user_activity,
        # For async calls, wrap with asyncio
        "log_activity": lambda data: asyncio.run(log_activity(data)),
        "get_recommendations": lambda data: asyncio.run(get_recommendations(data))
    }

    if not action or action not in dispatch_map:
        response = {
            "status": "error",
            "error": f"Unknown or missing action: {action}. "
                     f"Available: {list(dispatch_map.keys())}"
        }
        print(json.dumps(response))
        return

    # Invoke the selected function
    result = dispatch_map[action](payload)
    print(json.dumps(result, default=str))  # default=str for datetime serialization

if __name__ == "__main__":
    main()
