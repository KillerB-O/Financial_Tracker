from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta

from ....db.session import get_db
from ....db.models.user import User
from ....db.models.sms import SMS, TransactionType, ParsingStatus
from .auth import get_current_user
from ....schemas.sms import SMSResponse, SMSListResponse
from ....core.helpers.aggregation_helpers import AggregationHelper
from ....core.helpers.formatting_helpers import FormattingHelper
from ....core.helpers.date_helpers import DateHelper


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=SMSListResponse)
async def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    transaction_type: Optional[str] = Query(None, description="Filter by debit/credit"),
    category: Optional[str] = Query(None, description="Filter by category"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    min_amount: Optional[float] = Query(None, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
    search: Optional[str] = Query(None, description="Search merchant name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all transactions with filters and pagination
    """
    query = db.query(SMS).filter(SMS.user_id == str(current_user.id))
    
    # Apply filters
    if transaction_type:
        if transaction_type.lower() not in ['debit', 'credit']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transaction type. Must be 'debit' or 'credit'"
            )
        query = query.filter(SMS.transaction_type == transaction_type.lower())
    
    if category:
        query = query.filter(SMS.category == category)
    
    if start_date:
        query = query.filter(SMS.received_at >= start_date)
    
    if end_date:
        query = query.filter(SMS.received_at <= end_date)
    
    if min_amount is not None:
        query = query.filter(SMS.amount >= min_amount)
    
    if max_amount is not None:
        query = query.filter(SMS.amount <= max_amount)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                SMS.merchant.ilike(search_pattern),
                SMS.raw_message.ilike(search_pattern)
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination and sorting
    transactions = query.order_by(desc(SMS.received_at)).offset(skip).limit(limit).all()
    
    return {
        "items": transactions,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/summary")
async def get_transaction_summary(
    period: str = Query("month", description="Period: week, month, year, all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get transaction summary for a period
    """
    # Calculate date range
    now = datetime.utcnow()
    
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:  # all
        start_date = datetime.min
    
    # Query transactions
    transactions = db.query(SMS).filter(
        SMS.user_id == str(current_user.id),
        SMS.received_at >= start_date,
        SMS.amount.isnot(None)
    ).all()
    
    # Calculate totals
    total_income = sum(t.amount for t in transactions if t.transaction_type == TransactionType.CREDIT)
    total_expenses = sum(t.amount for t in transactions if t.transaction_type == TransactionType.DEBIT)
    net_savings = total_income - total_expenses
    
    # Get category breakdown
    category_breakdown = AggregationHelper.aggregate_by_category(
        [t for t in transactions if t.transaction_type == TransactionType.DEBIT]
    )
    
    # Get top merchants
    merchant_totals = AggregationHelper.aggregate_by_merchant(
        [t for t in transactions if t.transaction_type == TransactionType.DEBIT]
    )
    top_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Calculate average daily spending
    days_in_period = (now - start_date).days or 1
    avg_daily_spending = total_expenses / days_in_period
    
    return {
        "period": period,
        "start_date": start_date,
        "end_date": now,
        "summary": {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": net_savings,
            "savings_rate": (net_savings / total_income * 100) if total_income > 0 else 0,
            "transaction_count": len(transactions),
            "average_daily_spending": avg_daily_spending,
        },
        "category_breakdown": category_breakdown,
        "top_merchants": [
            {"merchant": merchant, "amount": amount}
            for merchant, amount in top_merchants
        ]
    }


@router.get("/analytics/monthly")
async def get_monthly_analytics(
    months: int = Query(6, ge=1, le=12, description="Number of months to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get monthly spending analytics for charts
    """
    from collections import defaultdict
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=30 * months)
    
    transactions = db.query(SMS).filter(
        SMS.user_id == str(current_user.id),
        SMS.received_at >= start_date,
        SMS.amount.isnot(None)
    ).all()
    
    # Group by month
    monthly_data = defaultdict(lambda: {"income": 0, "expenses": 0, "categories": {}})
    
    for txn in transactions:
        month_key = txn.received_at.strftime("%Y-%m")
        
        if txn.transaction_type == TransactionType.CREDIT:
            monthly_data[month_key]["income"] += txn.amount
        elif txn.transaction_type == TransactionType.DEBIT:
            monthly_data[month_key]["expenses"] += txn.amount
            
            if txn.category:
                category = txn.category
                if category not in monthly_data[month_key]["categories"]:
                    monthly_data[month_key]["categories"][category] = 0
                monthly_data[month_key]["categories"][category] += txn.amount
    
    # Format for response
    result = []
    for month_key in sorted(monthly_data.keys()):
        data = monthly_data[month_key]
        result.append({
            "month": month_key,
            "income": data["income"],
            "expenses": data["expenses"],
            "savings": data["income"] - data["expenses"],
            "categories": data["categories"]
        })
    
    return result


@router.get("/analytics/category-trends")
async def get_category_trends(
    category: str,
    months: int = Query(6, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get spending trend for a specific category
    """
    from collections import defaultdict
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=30 * months)
    
    transactions = db.query(SMS).filter(
        SMS.user_id == str(current_user.id),
        SMS.category == category,
        SMS.transaction_type == TransactionType.DEBIT,
        SMS.received_at >= start_date
    ).all()
    
    # Group by month
    monthly_spending = defaultdict(float)
    
    for txn in transactions:
        month_key = txn.received_at.strftime("%Y-%m")
        monthly_spending[month_key] += txn.amount
    
    # Calculate trend
    result = []
    for month_key in sorted(monthly_spending.keys()):
        result.append({
            "month": month_key,
            "amount": monthly_spending[month_key],
            "transaction_count": sum(1 for t in transactions if t.received_at.strftime("%Y-%m") == month_key)
        })
    
    # Calculate average and growth
    amounts = [item["amount"] for item in result]
    avg_spending = sum(amounts) / len(amounts) if amounts else 0
    
    if len(amounts) >= 2:
        growth_rate = ((amounts[-1] - amounts[0]) / amounts[0] * 100) if amounts[0] > 0 else 0
    else:
        growth_rate = 0
    
    return {
        "category": category,
        "monthly_data": result,
        "average_monthly_spending": avg_spending,
        "growth_rate": growth_rate
    }


@router.get("/compare/period")
async def compare_periods(
    period_type: str = Query("month", description="week, month, quarter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare current period vs previous period
    """
    now = datetime.utcnow()
    
    # Define periods
    if period_type == "week":
        days = 7
    elif period_type == "month":
        days = 30
    elif period_type == "quarter":
        days = 90
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period type"
        )
    
    # Current period
    current_start = now - timedelta(days=days)
    current_txns = db.query(SMS).filter(
        SMS.user_id == str(current_user.id),
        SMS.received_at >= current_start,
        SMS.transaction_type == TransactionType.DEBIT
    ).all()
    
    # Previous period
    previous_start = now - timedelta(days=days * 2)
    previous_end = current_start
    previous_txns = db.query(SMS).filter(
        SMS.user_id == str(current_user.id),
        SMS.received_at >= previous_start,
        SMS.received_at < previous_end,
        SMS.transaction_type == TransactionType.DEBIT
    ).all()
    
    # Calculate totals
    current_total = sum(t.amount for t in current_txns)
    previous_total = sum(t.amount for t in previous_txns)
    
    # Calculate change
    if previous_total > 0:
        change_percentage = ((current_total - previous_total) / previous_total) * 100
    else:
        change_percentage = 0
    
    # Category comparison
    current_categories = AggregationHelper.aggregate_by_category(current_txns)
    previous_categories = AggregationHelper.aggregate_by_category(previous_txns)
    
    category_changes = {}
    for category in set(list(current_categories.keys()) + list(previous_categories.keys())):
        current = current_categories.get(category, 0)
        previous = previous_categories.get(category, 0)
        change = ((current - previous) / previous * 100) if previous > 0 else 0
        category_changes[category] = {
            "current": current,
            "previous": previous,
            "change_percentage": change
        }
    
    return {
        "period_type": period_type,
        "current_period": {
            "start": current_start,
            "end": now,
            "total_spending": current_total,
            "transaction_count": len(current_txns)
        },
        "previous_period": {
            "start": previous_start,
            "end": previous_end,
            "total_spending": previous_total,
            "transaction_count": len(previous_txns)
        },
        "comparison": {
            "change_amount": current_total - previous_total,
            "change_percentage": change_percentage,
            "trend": "increasing" if change_percentage > 0 else "decreasing",
            "category_changes": category_changes
        }
    }


@router.get("/{transaction_id}", response_model=SMSResponse)
async def get_transaction_detail(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific transaction
    """
    transaction = db.query(SMS).filter(
        SMS.id == transaction_id,
        SMS.user_id == str(current_user.id)
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a transaction (soft delete - mark as inactive)
    """
    transaction = db.query(SMS).filter(
        SMS.id == transaction_id,
        SMS.user_id == str(current_user.id)
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Soft delete by updating parsing status
    transaction.parsing_status = ParsingStatus.FAILED
    transaction.error_message = "Deleted by user"
    
    db.commit()
    
    return {"message": "Transaction deleted successfully"}


@router.get("/export/csv")
async def export_transactions_csv(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export transactions as CSV
    """
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse
    
    query = db.query(SMS).filter(SMS.user_id == str(current_user.id))
    
    if start_date:
        query = query.filter(SMS.received_at >= start_date)
    if end_date:
        query = query.filter(SMS.received_at <= end_date)
    
    transactions = query.order_by(SMS.received_at).all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Date', 'Type', 'Amount', 'Merchant', 'Category',
        'Account', 'Balance', 'Description'
    ])
    
    # Data
    for txn in transactions:
        writer.writerow([
            txn.received_at.strftime('%Y-%m-%d %H:%M:%S'),
            txn.transaction_type.value if txn.transaction_type else 'unknown',
            txn.amount or 0,
            txn.merchant or '',
            txn.category or '',
            txn.account_last4 or '',
            txn.balance or 0,
            (txn.raw_message or '')[:100]  # Truncate description
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=transactions_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )

