import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta,timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid

from ..db.models.sms import SMS, TransactionType
from ..db.models.recommendation import (
    FinancialGoal, Recommendation, UserFinancialProfile
)
from ..schemas.recommendation import RecommendationType


class FinancialRecommender:
    """Core recommendation engine with mathematical models"""
    
    # Weights for health score
    HEALTH_WEIGHTS = {
        'savings': 0.30,
        'spending': 0.30,
        'stability': 0.25,
        'progress': 0.15
    }
    
    # Thresholds
    MIN_SAVINGS_THRESHOLD = 500  # Minimum monthly savings to recommend
    MIN_CONFIDENCE = 0.5
    EXCESS_SPENDING_THRESHOLD = 0.2  # 20% above peer median
    
    # Peer data (simplified - in production, use actual anonymized peer data)
    PEER_MEDIANS = {
        'food': 4500,
        'transport': 3000,
        'shopping': 3500,
        'entertainment': 2000,
        'utilities': 2500,
        'groceries': 6000,
        'health': 1500,
        'other': 2000
    }
    
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.suggestions = []
    
    # ==================== 1. FINANCIAL HEALTH SCORING ====================
    
    def calculate_health_score(self) -> Dict[str, float]:
        """Calculate multi-dimensional financial health score"""
        
        # Get user data
        transactions = self._get_user_transactions(days=90)
        if not transactions:
            print(f"No transactions found for user {self.user_id}")
            return {
                'overall_score': 0.0,
                'savings_score': 0.0,
                'spending_score': 0.0,
                'stability_score': 0.0,
                'progress_score': 0.0
            }
        
        goals = self._get_user_goals()
        
        # Calculate component scores
        savings_score = self._calculate_savings_score(transactions)
        spending_score = self._calculate_spending_score(transactions)
        stability_score = self._calculate_stability_score(transactions)
        progress_score = self._calculate_progress_score(goals)
        
        # Calculate weighted overall score
        overall_score = (
            self.HEALTH_WEIGHTS['savings'] * savings_score +
            self.HEALTH_WEIGHTS['spending'] * spending_score +
            self.HEALTH_WEIGHTS['stability'] * stability_score +
            self.HEALTH_WEIGHTS['progress'] * progress_score
        )
        
        # Update user profile
        profile = self._get_or_create_profile()
        profile.health_score = overall_score
        profile.savings_score = savings_score
        profile.spending_score = spending_score
        profile.stability_score = stability_score
        profile.progress_score = progress_score
        self.db.commit()
        
        return {
            'overall_score': round(overall_score, 2),
            'savings_score': round(savings_score, 2),
            'spending_score': round(spending_score, 2),
            'stability_score': round(stability_score, 2),
            'progress_score': round(progress_score, 2)
        }
    
    def _calculate_savings_score(self, transactions: List[SMS]) -> float:
        """S_savings = 100 × min(1, Actual/Recommended)"""
        
        # Calculate income and expenses
        income = sum(t.amount for t in transactions if t.transaction_type == TransactionType.CREDIT)
        expenses = sum(t.amount for t in transactions if t.transaction_type == TransactionType.DEBIT)
        
        if income == 0:
            return 0.0
        
        actual_savings_rate = (income - expenses) / income
        recommended_rate = 0.20  # Recommend 20% savings rate
        
        score = 100 * min(1.0, actual_savings_rate / recommended_rate)
        return max(0, score)
    
    def _calculate_spending_score(self, transactions: List[SMS]) -> float:
        """S_spending = 100 × max(0, 1 - Discretionary/Budget)"""
        
        # Get discretionary spending (non-essential categories)
        discretionary_categories = ['food', 'entertainment', 'shopping']
        category_spending = self._categorize_spending(transactions)
        
        discretionary_spending = sum(
            category_spending.get(cat, 0) for cat in discretionary_categories
        )
        
        total_spending = sum(category_spending.values())
        
        if total_spending == 0:
            return 100.0
        
        discretionary_ratio = discretionary_spending / total_spending
        recommended_ratio = 0.30  # 30% discretionary budget
        
        score = 100 * max(0, 1 - (discretionary_ratio / recommended_ratio))
        return min(100, score)
    
    def _calculate_stability_score(self, transactions: List[SMS]) -> float:
        """S_stability = 100 × (1 - σ_balance/μ_balance)"""
        
        # Get daily balances
        daily_balances = self._calculate_daily_balances(transactions)
        
        if len(daily_balances) < 2:
            return 50.0
        
        mean_balance = np.mean(daily_balances)
        std_balance = np.std(daily_balances)
        
        if mean_balance == 0:
            return 0.0
        
        coefficient_variation = std_balance / mean_balance
        score = 100 * (1 - min(1.0, coefficient_variation))
        
        return max(0, score)
    
    def _calculate_progress_score(self, goals: List[FinancialGoal]) -> float:
        """S_progress = 100 × Goals_on_track/Total_goals"""
        
        if not goals:
            return 50.0  # Neutral score if no goals
        
        goals_on_track = 0
        for goal in goals:
            if not goal.is_active:
                continue
            
            progress = goal.current_amount / goal.target_amount
            
            if goal.deadline:
                deadline=self._make_aware(goal.deadline)
                days_remaining = (deadline - datetime.now(timezone.utc)).days
                months_remaining = max(1, days_remaining / 30)
                
                
                # Check if on track (with 10% buffer)
                if progress >= 0.9 * (1 - months_remaining / 12):
                    goals_on_track += 1
            else:
                # No deadline, consider on track if > 10% progress
                if progress > 0.1:
                    goals_on_track += 1
        
        return 100 * (goals_on_track / len(goals))
    
    # ==================== 2. SPENDING OPTIMIZATION ====================
    
    def generate_spending_suggestions(self) -> List[Recommendation]:
        """Algorithm 1: Generate spending optimization recommendations"""
        
        transactions = self._get_user_transactions(days=30)
        if not transactions:
            print(f"No transactions to generate suggestions for user {self.user_id}")
            return[]
        
        category_spending = self._categorize_spending(transactions)
        
        if not category_spending:
            print(f"No categorized spending fund")
            return[]
        
        suggestions = []
        
        for category, user_spending in category_spending.items():
            peer_median = self.PEER_MEDIANS.get(category, 3000)
            
            # Calculate excess ratio
            if peer_median==0:
                continue
            
            excess_ratio = (user_spending / peer_median) - 1
            
            # Check if spending is 20% above peers
            if excess_ratio > self.EXCESS_SPENDING_THRESHOLD:
                savings = user_spending - peer_median
                confidence = self._calculate_confidence(category, transactions)
                
                # Only suggest if significant and confident
                if savings > self.MIN_SAVINGS_THRESHOLD and confidence > self.MIN_CONFIDENCE:
                    suggestion = self._create_spending_suggestion(
                        category, savings, excess_ratio, confidence,category_spending
                    )
                    suggestions.append(suggestion)
        
        return self._rank_suggestions(suggestions)
    
    def _create_spending_suggestion(
        self, category: str, monthly_savings: float, excess_ratio: float, confidence: float,
                category_spending:Dict[str,float]) -> Recommendation:
        """Create a spending optimization recommendation"""
        
        annual_savings = monthly_savings * 12
        
        # Calculate goal impact
        goals = self._get_user_goals()
        goal_impact = 0
        if goals:
            primary_goal = goals[0]
            if primary_goal.target_amount>0:
                goal_impact = (annual_savings / primary_goal.target_amount) * 100
        
        title = f"Reduce {category.title()} Spending"
        description = (
            f"You're spending {excess_ratio*100:.0f}% more than similar users on {category}. "
            f"Reducing to peer median could save ₹{monthly_savings:,.0f} monthly "
            f"(₹{annual_savings:,.0f} annually)"
        )
        
        if goal_impact > 0:
            description += f", accelerating your goal by {goal_impact:.0f}%."
        
        recommendation = Recommendation(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            type=RecommendationType.SPENDING_OPTIMIZATION.value,
            category=category,
            title=title,
            description=description,
            monthly_savings=monthly_savings,
            annual_savings=annual_savings,
            goal_impact_percentage=goal_impact,
            confidence_score=confidence,
            priority_score=self._calculate_priority(monthly_savings, confidence, goal_impact),
            calculation_data={
                'excess_ratio': excess_ratio,
                'user_spending': category_spending.get(category, 0),
                'peer_median': self.PEER_MEDIANS.get(category, 0)
            }
        )
        
        return recommendation
    
    # ==================== 3. GOAL ACCELERATION ====================
    
    def accelerate_goal_suggestions(self, goal_id: str) -> List[Recommendation]:
    #     """Algorithm 2: Generate suggestions to accelerate goal achievement"""
        
    #     goal = self.db.query(FinancialGoal).filter(
    #         FinancialGoal.id == goal_id,
    #         FinancialGoal.user_id == self.user_id
    #     ).first()
        
    #     if not goal or not goal.deadline:
    #         return []
        
    #     deadline=self._make_aware(goal.deadline)
        
    #     # Calculate required savings rate
    #     months_remaining = (deadline - datetime.now(timezone.utc)).days / 30
    #     if months_remaining <= 0:
    #         return []
        
    #     required_monthly = (goal.target_amount - goal.current_amount) / months_remaining
    #     current_rate = self._estimate_current_savings_rate()
        
    #     shortfall = required_monthly - current_rate
        
    #     if shortfall <= 0:
    #         return []  # User is on track
        
    #     # Find savings opportunities
    #     opportunities = self.generate_spending_suggestions()
        
    #     # Filter feasible savings that cover shortfall
    #     cumulative_savings = 0
    #     selected_suggestions = []
        
    #     for opp in opportunities:
    #         if cumulative_savings < shortfall:
    #             selected_suggestions.append(opp)
    #             cumulative_savings += opp.monthly_savings
        
    #     return selected_suggestions
       
        goal = self.db.query(FinancialGoal).filter(
            FinancialGoal.id == goal_id,
            FinancialGoal.user_id == self.user_id
        ).first()

        if not goal:
            print(f"[GOAL] No goal found for id={goal_id} user_id={self.user_id}")
            return []

        if not goal.deadline:
            print(f"[GOAL] Goal {goal.id} has no deadline, cannot accelerate")
            return []

        deadline = self._make_aware(goal.deadline)
        now = datetime.now(timezone.utc)

        months_remaining = (deadline - now).days / 30
        print(f"[GOAL] target={goal.target_amount} current={goal.current_amount} "
              f"deadline={deadline.isoformat()} months_remaining={months_remaining}")

        if months_remaining <= 0:
            print("[GOAL] Deadline is in the past or now, months_remaining <= 0")
            return []

        required_monthly = (goal.target_amount - goal.current_amount) / months_remaining
        current_rate = self._estimate_current_savings_rate()
        shortfall = required_monthly - current_rate

        print(f"[GOAL] required_monthly={required_monthly:.2f} "
              f"current_rate={current_rate:.2f} shortfall={shortfall:.2f}")

        opportunities = self.generate_spending_suggestions()
        print(f"[GOAL] {len(opportunities)} spending opportunities found")

        if shortfall <= 0:
            # print("[GOAL] User is already on track (shortfall <= 0)")
            # return []
            print("[GOAL] User is already on track, returning top 3 opportunities")
            top = opportunities[:3]

            now = datetime.now(timezone.utc)
            for rec in top:
                if rec.status is None:
                    rec.status = "pending"
                if rec.shown_at is None:
                    rec.shown_at = now

            return top


        cumulative_savings = 0
        selected_suggestions: list[Recommendation] = []

        for opp in opportunities:
            if cumulative_savings < shortfall:
                selected_suggestions.append(opp)
                cumulative_savings += opp.monthly_savings
                print(f"[GOAL] Selected {opp.category} saving={opp.monthly_savings}, "
                      f"cumulative_savings={cumulative_savings}")

        now = datetime.now(timezone.utc)
        for rec in selected_suggestions:
            if rec.status is None:
                rec.status = "pending"
            if rec.shown_at is None:
                rec.shown_at = now

        print(f"[GOAL] Returning {len(selected_suggestions)} acceleration suggestions")
        return selected_suggestions
    # ==================== 4. SUBSCRIPTION OPTIMIZATION ====================
    
    def generate_subscription_suggestions(self) -> List[Recommendation]:
        """Detect unused subscriptions"""
        
        transactions = self._get_user_transactions(days=60)
        if not transactions:
            return []
        
        # Identify recurring transactions (subscriptions)
        subscription_merchants = {}
        for t in transactions:
          if t.transaction_type == TransactionType.DEBIT and t.category and t.category != 'income':
                if t.merchant not in subscription_merchants:
                    subscription_merchants[t.merchant] = []
                subscription_merchants[t.merchant].append(t)
        
        suggestions = []
        
        # Find merchants with consistent monthly charges (subscriptions)
        for merchant, txns in subscription_merchants.items():
            if len(txns) >= 2:  # At least 2 transactions
                # Check if amounts are similar (within 10%)
                amounts = [t.amount for t in txns]
                mean_amount=np.mean(amounts)
                
                if mean_amount == 0:
                    continue

                std_amount=np.std(amounts)
                if std_amount/mean_amount<0.1:
                    # This looks like a subscription
                    avg_amount = mean_amount
                
                    # Check if unused (no transactions in last 30 days from related categories)
                    last_txn_date = max(t.received_at for t in txns)
                    days_since_last = (datetime.now(timezone.utc) - last_txn_date).days

                    if days_since_last > 30:
                        suggestion = self._create_subscription_suggestion(
                            merchant, avg_amount, days_since_last
                        )
                        suggestions.append(suggestion)

        return suggestions
    
    def _create_subscription_suggestion(
        self, merchant: str, monthly_cost: float, days_unused: int
    ) -> Recommendation:
        """Create subscription optimization recommendation"""
        
        annual_savings = monthly_cost * 12
        
        title = f"Cancel Unused {merchant} Subscription"
        description = (
            f"Your {merchant} subscription (₹{monthly_cost:,.0f}/month) "
            f"hasn't been used in {days_unused} days. "
            f"Canceling could save ₹{annual_savings:,.0f} annually."
        )
        
        return Recommendation(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            type=RecommendationType.SUBSCRIPTION_OPTIMIZATION.value,
            category="subscriptions",
            title=title,
            description=description,
            monthly_savings=monthly_cost,
            annual_savings=annual_savings,
            confidence_score=0.9,  # High confidence for recurring unused charges
            priority_score=self._calculate_priority(monthly_cost, 0.9, 0),
            calculation_data={
                'merchant': merchant,
                'days_unused': days_unused
            }
        )
    
    # ==================== HELPER METHODS ====================
    
    def _get_user_transactions(self, days: int = 30) -> List[SMS]:
        """Get user's parsed SMS transactions"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        return self.db.query(SMS).filter(
            SMS.user_id == self.user_id,
            SMS.received_at >= cutoff_date,
            SMS.amount.isnot(None)
        ).all()
    
    def _get_user_goals(self) -> List[FinancialGoal]:
        """Get user's active financial goals"""
        return self.db.query(FinancialGoal).filter(
            FinancialGoal.user_id == self.user_id,
            FinancialGoal.is_active == True
        ).all()
    
    def _get_or_create_profile(self) -> UserFinancialProfile:
        """Get or create user financial profile"""
        profile = self.db.query(UserFinancialProfile).filter(
            UserFinancialProfile.user_id == self.user_id
        ).first()
        
        if not profile:
            profile = UserFinancialProfile(
                id=str(uuid.uuid4()),
                user_id=self.user_id
            )
            self.db.add(profile)
            self.db.commit()
        
        return profile
    
    def _categorize_spending(self, transactions: List[SMS]) -> Dict[str, float]:
        """Aggregate spending by category"""
        category_totals = {}
        for t in transactions:
          if t.transaction_type == TransactionType.DEBIT and t.category and t.category != 'income':
                category_totals[t.category] = category_totals.get(t.category, 0) + t.amount
        return category_totals
    
    def _calculate_daily_balances(self, transactions: List[SMS]) -> List[float]:
        """Estimate daily balances from transactions"""
        # Simplified - in production, track actual balances from SMS
        balances = [t.balance for t in transactions if t.balance is not None]
        return balances if balances else [0]
    
    def _calculate_confidence(self, category: str, transactions: List[SMS]) -> float:
        """Calculate confidence score for a recommendation"""
        
        category_txns = [t for t in transactions if t.category == category]
        
        if not category_txns:
            return 0.0
        
        # Data quality score (more months = higher confidence)
        months_data = len(transactions) / 30
        c_data = min(1.0, months_data / 6)
        
        # Pattern consistency (lower variance = higher confidence)
        amounts = [t.amount for t in category_txns]
        if len(amounts) > 1:
            c_pattern = 1 - min(1.0, np.std(amounts) / np.mean(amounts))
        else:
            c_pattern = 0.5
        
        # Peer data confidence (simulated)
        c_peer = 0.8
        
        # History confidence (acceptance rate - simulated for now)
        c_history = 0.7
        
        # Weighted average
        confidence = (
            0.3 * c_data +
            0.3 * c_pattern +
            0.2 * c_peer +
            0.2 * c_history
        )
        
        return confidence
    
    def _calculate_priority(
        self, savings: float, confidence: float, goal_impact: float
    ) -> float:
        """Calculate priority score for ranking suggestions"""
        
        SAVINGS_WEIGHT = 0.4
        CONFIDENCE_WEIGHT = 0.3
        GOAL_WEIGHT = 0.3
        
        normalized_savings = min(1.0, savings / 5000)  # Normalize to 0-1
        normalized_goal = min(1.0, goal_impact / 50)  # Normalize to 0-1
        
        priority = (
            SAVINGS_WEIGHT * normalized_savings +
            CONFIDENCE_WEIGHT * confidence +
            GOAL_WEIGHT * normalized_goal
        )
        
        return priority
    
    def _rank_suggestions(self, suggestions: List[Recommendation]) -> List[Recommendation]:
        """Rank suggestions by priority score"""
        return sorted(suggestions, key=lambda x: x.priority_score, reverse=True)
    
    def _estimate_current_savings_rate(self) -> float:
        """Estimate user's current monthly savings rate"""
        transactions = self._get_user_transactions(days=30)
        
        income = sum(t.amount for t in transactions if t.transaction_type == TransactionType.CREDIT)
        expenses = sum(t.amount for t in transactions if t.transaction_type == TransactionType.DEBIT)
        
        return max(0, income - expenses)

    def _make_aware(self, dt: datetime) -> datetime:
        """Convert naive datetime to timezone-aware UTC datetime"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt