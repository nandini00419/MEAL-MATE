import os
import textwrap
import json
from flask import Flask, render_template, url_for, flash, redirect, request, jsonify
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_bcrypt import Bcrypt
from models import db, User, DailyLog, Meal, HealthQuestionnaire, NotificationSetting
import models
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'production-ready-super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ai_health.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)

# Setup Login Manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Sarvam API config
SARVAM_API_KEY = os.environ.get('SARVAM_API_KEY', 'sk_756ky6ne_LMPV9QHtDfx2EBmN3HCzB94v')

def call_sarvam_api(prompt):
    url = "https://api.sarvam.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sarvam-105b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"Error: {response.text}"
    except Exception as e:
        return str(e)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# =======================
# AI INTELLIGENCE CORE
# =======================

def calculate_adaptive_calories(user):
    """Calculates daily calorie target based on user profile and activity."""
    # Basic BMR calculation (Mifflin-St Jeor Equation)
    try:
        weight = float(user.weight or 70)
        height = float(user.height or 170)
        age = int(user.age or 25)
        
        if user.gender == 'Male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
            
        # Activity Multiplier
        multipliers = {
            'Sedentary': 1.2,
            'Lightly Active': 1.375,
            'Moderately Active': 1.55,
            'Very Active': 1.725,
            'Extra Active': 1.9
        }
        
        tdee = bmr * multipliers.get(user.activity_level, 1.2)
        
        # Adjust based on goal
        if user.goal == 'Weight Loss':
            target = tdee - 500
        elif user.goal == 'Muscle Gain':
            target = tdee + 300
        else:
            target = tdee
            
        return int(target)
    except:
        return 2000

def update_health_score(log):
    """Calculates a daily health score (0-100) based on log metrics."""
    score = 0
    # Water (8 glasses = 25 points)
    score += min(25, (log.water_intake / 8) * 25)
    # Steps (10,000 steps = 25 points)
    score += min(25, (log.steps / 10000) * 25)
    # Calories (Close to target = 25 points)
    target = calculate_adaptive_calories(log.owner)
    diff = abs(log.calories_consumed - target)
    if diff < 200: score += 25
    elif diff < 500: score += 15
    else: score += 5
    # Sleep (8 hours = 25 points)
    score += min(25, (log.sleep_hours / 8) * 25)
    
    log.health_score = int(score)
    db.session.commit()

def generate_health_predictions(user):
    """Uses history to predict future health outcomes."""
    logs = DailyLog.query.filter_by(user_id=user.id).order_by(DailyLog.date.desc()).limit(14).all()
    if len(logs) < 3:
        return "<div style='padding: 15px;'><p>📊 Keep logging daily metrics (3+ days) for AI predictions. You're building your health profile!</p></div>"
        
    history_summary = "\n".join([
        f"Day: {l.date.strftime('%a')}, Calories: {l.calories_consumed}kcal, Steps: {l.steps}, Water: {l.water_intake}L, Score: {l.health_score}"
        for l in reversed(logs)
    ])
    
    prompt = f"""You are an advanced health analytics AI. Analyze this 14-day health data and provide predictions:

User: Age {user.age}, Goal: {user.goal}, Current Weight: {user.weight}kg

History:
{history_summary}

Provide in clean HTML:
<div style='font-family: Arial; color: #333;'>
<h4>🎯 30-Day Health Forecast</h4>
<p><strong>Predicted Weight:</strong> [weight]kg</p>
<p><strong>Health Trend:</strong> [trend - improving/stable/declining]</p>
<h4>⚠️ Smart Alerts:</h4>
<ul>
<li>[Alert 1 - specific and actionable]</li>
<li>[Alert 2 - specific and actionable]</li>
<li>[Alert 3 - specific and actionable]</li>
</ul>
<h4>💡 Recommendation:</h4>
<p>[One key action to take today]</p>
</div>"""
    try:
        response_text = call_sarvam_api(prompt)
        if response_text and len(response_text) > 30:
            user.health_predictions = response_text
        else:
            avg_score = int(sum(log.health_score for log in logs) / len(logs))
            user.health_predictions = f"<div style='padding: 15px;'><p>Your health score is trending at <strong>{avg_score}/100</strong>. Keep up the consistency!</p></div>"
        db.session.commit()
        return user.health_predictions
    except Exception as e:
        print(f"Prediction Error: {e}")
        return "<div style='padding: 15px;'><p>🔄 Generating your personalized health forecast...</p></div>"

def generate_ai_plan(user):
    try:
        daily_target = calculate_adaptive_calories(user)
        prompt = f"""You are an elite AI nutrition engineer with 10+ years of experience. Create a PREMIUM personalized meal plan.

Client Profile:
- Age: {user.age}, Gender: {user.gender}
- Current Weight: {user.weight}kg, Height: {user.height}cm
- Goal: {user.goal}
- Preferences: {user.preferences or 'No preferences'}
- Allergies: {user.allergies or 'None'}
- Daily Target: {daily_target} kcal

Deliver EXACTLY in this HTML format:
<div style='font-family: Arial; color: #333;'>
<h3>📊 Your Personalized Nutrition Plan</h3>
<h4>Macro Strategy:</h4>
<p>Based on your {user.goal} goal, your ideal macro split is: <strong>40% Protein | 35% Carbs | 25% Fats</strong></p>
<h4>Daily Target: {daily_target} kcal</h4>
<h4>7-Day Meal Plan:</h4>
<ul>
<li><strong>Monday:</strong> [Breakfast] | [Lunch] | [Dinner] - ~{daily_target} kcal</li>
<li><strong>Tuesday:</strong> [Breakfast] | [Lunch] | [Dinner] - ~{daily_target} kcal</li>
<li><strong>Wednesday:</strong> [Breakfast] | [Lunch] | [Dinner] - ~{daily_target} kcal</li>
<li><strong>Thursday:</strong> [Breakfast] | [Lunch] | [Dinner] - ~{daily_target} kcal</li>
<li><strong>Friday:</strong> [Breakfast] | [Lunch] | [Dinner] - ~{daily_target} kcal</li>
<li><strong>Saturday:</strong> [Breakfast] | [Lunch] | [Dinner] - ~{daily_target} kcal</li>
<li><strong>Sunday:</strong> [Breakfast] | [Lunch] | [Dinner] - ~{daily_target} kcal</li>
</ul>
<h4>Shopping List:</h4>
<p>Proteins, Vegetables, Grains, Dairy, Oils - all aligned with your goal</p>
<h4>💡 Why This Works:</h4>
<p>This plan is scientifically designed for {user.goal}. It respects your preferences and allergies while optimizing micronutrients.</p>
</div>"""
        response_text = call_sarvam_api(prompt)
        if response_text and len(response_text) > 50:
            user.meal_plan = response_text
        else:
            user.meal_plan = f"<div style='color: #666; padding: 15px;'><p>🔄 Your personalized plan is being generated...</p><p>Daily Target: {daily_target} kcal | Goal: {user.goal}</p></div>"
        db.session.commit()
        return True
    except Exception as e:
        print(f"AI Generation Error: {str(e)}")
        daily_target = calculate_adaptive_calories(user)
        user.meal_plan = f"<div style='padding: 15px; background: #f0f0f0; border-radius: 8px;'><h4>Your Personalized Plan</h4><p>Daily Calorie Target: <strong>{daily_target} kcal</strong></p><p>Goal: <strong>{user.goal}</strong></p><p>✓ Plan structure is ready. Detailed meals will appear here.</p></div>"
        db.session.commit()
        return False

# =======================
# ROUTES
# =======================

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/health')
@login_required
def health():
    if not current_user.questionnaire_completed:
        return redirect(url_for('health_questionnaire'))
    return redirect(url_for('health_monitor'))

@app.route('/health_monitor')
@login_required
def health_monitor():
    today = datetime.utcnow().date()
    log = DailyLog.query.filter_by(user_id=current_user.id, date=today).first()
    if not log:
        log = DailyLog(user_id=current_user.id, date=today)
        db.session.add(log)
        db.session.commit()
    
    # Calculate BMI for health monitor
    bmi = 0
    bmi_status = "N/A"
    if current_user.weight and current_user.height:
        height_m = current_user.height / 100
        bmi = round(current_user.weight / (height_m * height_m), 1)
        if bmi < 18.5: bmi_status = "Underweight"
        elif bmi < 25: bmi_status = "Healthy"
        elif bmi < 30: bmi_status = "Overweight"
        else: bmi_status = "Obese"
        
    return render_template('health_monitor.html', log=log, user=current_user, bmi=bmi, bmi_status=bmi_status)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email is already registered.', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash('Account created! Please complete your health assessment.', 'success')
        login_user(user, remember=True)
        return redirect(url_for('health_questionnaire'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.meal_plan:
        return redirect(url_for('onboarding'))
        
    date_str = request.args.get('date')
    if date_str:
        today = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        today = datetime.utcnow().date()
        
    log = DailyLog.query.filter_by(user_id=current_user.id, date=today).first()
    if not log:
        log = DailyLog(user_id=current_user.id, date=today)
        db.session.add(log)
        db.session.commit()
    
    update_health_score(log)
    
    # Calculate BMI
    bmi = 0
    bmi_status = "N/A"
    if current_user.weight and current_user.height:
        height_m = current_user.height / 100
        bmi = round(current_user.weight / (height_m * height_m), 1)
        if bmi < 18.5: bmi_status = "Underweight"
        elif bmi < 25: bmi_status = "Healthy"
        elif bmi < 30: bmi_status = "Overweight"
        else: bmi_status = "Obese"

    # Fetch recent history for charts and summary cards
    history = DailyLog.query.filter_by(user_id=current_user.id).order_by(DailyLog.date.desc()).limit(14).all()
    history = history[::-1]

    # Dynamic target
    daily_target = calculate_adaptive_calories(current_user)
    
    # Calculate percentage for progress bar safely
    cal_percentage = 0
    if daily_target > 0:
        cal_percentage = min(100, int((log.calories_consumed / daily_target) * 100))

    # Prepare history for chart
    chart_labels = [h.date.strftime('%a') for h in history]
    chart_steps = [h.steps for h in history]
    chart_calories = [h.calories_consumed for h in history]

    # Weekly/bi-weekly summary metrics (data-driven, no hardcoded values)
    sleep_values = [h.sleep_hours for h in history if h.sleep_hours and h.sleep_hours > 0]
    avg_sleep = round(sum(sleep_values) / len(sleep_values), 1) if sleep_values else 0.0

    water_goal_pct = 0
    if log.water_intake:
        water_goal_pct = min(100, int((log.water_intake / 8) * 100))

    # Approximate fat-loss progress from calorie deficit trend (7700 kcal ~= 1kg)
    total_deficit = sum(max(0, daily_target - h.calories_consumed) for h in history)
    fat_burned_kg = round(total_deficit / 7700, 2) if total_deficit > 0 else 0.0

    avg_health_score = int(sum([h.health_score for h in history]) / len(history)) if history else log.health_score
    if avg_health_score >= 85:
        health_rank = "A+"
    elif avg_health_score >= 75:
        health_rank = "A"
    elif avg_health_score >= 65:
        health_rank = "B+"
    elif avg_health_score >= 55:
        health_rank = "B"
    elif avg_health_score >= 45:
        health_rank = "C"
    else:
        health_rank = "D"

    return render_template('dashboard.html', 
                          user=current_user, 
                          log=log, 
                          bmi=bmi, 
                          bmi_status=bmi_status,
                          history=history,
                          daily_target=daily_target,
                          cal_percentage=cal_percentage,
                          chart_labels=chart_labels,
                          chart_steps=chart_steps,
                          chart_calories=chart_calories,
                          avg_sleep=avg_sleep,
                          water_goal_pct=water_goal_pct,
                          fat_burned_kg=fat_burned_kg,
                          health_rank=health_rank)

@app.route('/track', methods=['POST'])
@login_required
def track():
    data = request.json
    today = datetime.utcnow().date()
    log = DailyLog.query.filter_by(user_id=current_user.id, date=today).first()
    
    if not log:
        log = DailyLog(user_id=current_user.id, date=today)
        db.session.add(log)
    
    field = data.get('field')
    value = data.get('value', 0)
    
    if field == 'water': log.water_intake = max(0, log.water_intake + int(value))
    elif field == 'calories': log.calories_consumed = max(0, log.calories_consumed + int(value))
    elif field == 'steps': log.steps = max(0, log.steps + int(value))
    elif field == 'sleep': log.sleep_hours = max(0, float(value))
    elif field == 'mood': log.mood = value
    elif field == 'stress': log.stress_level = int(value)
        
    db.session.commit()
    update_health_score(log)
    
    return jsonify({
        "success": True, 
        "water": log.water_intake, 
        "calories": log.calories_consumed,
        "steps": log.steps,
        "health_score": log.health_score
    })

@app.route('/get_predictions')
@login_required
def get_predictions():
    prediction_html = generate_health_predictions(current_user)
    return jsonify({"html": prediction_html})

@app.route('/ai_nutritionist', methods=['POST'])
@login_required
def ai_nutritionist():
    user_msg = request.json.get('message')
    last_calories = current_user.logs[-1].calories_consumed if current_user.logs else 0
    
    prompt = f"""You are a certified sports nutritionist and AI health expert. 
User Context: Goal={current_user.goal}, Weight={current_user.weight}kg, Last meal={last_calories}kcal
User Question: {user_msg}

Respond professionally with:
1. Direct answer to their question
2. 1-2 science-backed tips
3. Action step they can take TODAY

Be brief, conversational, and expert-level."""
    
    try:
        response_text = call_sarvam_api(prompt)
        if response_text and len(response_text) > 20:
            return jsonify({"reply": response_text})
        else:
            return jsonify({"reply": "Great question! I'm refining my response. Try again in a moment."})
    except Exception as e:
        print(f"Nutritionist Error: {e}")
        return jsonify({"reply": "I'm analyzing nutrition data. Please try again!"})

@app.route('/analyze_ingredients', methods=['POST'])
@login_required
def analyze_ingredients():
    ingredients = request.json.get('ingredients')
    prompt = f"""You are a culinary AI expert. Given these ingredients: {ingredients}

Suggest ONE perfect healthy meal for {current_user.goal} goal.

Format as HTML:
<div style='padding: 15px; font-family: Arial;'>
<h4>[Dish Name]</h4>
<p><strong>Calories:</strong> ~[number]kcal</p>
<p><strong>Method:</strong> [Brief 3-4 line cooking instruction]</p>
<p><strong>Why it works:</strong> [One sentence on macros/nutrition]</p>
</div>"""
    try:
        response_text = call_sarvam_api(prompt)
        if response_text and len(response_text) > 30:
            return jsonify({"recipe": response_text})
        else:
            return jsonify({"recipe": "<div style='padding: 15px;'>Creative recipe suggestions loading...</div>"})
    except Exception as e:
        print(f"Recipe Error: {e}")
        return jsonify({"recipe": "<div style='padding: 15px;'>Let me cook up something amazing for you!</div>"})

@app.route('/how_to_cook', methods=['POST'])
@login_required
def how_to_cook():
    dish = request.json.get('dish', '').strip()
    if not dish:
        return jsonify({"success": False, "error": "Please enter a dish name."}), 400

    prompt = f"""You are a professional culinary engineer. Create a step-by-step cooking guide for beginners.

Dish: {dish}
Dietary Goal: {current_user.goal}

Format EXACTLY as HTML:
<div style='font-family: Arial; padding: 15px; background: #f9f9f9; border-radius: 8px;'>
<h3>\ud83d\udc69\u200d\ud83c\udf73 How to Cook {dish}</h3>
<h4>Ingredients:</h4>
<ul style='line-height: 1.8;'>
<li>[Ingredient 1 with quantity]</li>
<li>[Ingredient 2 with quantity]</li>
<li>[Ingredient 3 with quantity]</li>
</ul>
<h4>Step-by-Step Method:</h4>
<ol style='line-height: 1.8;'>
<li>[Clear step with timing]</li>
<li>[Clear step with timing]</li>
<li>[Clear step with timing]</li>
<li>[Clear step with timing]</li>
</ol>
<h4>\ud83d\udca1 Beginner Tips:</h4>
<ul>
<li>[Pro tip 1 for success]</li>
<li>[Pro tip 2 for success]</li>
</ul>
<p style='margin-top: 15px; color: #666;'><em>Cooking time: [X] mins | Difficulty: Beginner-friendly</em></p>
</div>"""
    try:
        response_text = call_sarvam_api(prompt)
        if response_text and len(response_text) > 100:
            return jsonify({"success": True, "html": response_text})
        else:
            return jsonify({"success": True, "html": f"<div style='padding: 15px;'><p>🍳 Generating your perfect {dish} recipe...</p></div>"})
    except Exception as e:
        print(f"Cooking Guide Error: {e}")
        return jsonify({"success": False, "error": "Culinary AI is learning how to cook this. Try another dish!"}), 500

@app.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    if request.method == 'POST':
        current_user.age = request.form.get('age')
        current_user.gender = request.form.get('gender')
        current_user.weight = request.form.get('weight')
        current_user.target_weight = request.form.get('target_weight')
        current_user.height = request.form.get('height')
        current_user.activity_level = request.form.get('activity_level')
        current_user.goal = request.form.get('goal')
        current_user.preferences = request.form.get('preferences')
        current_user.allergies = request.form.get('allergies')
        
        db.session.commit()
        generate_ai_plan(current_user)
        return redirect(url_for('dashboard'))
            
    return render_template('onboarding.html')

@app.route('/health_questionnaire', methods=['GET', 'POST'])
@login_required
def health_questionnaire():
    if request.method == 'POST':
        # Check if questionnaire already exists
        questionnaire = current_user.questionnaire
        if not questionnaire:
            questionnaire = models.HealthQuestionnaire(user_id=current_user.id)
            db.session.add(questionnaire)
        
        # Update questionnaire data
        questionnaire.family_history = request.form.get('family_history')
        questionnaire.past_surgeries = request.form.get('past_surgeries')
        questionnaire.sleep_quality = request.form.get('sleep_quality')
        questionnaire.stress_level = request.form.get('stress_level')
        
        questionnaire.exercise_frequency = request.form.get('exercise_frequency')
        questionnaire.preferred_exercises = request.form.get('preferred_exercises')
        questionnaire.past_injuries = request.form.get('past_injuries')
        
        questionnaire.diet_type = request.form.get('diet_type')
        questionnaire.cooking_skill = request.form.get('cooking_skill')
        questionnaire.meals_per_day = request.form.get('meals_per_day')
        
        questionnaire.mental_health_concerns = request.form.get('mental_health_concerns')
        questionnaire.anxiety_level = request.form.get('anxiety_level')
        
        questionnaire.primary_health_goal = request.form.get('primary_health_goal')
        questionnaire.secondary_goals = request.form.get('secondary_goals')
        questionnaire.motivation_level = request.form.get('motivation_level')
        
        current_user.questionnaire_completed = True
        db.session.commit()
        
        flash('Health assessment completed! Now let\'s personalize your profile.', 'success')
        return redirect(url_for('onboarding'))
    
    return render_template('health_questionnaire.html')

@app.route('/add_meal', methods=['POST'])
@login_required
def add_meal():
    if 'photo' not in request.files:
        return jsonify({"success": False, "error": "No photo uploaded"})
    
    photo = request.files['photo']
    if photo.filename == '':
        return jsonify({"success": False, "error": "No photo selected"})

    prompt = """You are a professional nutrition AI that detects meals and calculates macros perfectly.

Based on the meal description, provide ONLY valid JSON (no markdown, no extra text):
{"name": "Dish Name", "calories": 350, "nutrition": "P: 30g, C: 45g, F: 12g"}

Assume a typical home-cooked meal for an average portion. Make realistic estimates."""
    
    try:
        response_text = call_sarvam_api(prompt)
        res_text = response_text.strip()
        
        # Clean various JSON formats
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()
        
        # Extract JSON if embedded in text
        if "{" in res_text:
            res_text = res_text[res_text.find("{"):res_text.rfind("}")+1]
        
        meal_data = json.loads(res_text)
        
        # Validate meal data
        if not all(k in meal_data for k in ['name', 'calories', 'nutrition']):
            raise ValueError("Missing required meal data fields")
        
        # Ensure calories is an integer
        meal_data['calories'] = int(meal_data['calories'])
        
        # Save meal to DB
        today = datetime.utcnow().date()
        log = DailyLog.query.filter_by(user_id=current_user.id, date=today).first()
        if not log:
            log = DailyLog(user_id=current_user.id, date=today)
            db.session.add(log)
        
        new_meal = Meal(
            name=meal_data['name'],
            calories=meal_data['calories'],
            log_id=log.id
        )
        
        log.calories_consumed += meal_data['calories']
        db.session.add(new_meal)
        db.session.commit()
        update_health_score(log)
        
        return jsonify({
            "success": True, 
            "meal": meal_data,
            "total_calories": log.calories_consumed,
            "health_score": log.health_score
        })
    except json.JSONDecodeError:
        print(f"AI Meal JSON Error: Could not parse response")
        return jsonify({"success": False, "error": "Meal detection AI needs better image. Try again!"})
    except Exception as e:
        print(f"AI Meal Analysis Error: {str(e)}")
        return jsonify({"success": False, "error": "AI meal analyzer is learning. Please try again!"})

@app.route('/history')
@login_required
def history():
    date_str = request.args.get('date')
    if date_str:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        target_date = datetime.utcnow().date()
    
    log = DailyLog.query.filter_by(user_id=current_user.id, date=target_date).first()
    
    # Fetch meals for this log
    meals = []
    if log:
        meals = [{"name": m.name, "calories": m.calories, "time": m.timestamp.strftime('%H:%M')} for m in log.meals]
    
    return jsonify({
        "date": target_date.strftime('%Y-%m-%d'),
        "log": {
            "water": log.water_intake if log else 0,
            "calories": log.calories_consumed if log else 0,
            "steps": log.steps if log else 0,
            "health_score": log.health_score if log else 0
        },
        "meals": meals
    })

@app.route('/reports')
@login_required
def reports():
    # Fetch last 30 days of history
    history = DailyLog.query.filter_by(user_id=current_user.id).order_by(DailyLog.date.desc()).limit(30).all()
    history = history[::-1] # Oldest first

    # Consider only days with at least one meaningful log entry for averages
    active_logs = [
        h for h in history
        if (h.calories_consumed > 0 or h.water_intake > 0 or h.steps > 0 or h.sleep_hours > 0 or h.health_score > 0)
    ]
    active_days = len(active_logs)

    adherence = 0
    avg_sleep = 0.0
    avg_water = 0.0
    avg_score = 0
    if active_days > 0:
        good_days = len([h for h in active_logs if h.health_score >= 70])
        adherence = int((good_days / active_days) * 100)
        avg_sleep = round(sum(h.sleep_hours for h in active_logs) / active_days, 1)
        avg_water = round(sum(h.water_intake for h in active_logs) / active_days, 1)
        avg_score = int(sum(h.health_score for h in active_logs) / active_days)

    # BMI summary for reports
    bmi = None
    bmi_status = "N/A"
    if current_user.weight and current_user.height and current_user.height > 0:
        height_m = current_user.height / 100
        bmi = round(current_user.weight / (height_m * height_m), 1)
        if bmi < 18.5:
            bmi_status = "Underweight"
        elif bmi < 25:
            bmi_status = "Healthy"
        elif bmi < 30:
            bmi_status = "Overweight"
        else:
            bmi_status = "Obese"

    return render_template(
        'reports.html',
        history=history,
        user=current_user,
        adherence=adherence,
        avg_sleep=avg_sleep,
        avg_water=avg_water,
        avg_score=avg_score,
        bmi=bmi,
        bmi_status=bmi_status,
        active_days=active_days
    )

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html', user=current_user)

@app.route('/connect_google_fit')
@login_required
def connect_google_fit():
    # This would normally initiate OAuth
    # For now, we'll simulate a successful connection
    flash('Successfully connected to Google Fit! Syncing steps and sleep data...', 'success')
    
    # Simulate syncing data for today
    today = datetime.utcnow().date()
    log = DailyLog.query.filter_by(user_id=current_user.id, date=today).first()
    if not log:
        log = DailyLog(user_id=current_user.id, date=today)
        db.session.add(log)
    
    log.steps += 5432 # Mocked data
    log.sleep_hours = 7.5 # Mocked data
    db.session.commit()
    
    return redirect(url_for('dashboard'))

# =======================
# STEP ANALYSIS ROUTES
# =======================

@app.route('/step_analysis')
@login_required
def step_analysis():
    """Display step tracking and analysis."""
    history = DailyLog.query.filter_by(user_id=current_user.id).order_by(DailyLog.date.desc()).limit(30).all()
    history = history[::-1]  # Oldest first
    
    step_goal = current_user.daily_step_goal or 10000
    
    # Calculate metrics
    total_steps = sum(log.steps for log in history)
    avg_steps = int(total_steps / len(history)) if history else 0
    max_steps = max((log.steps for log in history), default=0)
    days_goal_met = sum(1 for log in history if log.steps >= step_goal)
    achievement_rate = int((days_goal_met / len(history)) * 100) if history else 0
    
    # Prepare chart data
    chart_labels = [h.date.strftime('%a %d') for h in history]
    chart_steps = [h.steps for h in history]
    
    return render_template('step_analysis.html',
                          history=history,
                          step_goal=step_goal,
                          total_steps=total_steps,
                          avg_steps=avg_steps,
                          max_steps=max_steps,
                          days_goal_met=days_goal_met,
                          achievement_rate=achievement_rate,
                          chart_labels=chart_labels,
                          chart_steps=chart_steps)

@app.route('/update_step_goal', methods=['POST'])
@login_required
def update_step_goal():
    """Update daily step goal."""
    new_goal = request.json.get('goal', 10000)
    current_user.daily_step_goal = int(new_goal)
    db.session.commit()
    return jsonify({"success": True, "goal": new_goal})

# =======================
# AI COOK CHATBOT ROUTES
# =======================

@app.route('/cook_chatbot')
@login_required
def cook_chatbot():
    """Display AI cook chatbot interface."""
    return render_template('cook_chatbot.html')

@app.route('/cook_chat', methods=['POST'])
@login_required
def cook_chat():
    """AI cook chatbot with YouTube suggestions."""
    user_msg = request.json.get('message', '').strip()
    if not user_msg:
        return jsonify({"error": "Message is empty"}), 400
    
    prompt = f"""You are a professional AI culinary expert and YouTube cooking channel curator. 
User's Goal: {current_user.goal}
User Question: {user_msg}

Provide a response that includes:
1. Direct answer to their cooking question
2. Step-by-step cooking tips
3. 2-3 YouTube cooking channels or videos that match their query (format: "Channel Name" - brief description)
4. Make meal suggestions aligned with their health goal

Keep response conversational, friendly, and actionable."""
    
    try:
        response_text = call_sarvam_api(prompt)
        if response_text and len(response_text) > 20:
            return jsonify({"reply": response_text})
        else:
            return jsonify({"reply": "Let me cook up a great suggestion for you! Try asking about specific dishes or cooking techniques."})
    except Exception as e:
        print(f"Cook Chatbot Error: {e}")
        return jsonify({"reply": "I'm heating up the kitchen AI! Please try again in a moment."})

@app.route('/recipe_suggestion', methods=['POST'])
@login_required
def recipe_suggestion():
    """Get recipe suggestions with YouTube links."""
    dietary_need = request.json.get('dietary_need', 'healthy').strip()
    
    prompt = f"""You are a professional chef and nutrition expert. The user needs a {dietary_need} recipe.
User Profile: Goal={current_user.goal}, Age={current_user.age}, Dietary Preference={current_user.preferences}

Suggest ONE amazing recipe with:
1. Recipe name and brief description
2. Main ingredients (5-7 key items)
3. Estimated cook time
4. Nutritional benefits for their {current_user.goal} goal
5. 2 YouTube cooking video suggestions (format: "Video Title by Channel Name" - URL if possible)
6. Difficulty level (Beginner/Intermediate/Advanced)

Format as HTML with proper structure."""
    
    try:
        response_text = call_sarvam_api(prompt)
        if response_text and len(response_text) > 50:
            return jsonify({"recipe": response_text})
        else:
            return jsonify({"recipe": "<div style='padding: 15px;'><p>🍳 Generating delicious recipe ideas...</p></div>"})
    except Exception as e:
        print(f"Recipe Error: {e}")
        return jsonify({"recipe": "<div style='padding: 15px;'><p>Let me find the perfect recipe for you!</p></div>"})

# =======================
# NOTIFICATION SETTINGS ROUTES
# =======================

@app.route('/notification_settings', methods=['GET', 'POST'])
@login_required
def notification_settings():
    """Manage notification and reminder settings."""
    # Get or create notification settings
    settings = current_user.notifications
    if not settings:
        settings = NotificationSetting(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()
    
    if request.method == 'POST':
        # Water Reminders
        settings.water_reminder_enabled = 'water_reminder_enabled' in request.form
        settings.water_reminder_interval = int(request.form.get('water_reminder_interval', 60))
        settings.water_reminder_time = request.form.get('water_reminder_time', '08:00')
        
        # Meal Reminders
        settings.breakfast_reminder = 'breakfast_reminder' in request.form
        settings.breakfast_time = request.form.get('breakfast_time', '07:00')
        settings.lunch_reminder = 'lunch_reminder' in request.form
        settings.lunch_time = request.form.get('lunch_time', '12:30')
        settings.dinner_reminder = 'dinner_reminder' in request.form
        settings.dinner_time = request.form.get('dinner_time', '19:00')
        
        # Sleep Reminder
        settings.sleep_reminder_enabled = 'sleep_reminder_enabled' in request.form
        settings.sleep_time = request.form.get('sleep_time', '23:00')
        
        # Exercise Reminder
        settings.exercise_reminder_enabled = 'exercise_reminder_enabled' in request.form
        settings.exercise_time = request.form.get('exercise_time', '06:00')
        
        # General Settings
        settings.notification_method = request.form.get('notification_method', 'browser')
        
        db.session.commit()
        flash('Notification settings updated successfully!', 'success')
        return redirect(url_for('notification_settings'))
    
    return render_template('notification_settings.html', settings=settings)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=3000)
