from datetime import datetime, timedelta
from jose import jwt
from jose import JWTError
from passlib.context import CryptContext

from app.core.config import settings

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

pwd_context=CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def hash_password(password:str):
    return pwd_context.hash(password)

def verify_password(plain_password: str , hashed_password: str):
    return pwd_context.verify(
        plain_password,
        hashed_password
    )

def create_access_token(data: dict):
    to_encode=data.copy()

    expire=datetime.utcnow()+timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp" : expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM

    )

def decode_access_token(token : str):
    try:
        payload=jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload
    except JWTError:
        return None
