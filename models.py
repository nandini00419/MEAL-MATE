from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    
    # Profile Data
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    height = db.Column(db.Float, nullable=True)
    weight = db.Column(db.Float, nullable=True)
    target_weight = db.Column(db.Float, nullable=True)
    activity_level = db.Column(db.String(50), nullable=True)
    goal = db.Column(db.String(50), nullable=True)
    preferences = db.Column(db.String(100), nullable=True)
    allergies = db.Column(db.String(100), nullable=True)
    
    # Health Monitoring Profile
    blood_type = db.Column(db.String(10), nullable=True)
    medical_conditions = db.Column(db.Text, nullable=True)
    medications = db.Column(db.Text, nullable=True)
    emergency_contact = db.Column(db.String(100), nullable=True)
    
    # Plans & Predictions
    meal_plan = db.Column(db.Text, nullable=True)
    fitness_plan = db.Column(db.Text, nullable=True)
    health_predictions = db.Column(db.Text, nullable=True) # AI generated text
    wellness_report = db.Column(db.Text, nullable=True)  # AI comprehensive wellness report
    
    date_registered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Questionnaire & Settings
    questionnaire_completed = db.Column(db.Boolean, default=False)
    daily_step_goal = db.Column(db.Integer, default=10000)
    
    # Relationships
    logs = db.relationship('DailyLog', backref='owner', lazy=True)
    weight_logs = db.relationship('WeightLog', backref='owner', lazy=True)
    health_alerts = db.relationship('HealthAlert', backref='owner', lazy=True)
    questionnaire = db.relationship('HealthQuestionnaire', backref='user', lazy=True, uselist=False)
    notifications = db.relationship('NotificationSetting', backref='user', lazy=True, uselist=False)

class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    water_intake = db.Column(db.Integer, default=0) # in glasses
    calories_consumed = db.Column(db.Integer, default=0)
    steps = db.Column(db.Integer, default=0)
    sleep_hours = db.Column(db.Float, default=0)
    mood = db.Column(db.String(50), nullable=True) # happy, sad, etc.
    stress_level = db.Column(db.Integer, default=0) # 1-10
    health_score = db.Column(db.Integer, default=0) # 1-100 calculated daily
    
    # Health Monitoring vitals
    heart_rate = db.Column(db.Integer, default=0)  # bpm
    blood_pressure_sys = db.Column(db.Integer, default=0)  # systolic
    blood_pressure_dia = db.Column(db.Integer, default=0)  # diastolic
    body_temperature = db.Column(db.Float, default=0)  # celsius
    blood_oxygen = db.Column(db.Integer, default=0)  # SpO2 percentage
    
    # Exercise tracking
    exercise_minutes = db.Column(db.Integer, default=0)
    exercise_type = db.Column(db.String(100), nullable=True)
    calories_burned = db.Column(db.Integer, default=0)
    
    # Mental wellness
    mood_notes = db.Column(db.Text, nullable=True)
    energy_level = db.Column(db.Integer, default=0)  # 1-10
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationship with individual meals
    meals = db.relationship('Meal', backref='daily_log', lazy=True)

    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='_user_date_uc'),)

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Integer, nullable=False)
    protein = db.Column(db.Float, default=0)
    carbs = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)
    meal_type = db.Column(db.String(30), nullable=True)  # breakfast, lunch, dinner, snack
    image_url = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    log_id = db.Column(db.Integer, db.ForeignKey('daily_log.id'), nullable=False)

class WeightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class HealthAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # warning, critical, info
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class HealthQuestionnaire(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Health History
    family_history = db.Column(db.Text, nullable=True)  # Any hereditary conditions
    past_surgeries = db.Column(db.Text, nullable=True)
    sleep_quality = db.Column(db.String(50), nullable=True)  # poor, fair, good, excellent
    stress_level = db.Column(db.String(50), nullable=True)  # low, moderate, high
    
    # Fitness History
    exercise_frequency = db.Column(db.String(50), nullable=True)  # never, rarely, 1-3x/week, 4-5x/week, daily
    preferred_exercises = db.Column(db.Text, nullable=True)
    past_injuries = db.Column(db.Text, nullable=True)
    
    # Dietary Info
    diet_type = db.Column(db.String(50), nullable=True)  # omnivore, vegetarian, vegan, keto, etc.
    cooking_skill = db.Column(db.String(50), nullable=True)  # beginner, intermediate, advanced
    meals_per_day = db.Column(db.Integer, nullable=True)
    
    # Mental Health
    mental_health_concerns = db.Column(db.Text, nullable=True)
    anxiety_level = db.Column(db.String(50), nullable=True)  # none, mild, moderate, severe
    
    # Health Goals (detailed)
    primary_health_goal = db.Column(db.String(100), nullable=True)
    secondary_goals = db.Column(db.Text, nullable=True)
    motivation_level = db.Column(db.Integer, nullable=True)  # 1-10 scale
    
    date_completed = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class NotificationSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Water Reminders
    water_reminder_enabled = db.Column(db.Boolean, default=True)
    water_reminder_interval = db.Column(db.Integer, default=60)  # minutes
    water_reminder_time = db.Column(db.String(5), default="08:00")  # start time HH:MM
    
    # Meal Reminders
    breakfast_reminder = db.Column(db.Boolean, default=True)
    breakfast_time = db.Column(db.String(5), default="07:00")
    lunch_reminder = db.Column(db.Boolean, default=True)
    lunch_time = db.Column(db.String(5), default="12:30")
    dinner_reminder = db.Column(db.Boolean, default=True)
    dinner_time = db.Column(db.String(5), default="19:00")
    
    # Sleep Reminders
    sleep_reminder_enabled = db.Column(db.Boolean, default=True)
    sleep_time = db.Column(db.String(5), default="23:00")
    
    # Exercise Reminders
    exercise_reminder_enabled = db.Column(db.Boolean, default=True)
    exercise_time = db.Column(db.String(5), default="06:00")
    
    # General Settings
    notification_method = db.Column(db.String(50), default="browser")  # browser, email, both
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
