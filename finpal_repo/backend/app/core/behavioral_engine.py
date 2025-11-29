import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db.models.challenges import Challenge, Nudge, UserStreak
from ..db.models.sms import SMS, TransactionType
from ..db.models.recommendation import Recommendation


class BehavioralEngine:
    """Behavioral coaching and habit building system"""
    
    CHALLENGE_TEMPLATES = {
        'spending_limit': {
            'title': 'Weekly Spending Challenge',
            'description': 'Keep your total spending under ₹{target} this week',
            'points': 150
        },
        'no_spend_day': {
            'title': 'No-Spend Day Challenge',
            'description': 'Go 24 hours without any discretionary spending',
            'points': 100
        },
        'category_limit': {
            'title': '{category} Limit Challenge',
            'description': 'Keep {category} spending under ₹{target} this week',
            'points': 120
        },
        'saving_goal': {
            'title': 'Savings Booster',
            'description': 'Save at least ₹{target} this week',
            'points': 200
        }
    }
    
    NUDGE_TEMPLATES = {
        'spending_warning': [
            "⚠️ You've spent ₹{amount} on {category} this week - that's {percentage}% of your usual budget!",
            "🚨 Heads up! {category} spending is trending high this month.",
        ],
        'goal_reminder': [
            "🎯 You're ₹{amount} away from your {goal_name} goal. Keep going!",
            "💪 Just ₹{amount} more to hit your {goal_name} target!",
        ],
        'encouragement': [
            "🎉 Great job! You're {percentage}% under budget this week!",
            "⭐ You've saved ₹{amount} compared to last month. Keep it up!",
        ],
        'streak': [
            "🔥 {days} day streak! Don't break it now!",
            "💯 Amazing! {days} days of smart spending!",
        ]
    }
    
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
    
    # ==================== CHALLENGE MANAGEMENT ====================
    
    def generate_weekly_challenges(self) -> List[Challenge]:
        """Generate personalized weekly challenges"""
        
        # Analyze user's spending patterns
        transactions = self._get_recent_transactions(days=30)
        avg_weekly_spending = self._calculate_weekly_average(transactions)
        problem_categories = self._identify_problem_categories(transactions)
        
        challenges = []
        
        # Challenge 1: Overall spending limit (10-15% below average)
        target = avg_weekly_spending * 0.85
        challenges.append(self._create_challenge(
            'spending_limit',
            target_value=target,
            duration_days=7
        ))
        
        # Challenge 2: Category-specific if problem areas exist
        if problem_categories:
            category = problem_categories[0]
            category_avg = self._get_category_average(transactions, category)
            challenges.append(self._create_challenge(
                'category_limit',
                target_value=category_avg * 0.75,
                duration_days=7,
                category=category
            ))
        
        # Challenge 3: No-spend day (random day)
        challenges.append(self._create_challenge(
            'no_spend_day',
            target_value=0,
            duration_days=1
        ))
        
        # Save to database
        for challenge in challenges:
            self.db.add(challenge)
        self.db.commit()
        
        return challenges
    
    def _create_challenge(
        self,
        challenge_type: str,
        target_value: float,
        duration_days: int,
        category: Optional[str] = None
    ) -> Challenge:
        """Create a challenge instance"""
        
        template = self.CHALLENGE_TEMPLATES[challenge_type]
        
        title = template['title']
        description = template['description']
        
        # Format strings with actual values
        if '{target}' in description:
            description = description.format(target=f"{target_value:,.0f}")
        if '{category}' in title:
            title = title.format(category=category.title() if category else "")
        if '{category}' in description:
            description = description.format(category=category.title() if category else "")
        
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=duration_days)
        
        return Challenge(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            type=challenge_type,
            title=title,
            description=description,
            category=category,
            target_value=target_value,
            current_value=0.0,
            start_date=start_date,
            end_date=end_date,
            points_reward=template['points']
        )
    
    def update_challenge_progress(self):
        """Update progress for all active challenges"""
        
        active_challenges = self.db.query(Challenge).filter(
            Challenge.user_id == self.user_id,
            Challenge.status == "active",
            Challenge.end_date >= datetime.utcnow()
        ).all()
        
        for challenge in active_challenges:
            # Get transactions since challenge start
            transactions = self.db.query(SMS).filter(
                SMS.user_id == self.user_id,
                SMS.received_at >= challenge.start_date,
                SMS.transaction_type == TransactionType.DEBIT
            )
            
            if challenge.category:
                transactions = transactions.filter(SMS.category == challenge.category)
            
            # Calculate current value
            current_value = sum(t.amount for t in transactions.all())
            challenge.current_value = current_value
            
            # Check if completed
            if challenge.type in ['spending_limit', 'category_limit', 'no_spend_day']:
                if current_value <= challenge.target_value:
                    self._complete_challenge(challenge)
            elif challenge.type == 'saving_goal':
                if current_value >= challenge.target_value:
                    self._complete_challenge(challenge)
        
        self.db.commit()
    
    def _complete_challenge(self, challenge: Challenge):
        """Mark challenge as completed and award points"""
        
        challenge.status = "completed"
        challenge.completed_at = datetime.utcnow()
        
        # Update user streak
        streak = self._get_or_create_streak()
        streak.challenges_completed += 1
        streak.total_points += challenge.points_reward
        streak.current_streak += 1
        
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
        
        self.db.commit()
        
        # Send congratulatory nudge
        self.send_nudge(
            'encouragement',
            f"🎉 Challenge completed! You earned {challenge.points_reward} points!"
        )
    
    # ==================== NUDGE SYSTEM (Reinforcement Learning) ====================
    
    def send_smart_nudge(self):
        """Send optimally-timed nudge based on user state"""
        
        # Get current user state
        user_state = self._get_user_state()
        
        # Determine best nudge type based on state
        nudge_type, message = self._select_optimal_nudge(user_state)
        
        if not message:
            return None
        
        # Determine optimal time (simplified RL)
        optimal_time = self._predict_optimal_time(user_state)
        
        nudge = Nudge(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            type=nudge_type,
            message=message,
            optimal_time=optimal_time,
            user_state=user_state
        )
        
        self.db.add(nudge)
        self.db.commit()
        
        return nudge
    
    def _select_optimal_nudge(self, user_state: Dict) -> tuple:
        """Select best nudge using simple RL logic"""
        
        health_score = user_state.get('health_score', 50)
        days_into_month = user_state.get('days_into_month', 1)
        recent_spending = user_state.get('recent_spending_trend', 0)
        
        # Warning if spending is high mid-month
        if days_into_month > 15 and recent_spending > 1.2:
            category = user_state.get('highest_category', 'food')
            amount = user_state.get('category_spending', 0)
            percentage = int((recent_spending - 1) * 100)
            
            message = random.choice(self.NUDGE_TEMPLATES['spending_warning']).format(
                amount=f"{amount:,.0f}",
                category=category,
                percentage=percentage
            )
            return ('spending_warning', message)
        
        # Encouragement if doing well
        if health_score > 75:
            savings = user_state.get('monthly_savings', 0)
            message = random.choice(self.NUDGE_TEMPLATES['encouragement']).format(
                amount=f"{savings:,.0f}",
                percentage=int((1 - recent_spending) * 100)
            )
            return ('encouragement', message)
        
        # Goal reminder
        if user_state.get('has_active_goals'):
            goal_name = user_state.get('primary_goal_name', 'savings')
            amount_needed = user_state.get('goal_shortfall', 0)
            message = random.choice(self.NUDGE_TEMPLATES['goal_reminder']).format(
                goal_name=goal_name,
                amount=f"{amount_needed:,.0f}"
            )
            return ('goal_reminder', message)
        
        return (None, None)
    
    def _predict_optimal_time(self, user_state: Dict) -> str:
        """Predict best time to send nudge (simplified RL)"""
        
        # In production, use actual RL Q-learning
        # For now, use simple heuristics
        
        hour = datetime.now().hour
        
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        else:
            return "evening"
    
    def send_nudge(self, nudge_type: str, message: str):
        """Direct nudge send"""
        nudge = Nudge(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            type=nudge_type,
            message=message
        )
        self.db.add(nudge)
        self.db.commit()
        return nudge
    
    def track_nudge_response(self, nudge_id: str, action_taken: bool = False):
        """Track user response to nudge for RL learning"""
        
        nudge = self.db.query(Nudge).filter(Nudge.id == nudge_id).first()
        if not nudge:
            return
        
        nudge.viewed = True
        nudge.viewed_at = datetime.utcnow()
        
        if action_taken:
            nudge.action_taken = True
            nudge.action_taken_at = datetime.utcnow()
            
            # Calculate engagement score
            time_to_action = (nudge.action_taken_at - nudge.sent_at).total_seconds() / 3600
            nudge.engagement_score = 1.0 / (1 + time_to_action)  # Faster response = higher score
        
        self.db.commit()
# ==================== HELPER METHODS ====================
    
    def _get_user_state(self) -> Dict:
        """Get current user financial state"""
        
        from ..core.recommendation_engine import FinancialRecommender
        recommender = FinancialRecommender(self.db, self.user_id)
        
        scores = recommender.calculate_health_score()
        transactions = self._get_recent_transactions(days=7)
        
        now = datetime.now()
        days_into_month = now.day
        
        # Get spending trend
        last_week = sum(t.amount for t in transactions if t.transaction_type == TransactionType.DEBIT)
        avg_weekly = self._calculate_weekly_average(self._get_recent_transactions(days=30))
        spending_trend = last_week / avg_weekly if avg_weekly > 0 else 1.0
        
        # Get highest spending category
        category_totals = {}
        for t in transactions:
            if t.category and t.transaction_type == TransactionType.DEBIT:
                category_totals[t.category] = category_totals.get(t.category, 0) + t.amount
        
        highest_category = max(category_totals.items(), key=lambda x: x[1]) if category_totals else (None, 0)
        
        return {
            'health_score': scores['overall_score'],
            'days_into_month': days_into_month,
            'recent_spending_trend': spending_trend,
            'highest_category': highest_category[0],
            'category_spending': highest_category[1],
            'has_active_goals': self.db.query(func.count()).select_from(
                self.db.query(FinancialGoal).filter(
                    FinancialGoal.user_id == self.user_id,
                    FinancialGoal.is_active == True
                ).subquery()
            ).scalar() > 0
        }
    
    def _get_recent_transactions(self, days: int) -> List[SMS]:
        """Get recent transactions"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return self.db.query(SMS).filter(
            SMS.user_id == self.user_id,
            SMS.received_at >= cutoff,
            SMS.amount.isnot(None)
        ).all()
    
    def _calculate_weekly_average(self, transactions: List[SMS]) -> float:
        """Calculate average weekly spending"""
        debits = [t.amount for t in transactions if t.transaction_type == TransactionType.DEBIT]
        if not debits:
            return 0
        weeks = len(transactions) / 7
        return sum(debits) / max(1, weeks)
    
    def _identify_problem_categories(self, transactions: List[SMS]) -> List[str]:
        """Identify categories with excessive spending"""
        category_totals = {}
        for t in transactions:
            if t.category and t.transaction_type == TransactionType.DEBIT:
                category_totals[t.category] = category_totals.get(t.category, 0) + t.amount
        
        # Sort by amount
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in sorted_categories[:2]]  # Top 2 problem areas
    
    def _get_category_average(self, transactions: List[SMS], category: str) -> float:
        """Get average spending for a category"""
        amounts = [t.amount for t in transactions 
                   if t.category == category and t.transaction_type == TransactionType.DEBIT]
        return sum(amounts) / max(1, len(amounts))
    
    def _get_or_create_streak(self) -> UserStreak:
        """Get or create user streak record"""
        streak = self.db.query(UserStreak).filter(
            UserStreak.user_id == self.user_id
        ).first()
        
        if not streak:
            streak = UserStreak(
                id=str(uuid.uuid4()),
                user_id=self.user_id
            )
            self.db.add(streak)
            self.db.commit()
        
        return streak
