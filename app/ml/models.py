# app/ml/models.py
import numpy as np
import io
import joblib  # Also add this import
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import pandas as pd
from datetime import datetime, time
from database.mongodb import db
from config import storage
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
import os

from appwrite.input_file import InputFile  # Add this import at the top

class ModelStorage:
    def __init__(self):
        self.storage = storage
        self.bucket_id = '67b05f850003e4e960c3'
        self.model_dir = 'models'
        os.makedirs(self.model_dir, exist_ok=True)

    def save_model(self, model, name):
        try:
            temp_path = os.path.join(self.model_dir, f"{name}.joblib")
            print(f"Saving model to temporary path: {temp_path}")
            
            joblib.dump(model, temp_path)
            print("Model dumped to temporary file successfully")
            
            # Create InputFile object
            input_file = InputFile.from_path(temp_path)
            print("Created InputFile object")
            
            print("Uploading to Appwrite...")
            self.storage.create_file(
                bucket_id=self.bucket_id,
                file_id=name,
                file=input_file
            )
            print("Upload successful")
            
            os.remove(temp_path)
            print("Temporary file cleaned up")
            return True
            
        except Exception as e:
            print(f"Error saving model: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

    def load_model(self, name):
        try:
            file_data = self.storage.get_file_download(
                bucket_id=self.bucket_id,
                file_id=name
            )
            return joblib.load(io.BytesIO(file_data))
        except Exception as e:
            print(f"Error loading model: {e}")
            return None       
        
class ProductivityPredictor:
    def __init__(self):
        self.model_storage = ModelStorage()
        self.model = self._load_or_create_model()
        self.scaler = StandardScaler()
    
    
    def _load_or_create_model(self):
        model = self.model_storage.load_model('productivity_model')
        if model is None:
            model = RandomForestRegressor()
        return model
    
    def _load_or_create_scaler(self):
        scaler = self.model_storage.load_model('productivity_scaler')
        if scaler is None:
            scaler = StandardScaler()
            # Initialize with some default data to avoid the "not fitted" error
            default_features = np.array([[12, 3, 1], [15, 3, 1], [9, 3, 1]])  # Example data
            scaler.fit(default_features)
        return scaler
        
    def prepare_features(self, activities):
        features = []
        for activity in activities:
            try:
                # Ensure timestamp is a datetime object
                timestamp = self._get_timestamp(activity)
                if timestamp is None:
                    continue
                    
                hour = timestamp.hour
                day = timestamp.weekday()
                energy = self._encode_energy(activity['energy_level'])
                features.append([hour, day, energy])
            except Exception as e:
                print(f"Error processing activity in prepare_features: {e}")
                continue
                
        return np.array(features) if features else np.array([])
    
    def _encode_energy(self, energy_level):
        energy_map = {'low': 0, 'medium': 1, 'high': 2}
        return energy_map.get(energy_level, 1)
    
    def _calculate_productivity_scores(self, activities):
        """Calculate productivity scores based on user activities and task completions"""
        scores = []
        for activity in activities:
            try:
                # Base score from energy level
                base_score = self._encode_energy(activity['energy_level'])
                
                # Get timestamp
                timestamp = self._get_timestamp(activity)
                if timestamp is None:
                    continue
                    
                # Time-based adjustment
                time_score = self._calculate_time_score(timestamp.hour)
                
                # Final score (normalized between 0 and 1)
                final_score = (base_score + time_score) / 4
                scores.append(final_score)
            except Exception as e:
                print(f"Error calculating productivity score: {e}")
                continue
                
        return np.array(scores)
    
    def _calculate_time_score(self, hour):
        """Calculate time-based productivity score"""
        # Assuming peak productivity hours are 9-11 AM and 3-5 PM
        if 9 <= hour <= 11:
            return 2
        elif 15 <= hour <= 17:
            return 1.5
        elif 12 <= hour <= 14:  # Lunch time
            return 0.5
        else:
            return 1

    def _get_optimal_times(self, hours, predictions):
        """Get optimal time slots based on predictions"""
        # No need to handle multiple columns since we're using regression
        scores = predictions
        
        # Find top 3 time slots
        top_indices = np.argsort(scores)[-3:][::-1]
        
        optimal_times = []
        for idx in top_indices:
            hour = hours[idx]
            score = float(scores[idx])
            
            start_time = f"{hour:02d}:00"
            end_time = f"{(hour + 1):02d}:00"
            
            optimal_times.append({
                "start_time": start_time,
                "end_time": end_time,
                "productivity_score": score,
                "confidence": "high" if score > 0.7 else "medium" if score > 0.4 else "low"
            })
            
        return optimal_times 
   
    def train(self, user_activities):
        if not user_activities:
            return
            
        features = self.prepare_features(user_activities)
        if len(features) == 0:
            print("No valid features to train on")
            return
            
        productivity_scores = self._calculate_productivity_scores(user_activities)
        if len(productivity_scores) == 0:
            print("No valid productivity scores to train on")
            return
            
        try:
            self.scaler.fit(features)
            scaled_features = self.scaler.transform(features)
            self.model.fit(scaled_features, productivity_scores)
            
            # Save both model and scaler
            self.model_storage.save_model(self.model, 'productivity_model')
            self.model_storage.save_model(self.scaler, 'productivity_scaler')
        except Exception as e:
            print(f"Error in training: {e}")
    
    def predict_best_time(self, user_id, task_difficulty):
        try:
            # Predict productivity for all hours of the day
            hours = np.arange(24)
            current_day = datetime.now().weekday()
            
            test_features = []
            for hour in hours:
                test_features.append([hour, current_day, 1])  # Assuming medium energy
            
            test_features = np.array(test_features)
            
            # Check if scaler is fitted
            if not hasattr(self.scaler, 'mean_'):
                # If not fitted, fit with the test features
                self.scaler.fit(test_features)
            
            scaled_features = self.scaler.transform(test_features)
            predictions = self.model.predict(scaled_features)
            
            return self._get_optimal_times(hours, predictions)
        except Exception as e:
            print(f"Error in predict_best_time: {e}")
            return []
    
    def _get_timestamp(self, activity):
        timestamp = activity.get('timestamp')
        if timestamp is None:
            return None
            
        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                return None
        return None

class TaskMatcher:
    def __init__(self):
        self.task_scores = {}
        self.productivity_predictor = ProductivityPredictor()
    
    def update_task_scores(self, user_id, completed_tasks):
        """Update success rates for different task types based on completion data"""
        for task in completed_tasks:
            try:
                # Safely get required fields with defaults
                task_type = task.get('task_type', 'unknown')
                difficulty = task.get('difficulty', 'medium')
                timestamp = task.get('created_at') or task.get('timestamp')
                
                if not timestamp:
                    continue
                    
                key = (task_type, difficulty, self._get_time_bucket(timestamp))
                
                success = task.get('completed', False)
                if key not in self.task_scores:
                    self.task_scores[key] = {'success': 0, 'total': 0}
                
                self.task_scores[key]['total'] += 1
                if success:
                    self.task_scores[key]['success'] += 1
                    
            except Exception as e:
                print(f"Error processing task in update_task_scores: {e}")
                continue
    
    def _get_time_bucket(self, timestamp):
        """Convert time to morning/afternoon/evening bucket"""
        hour = timestamp.hour
        if hour < 12:
            return 'morning'
        elif hour < 17:
            return 'afternoon'
        else:
            return 'evening'
    
    def get_task_recommendations(self, user_id, current_time, energy_level):
        """Recommend tasks based on current context"""
        time_bucket = self._get_time_bucket(current_time)
        recommendations = []
        
        for (task_type, difficulty, tb), scores in self.task_scores.items():
            if tb == time_bucket:
                success_rate = scores['success'] / scores['total'] if scores['total'] > 0 else 0
                if self._is_suitable(difficulty, energy_level):
                    recommendations.append({
                        'task_type': task_type,
                        'difficulty': difficulty,
                        'score': success_rate
                    })
        
        return sorted(recommendations, key=lambda x: x['score'], reverse=True)
    
    def _is_suitable(self, task_difficulty, energy_level):
        """Check if task difficulty matches energy level"""
        difficulty_map = {'low': 0, 'medium': 1, 'high': 2}
        energy_map = {'low': 0, 'medium': 1, 'high': 2}
        
        task_level = difficulty_map.get(task_difficulty, 1)
        energy = energy_map.get(energy_level, 1)
        
        return abs(task_level - energy) <= 1

    
    async def process_new_activity(self, activity):
        """Process new user activity data"""
        # Update models with new activity data
        user_activities = await self._get_user_activities(activity['user_id'])
        self.productivity_predictor.train(user_activities)
    
    async def get_recommendations(self, user_id, current_time=None):
        """Get task recommendations based on current context"""
        if current_time is None:
            current_time = datetime.now()
            
        # Get user's current energy level
        energy_level = await self._get_current_energy(user_id)
        
        # Get task recommendations
        recommendations = self.task_matcher.get_task_recommendations(
            user_id, current_time, energy_level
        )
        
        # Get optimal times for tasks
        best_times = self.productivity_predictor.predict_best_time(
            user_id, recommendations[0]['difficulty'] if recommendations else 'medium'
        )
        
        return {
            'task_recommendations': recommendations,
            'best_times': best_times
        }

class MLProcessor:
    def __init__(self):
        self.productivity_predictor = None
        self.task_matcher = None
    
    def _lazy_load_predictors(self):
        if not self.productivity_predictor:
            self.productivity_predictor = ProductivityPredictor()
        if not self.task_matcher:
            self.task_matcher = TaskMatcher()
    
    async def _get_user_activities(self, user_id):
        """Fetch user activities from database"""
        # Get activities from last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        activities = list(db.user_activity.find({
            "user_id": user_id,
            "timestamp": {"$gte": thirty_days_ago}
        }))
        return activities
    
    async def _get_user_tasks(self, user_id):
        """Fetch user tasks from database"""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        tasks = list(db.tasks.find({
            "user_id": user_id,
            "created_at": {"$gte": thirty_days_ago}
        }))
        
        # Add logging to inspect task structure
        print("Sample task structure:", tasks[0] if tasks else "No tasks found")
        
        return tasks
        
    async def _get_current_energy(self, user_id):
        """Get user's most recent energy level"""
        latest_activity = db.user_activity.find_one(
            {"user_id": user_id},
            sort=[("timestamp", -1)]
        )
        return latest_activity["energy_level"] if latest_activity else "medium"
    
    async def process_new_activity(self, activity):
        """Process new user activity data"""
        try:
            
            db.user_activity.insert_one(activity)
            
            user_activities = await self._get_user_activities(activity['user_id'])
            user_tasks = await self._get_user_tasks(activity['user_id'])
            
            self.productivity_predictor.train(user_activities)
        
            if user_tasks:
                self.task_matcher.update_task_scores(activity['user_id'], user_tasks)
                print("Task scores updated")
            else:
                print("No tasks to update scores")
                
            print("Activity processing complete")
            
            return True
        except Exception as e:
            print(f"Error processing activity: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def get_recommendations(self, user_id, current_time=None):
        """Get task recommendations based on current context"""
        try:
            if current_time is None:
                current_time = datetime.now()
                
            # Get user's current energy level
            energy_level = await self._get_current_energy(user_id)
            
            # Get latest activity for location context
            latest_activity = db.user_activity.find_one(
                {"user_id": user_id},
                sort=[("timestamp", -1)]
            )
            current_location = latest_activity.get("location", {}).get("type") if latest_activity else "unknown"
            
            # Get task recommendations
            recommendations = self.task_matcher.get_task_recommendations(
                user_id, current_time, energy_level
            )
            
            # Get optimal times for tasks
            best_times = self.productivity_predictor.predict_best_time(
                user_id, recommendations[0]['difficulty'] if recommendations else 'medium'
            )
            
            return {
                'current_context': {
                    'time': current_time,
                    'energy_level': energy_level,
                    'location': current_location
                },
                'task_recommendations': recommendations,
                'best_times': best_times
            }
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return {
                'task_recommendations': [],
                'best_times': [],
                'error': str(e)
            }