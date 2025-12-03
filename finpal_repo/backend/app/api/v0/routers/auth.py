from fastapi import APIRouter,Depends,HTTPException,status
from fastapi.security import OAuth2PasswordRequestForm,OAuth2PasswordBearer
from sqlmodel import Session,select
from ....db.models.user import User
from ....schemas.user import UserCreate,UserRead,Token,UserDelete
from ....core.security import get_password_hash,verify_password,create_access_token,decode_access_token
from ....db.session import get_db
from ....core.config import settings

router = APIRouter(prefix="/auth",tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@router.post("/register",response_model=UserRead)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # check if email exists
    q = select(User).where(User.email == user_in.email.lower())
    exist = db.execute(q).scalar_one_or_none()
    if exist:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # safely hash password
    hashed_pw = get_password_hash(user_in.password)
    
    user = User(
        email=user_in.email.lower(),
        full_name=user_in.full_name,
        hashed_password=hashed_pw,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    created = {"id":user.id,"email": user.email, "full_name": user.full_name, "is_active": True}
    return created


@router.post("/login",response_model=Token)
def login(form_data:OAuth2PasswordRequestForm=Depends(),db:Session=Depends(get_db)):
    #OAuth2PasswordRequestForm Provides 'username' and 'password' form 
    q=select(User).where(User.email==form_data.username.lower())
    user=db.execute(q).scalar_one_or_none()
    if not user or not verify_password(form_data.password,user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Credentials")
    token=create_access_token(subject=user.id)
    return {"access_token":token,"token_type":"bearer"}

def get_user_by_uuid(db:Session,u_uid:str):
    q=select(User).where(User.id==u_uid)
    return db.execute(q).scalars().first()

@router.delete("/del",response_model=UserRead)
def user_delete(user_in:UserDelete,db:Session=Depends(get_db)):
    q=select(User).where(User.email==user_in.email)
    user=db.execute(q).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Doesn't exist!")
   
    db.delete(user)
    db.commit()
    return user

async def get_current_user(token:str=Depends(oauth2_scheme),db:Session=Depends(get_db))->User:
    credential_exception=HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate":"Bearer"},
    )
    try:
        payload=decode_access_token(token)
        subject=payload.get("sub")
        if subject is None:
            raise credential_exception
    except Exception:
        raise credential_exception
    user=get_user_by_uuid(db,subject)
    if user is None:
        raise credential_exception
    if not user.is_active:
        raise HTTPException(status_code=400,detail="Inactive user")
    return user


@router.get("/me",response_model=UserRead)
def read_me(current_user:User=Depends(get_current_user)):
    return current_user
