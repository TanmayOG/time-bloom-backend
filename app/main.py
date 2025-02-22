from flask import Flask, request, jsonify
from ml.models import MLProcessor
from database.mongodb import db
from models.schemas import Task, UserActivity
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Initialize ML Processor
ml_processor = MLProcessor()

@app.route("/", methods=["GET"])
def root():
    return jsonify({"message": "Welcome to TimeBloom API"})

@app.route("/tasks/", methods=["POST"])
def create_task():
    try:
        task_data = request.get_json()
        task = Task(**task_data)
        task_dict = task.dict()
        result = db.tasks.insert_one(task_dict)
        task_dict["_id"] = str(result.inserted_id)
        return jsonify(task_dict), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/tasks/<user_id>", methods=["GET"])
def get_user_tasks(user_id):
    try:
        tasks = list(db.tasks.find({"user_id": user_id}))
        for task in tasks:
            task["_id"] = str(task["_id"])
        return jsonify(tasks), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/activity/<user_id>", methods=["GET"])
def get_user_activity(user_id):
    try:
        activities = list(db.user_activity.find({"user_id": user_id}))
        for activity in activities:
            activity["_id"] = str(activity["_id"])
        return jsonify(activities), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/activity/", methods=["POST"])
def log_activity():
    try:
        activity_data = request.get_json()
        activity = UserActivity(**activity_data)
        activity_dict = activity.dict()
        current_time = datetime.now()
        activity_dict["timestamp"] = current_time
        result = db.user_activity.insert_one(activity_dict)
        activity_dict["_id"] = str(result.inserted_id)
        
        try:
            ml_processor.process_new_activity(activity_dict)
        except Exception as e:
            print(f"ML Processing error: {e}")
        
        return jsonify(activity_dict), 200
    except Exception as e:
        print(f"Error in log_activity: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/recommendations/<user_id>", methods=["GET"])
def get_recommendations(user_id):
    try:
        recommendations = ml_processor.get_recommendations(user_id)
        return jsonify(recommendations), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# New endpoint: Get all unique users
@app.route("/users/", methods=["GET"])
def get_users():
    try:
        # Get distinct user_ids from tasks or user_activity collections
        task_users = db.tasks.distinct("user_id")
        activity_users = db.user_activity.distinct("user_id")
        # Combine and remove duplicates using a set
        all_users = list(set(task_users + activity_users))
        return jsonify({"users": all_users}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# New endpoint: Get all tasks
@app.route("/tasks/all/", methods=["GET"])
def get_all_tasks():
    try:
        tasks = list(db.tasks.find({}))
        for task in tasks:
            task["_id"] = str(task["_id"])
        return jsonify(tasks), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)