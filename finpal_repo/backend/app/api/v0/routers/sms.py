from fastapi import APIRouter,HTTPException,Depends,BackgroundTasks,Query
from sqlalchemy.orm import Session
from typing import Optional,List
from datetime import datetime,timezone
import uuid

from ....db.session import get_db
from ....db.models import User
from ....schemas.sms import SMSIngest