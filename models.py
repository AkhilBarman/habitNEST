from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id', ''))
        self.username = user_data.get('username', '')
        self.email = user_data.get('email', '')
        self.password_hash = user_data.get('password_hash', '')
        self.created_at = user_data.get('created_at', datetime.utcnow())
        self.habits = user_data.get('habits', [])

    def get_id(self):
        return str(self.id)

    @staticmethod
    def create_user(username, email, password):
        from app import mongo
        user_data = {
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.utcnow(),
            'habits': []
        }
        result = mongo.db.users.insert_one(user_data)
        user_data['_id'] = result.inserted_id
        return User(user_data)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_email(email):
        from app import mongo
        user_data = mongo.db.users.find_one({'email': email})
        if user_data:
            return User(user_data)
        return None

class Habit:
    def __init__(self, habit_data):
        self.id = str(habit_data.get('_id', ''))
        self.user_id = str(habit_data.get('user_id', ''))
        self.name = habit_data.get('name', '')
        self.category = habit_data.get('category', '')
        self.description = habit_data.get('description', '')
        self.frequency = habit_data.get('frequency', 'daily')
        self.created_at = habit_data.get('created_at', datetime.utcnow())
        self.completions = habit_data.get('completions', [])
        self.streak = habit_data.get('streak', 0)

    @staticmethod
    def create_habit(user_id, name, category, description, frequency):
        from app import mongo
        habit_data = {
            'user_id': ObjectId(user_id),
            'name': name,
            'category': category,
            'description': description,
            'frequency': frequency,
            'created_at': datetime.utcnow(),
            'completions': [],
            'streak': 0
        }
        result = mongo.db.habits.insert_one(habit_data)
        habit_data['_id'] = result.inserted_id
        return Habit(habit_data)

    @staticmethod
    def get_user_habits(user_id):
        from app import mongo
        habits = mongo.db.habits.find({'user_id': ObjectId(user_id)})
        return [Habit(habit) for habit in habits]

    def complete(self):
        from app import mongo
        completion = {
            'date': datetime.utcnow(),
            'timestamp': datetime.utcnow()
        }
        self.completions.append(completion)
        mongo.db.habits.update_one(
            {'_id': ObjectId(self.id)},
            {'$push': {'completions': completion}}
        )
        self.update_streak()

    def update_streak(self):
        from app import mongo
        if not self.completions:
            return

        # Sort completions by date
        sorted_completions = sorted(self.completions, key=lambda x: x['date'])
        current_streak = 1
        last_completion = sorted_completions[-1]['date']

        # Check if streak is broken
        for i in range(len(sorted_completions) - 2, -1, -1):
            prev_completion = sorted_completions[i]['date']
            days_diff = (last_completion - prev_completion).days

            if self.frequency == 'daily' and days_diff == 1:
                current_streak += 1
            elif self.frequency == 'weekly' and days_diff <= 7:
                current_streak += 1
            elif self.frequency == 'monthly' and days_diff <= 30:
                current_streak += 1
            else:
                break

        self.streak = current_streak
        mongo.db.habits.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': {'streak': current_streak}}
        )

    def delete(self):
        from app import mongo
        mongo.db.habits.delete_one({'_id': ObjectId(self.id)})

class Analytics:
    def __init__(self, analytics_data):
        self.id = str(analytics_data.get('_id', ''))
        self.user_id = str(analytics_data.get('user_id', ''))
        self.total_habits = analytics_data.get('total_habits', 0)
        self.total_completions = analytics_data.get('total_completions', 0)
        self.completion_rate = analytics_data.get('completion_rate', 0)
        self.weekly_data = analytics_data.get('weekly_data', {})
        self.updated_at = analytics_data.get('updated_at', datetime.utcnow())

    @staticmethod
    def create_or_update(user_id, habits_list):
        from app import mongo
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        # Initialize weekly data
        weekly_data = {
            'Mon': 0, 'Tue': 0, 'Wed': 0, 'Thu': 0, 'Fri': 0, 'Sat': 0, 'Sun': 0
        }

        # Count completions for current week
        total_completions = 0
        for habit in habits_list:
            for completion in habit.completions:
                completion_date = completion['date']
                if start_of_week <= completion_date <= end_of_week:
                    day_name = completion_date.strftime('%a')
                    weekly_data[day_name] += 1
                total_completions += 1

        # Calculate completion rate for the week
        total_possible = len(habits_list) * 7  # 7 days in a week
        completion_rate = (sum(weekly_data.values()) / total_possible * 100) if total_possible > 0 else 0

        analytics_data = {
            'user_id': user_id,
            'total_habits': len(habits_list),
            'total_completions': total_completions,
            'completion_rate': round(completion_rate, 1),
            'weekly_data': weekly_data,
            'updated_at': now
        }

        # Update or insert analytics
        result = mongo.db.analytics.update_one(
            {'user_id': user_id},
            {'$set': analytics_data},
            upsert=True
        )
        
        if result.upserted_id:
            analytics_data['_id'] = result.upserted_id
        else:
            analytics_data['_id'] = mongo.db.analytics.find_one({'user_id': user_id})['_id']
            
        return Analytics(analytics_data)

    @staticmethod
    def get_user_analytics(user_id):
        from app import mongo
        analytics_data = mongo.db.analytics.find_one({'user_id': user_id})
        if analytics_data:
            return Analytics(analytics_data)
        return None

class Achievement:
    def __init__(self, achievement_data):
        self.id = str(achievement_data.get('_id', ''))
        self.user_id = str(achievement_data.get('user_id', ''))
        self.title = achievement_data.get('title', '')
        self.description = achievement_data.get('description', '')
        self.icon = achievement_data.get('icon', '')
        self.completed = achievement_data.get('completed', False)
        self.progress = achievement_data.get('progress', 0)
        self.completion_date = achievement_data.get('completion_date')
        self.created_at = achievement_data.get('created_at', datetime.utcnow())

    @staticmethod
    def create_or_update(user_id, habits_list):
        from app import mongo
        
        # Define achievements
        achievements_data = [
            {
                'user_id': user_id,
                'title': 'First Habit',
                'description': 'Create your first habit',
                'icon': 'bx-target-lock',
                'completed': len(habits_list) > 0,
                'progress': 100 if len(habits_list) > 0 else 0,
                'completion_date': habits_list[0].created_at.strftime('%Y-%m-%d') if habits_list else None,
                'created_at': datetime.utcnow()
            },
            {
                'user_id': user_id,
                'title': 'Streak Master',
                'description': 'Maintain a 7-day streak',
                'icon': 'bx-flame',
                'completed': any(habit.streak >= 7 for habit in habits_list),
                'progress': min(100, max((habit.streak / 7) * 100 for habit in habits_list) if habits_list else 0),
                'completion_date': next((habit.completions[-1]['date'].strftime('%Y-%m-%d') 
                                      for habit in habits_list if habit.streak >= 7), None),
                'created_at': datetime.utcnow()
            },
            {
                'user_id': user_id,
                'title': 'Habit Builder',
                'description': 'Create 5 different habits',
                'icon': 'bx-layer',
                'completed': len(habits_list) >= 5,
                'progress': min(100, (len(habits_list) / 5) * 100),
                'completion_date': habits_list[4].created_at.strftime('%Y-%m-%d') if len(habits_list) >= 5 else None,
                'created_at': datetime.utcnow()
            }
        ]

        # Update or insert achievements
        for achievement in achievements_data:
            mongo.db.achievements.update_one(
                {
                    'user_id': user_id,
                    'title': achievement['title']
                },
                {'$set': achievement},
                upsert=True
            )

        return [Achievement(achievement) for achievement in achievements_data]

    @staticmethod
    def get_user_achievements(user_id):
        from app import mongo
        achievements_data = mongo.db.achievements.find({'user_id': user_id})
        return [Achievement(achievement) for achievement in achievements_data] 