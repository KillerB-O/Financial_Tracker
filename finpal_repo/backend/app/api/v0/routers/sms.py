from fastapi import APIRouter,HTTPException,Depends,BackgroundTasks,Query
from sqlalchemy.orm import Session
from typing import Optional,List
from datetime import datetime,timezone
import uuid
import logging


from ....db.session import get_db
from ....db.models.user import User
from ....schemas.sms import (
    SMSIngestRequest, SMSParseRequest, PennyWiseCallback,
    SMSResponse, SMSListResponse
)
from .auth import get_current_user
from ....core.sms_parser import LocalSMSParser, enqueue_remote_parse
from ....db.models.sms import SMS, ParsingStatus

logger=logging.getLogger(__name__)
router = APIRouter(prefix="/sms", tags=["sms"])


@router.post("/ingest", response_model=SMSResponse)
async def ingest_sms(
    request: SMSIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest incoming SMS from device and parse it
    
    - Stores raw message if consent given
    - Parses locally with pattern matching
    - Optionally enqueues for remote parsing if confidence is low
    """
    # Create SMS record
    sms = SMS(
        id=str(uuid.uuid4()),
        user_id=str(current_user.id),
        phone_number=request.phone_number,
        raw_message=request.message if request.consent_store_raw else None,
        received_at=request.received_at or datetime.now(timezone.utc),
        parsing_status=ParsingStatus.PENDING
    )
    
    # Parse locally
    try:
        logger.debug(f"Parsung SMS:{request.message[:50]}...")

        message_to_parse=str(request.message) if request.message else ""

        parsed_data = LocalSMSParser.parse(message_to_parse)
        
        logger.debug(f"Parsed result: amount={parsed_data.amount},type={parsed_data.transaction_type}, merchant={parsed_data.merchant}")
        # Update SMS with parsed data
        sms.amount = parsed_data.amount
        sms.transaction_type = parsed_data.transaction_type
        sms.merchant = parsed_data.merchant
        sms.account_last4 = parsed_data.account_last4
        sms.transaction_date = parsed_data.transaction_date
        sms.balance = parsed_data.balance
        sms.category = parsed_data.category
        sms.confidence = parsed_data.confidence
        
        sms.parsed_at = datetime.now(timezone.utc)
        sms.parsing_status = ParsingStatus.PARSED

        logger.info(f"SMS parsed successfully with confidence {parsed_data.confidence:.2f}")
        
        # If confidence is low or remote parsing forced, enqueue for remote parsing
        if parsed_data.confidence < 0.7 or request.force_remote_parse:
            logger.info("Low confidence,enqueuing for remote parse")
            # background_tasks.add_task(enqueue_remote_parse, sms, request.message)
            
    except Exception as e:
        logger.error(f"Error parsing : {str(e)}",exc_info=True)
        sms.parsing_status = ParsingStatus.FAILED
        sms.error_message = str(e)
    
    # Save to database
    try:
        db.add(sms)
        db.commit()
        db.refresh(sms)
        logger.info(f"SMS saved with ID {sms.id}")
    except Exception as e:
        logger.error(f"Error saving SMS to database: {str(e)}",exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500,detail="Failed to save SMS") 
      
    return sms


@router.post("/parse", response_model=SMSResponse)
async def parse_sms(
    request: SMSParseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Force immediate re-parse of an SMS (user-initiated)
    """
    sms = db.query(SMS).filter(
        SMS.id == request.sms_id,
        SMS.user_id == str(current_user.id)
    ).first()
    
    if not sms:
        raise HTTPException(status_code=404, detail="SMS not found")
    
    if not sms.raw_message:
        raise HTTPException(
            status_code=400,
            detail="No raw message available for parsing"
        )
    
    try:
        parsed_data = LocalSMSParser.parse(sms.raw_message)
        
        # Update SMS with parsed data
        sms.amount = parsed_data.amount
        sms.transaction_type = parsed_data.transaction_type
        sms.merchant = parsed_data.merchant
        sms.account_last4 = parsed_data.account_last4
        sms.transaction_date = parsed_data.transaction_date
        sms.balance = parsed_data.balance
        sms.category = parsed_data.category
        sms.confidence = parsed_data.confidence
        
        sms.parsed_at = datetime.utcnow()
        sms.parsing_status = ParsingStatus.PARSED
        sms.error_message = None
        
    except Exception as e:
        sms.parsing_status = ParsingStatus.FAILED
        sms.error_message = str(e)
    
    db.commit()
    db.refresh(sms)
    
    return sms


@router.post("/callback")
async def pennywise_callback(
    callback: PennyWiseCallback,
    db: Session = Depends(get_db)
):
    """
    Webhook callback for PennyWise AI to post parsing results
    """
    sms = db.query(SMS).filter(SMS.id == callback.sms_id).first()
    
    if not sms:
        raise HTTPException(status_code=404, detail="SMS not found")
    
    if callback.success and callback.parsed_data:
        try:
            # Update with remote parsing results (higher quality)
            sms.amount = callback.parsed_data.get('amount')
            sms.transaction_type = callback.parsed_data.get('transaction_type')
            sms.merchant = callback.parsed_data.get('merchant')
            sms.account_last4 = callback.parsed_data.get('account_last4')
            sms.transaction_date = callback.parsed_data.get('transaction_date')
            sms.balance = callback.parsed_data.get('balance')
            sms.category = callback.parsed_data.get('category')
            sms.confidence = callback.parsed_data.get('confidence', 1.0)
            
            sms.parsing_status = ParsingStatus.PARSED
            sms.parsed_at = datetime.utcnow()
            sms.error_message = None
            
        except Exception as e:
            sms.parsing_status = ParsingStatus.FAILED
            sms.error_message = f"Failed to process callback: {str(e)}"
    else:
        sms.parsing_status = ParsingStatus.FAILED
        sms.error_message = callback.error or "Remote parsing failed"
    
    db.commit()
    
    return {"status": "received"}


@router.get("/{sms_id}", response_model=SMSResponse)
async def get_sms(
    sms_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a specific SMS record by ID
    """
    sms = db.query(SMS).filter(
        SMS.id == sms_id,
        SMS.user_id == str(current_user.id)
    ).first()
    
    if not sms:
        raise HTTPException(status_code=404, detail="SMS not found")
    
    return sms


@router.get("", response_model=SMSListResponse)
async def list_sms(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    status: Optional[str] = Query(None, description="Filter by parsing status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List SMS records for current user (paginated)
    """
    query = db.query(SMS).filter(SMS.user_id == str(current_user.id))
    
    # Filter by status if provided
    if status:
        query = query.filter(SMS.parsing_status == status)
    
    # Get total count
    total = query.count()
    
    # Sort by received date (newest first) and paginate
    sms_list = query.order_by(SMS.received_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": sms_list,
        "total": total,
        "skip": skip,
        "limit": limit
    }
