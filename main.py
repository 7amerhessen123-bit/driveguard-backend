from fastapi import FastAPI, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User, Company
from security import verify_password, create_token
from errors import AppError, register_handlers

import os
from datetime import datetime, timedelta, timezone
from fastapi import BackgroundTasks
from models import PasswordResetToken
from security import new_reset_token, hash_reset_token, hash_password
from emailer import send_reset_email
import jwt
from security import decode_token
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5173")

app = FastAPI(title="Drive Guard API")
register_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[DASHBOARD_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


def user_json(user: User, db: Session):
    company = db.get(Company, user.company_id) if user.company_id else None
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "companyId": str(user.company_id) if user.company_id else None,
        "companyName": company.name if company else None,
        "shift": user.shift,
        "consentGiven": user.consent_given,
        "hasFaceProfile": user.has_face_profile,
    }


@app.get("/")
def hello():
    return {"message": "Drive Guard backend is working"}


@app.post("/auth/login")
def login(body: LoginIn, x_client: str = Header(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()

    if not user or not verify_password(body.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS",
                       "Wrong password. Check Caps Lock and try again.", "password")

    if not user.is_active:
        raise AppError(403, "ACCOUNT_DISABLED",
                       "Your account is turned off. Contact your company.")

    if (x_client == "dashboard" and user.role != "ADMIN") or \
       (x_client == "mobile" and user.role != "DRIVER"):
        raise AppError(403, "WRONG_CLIENT", "This account can't be used here.")

    return {"token": create_token(user), "user": user_json(user, db)}
class ForgotIn(BaseModel):
    email: str = Field(min_length=3)


@app.post("/auth/forgot-password")
def forgot_password(body: ForgotIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()

    if user and user.is_active:
        raw, hashed = new_reset_token()
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hashed,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ))
        db.commit()
        link = f"{DASHBOARD_URL}/password-reset?token={raw}"
        background.add_task(send_reset_email, user.email, link)

    return {"ok": True}

class ResetIn(BaseModel):
    token: str = Field(min_length=1)
    newPassword: str = Field(min_length=8)


@app.post("/auth/reset-password")
def reset_password(body: ResetIn, db: Session = Depends(get_db)):
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == hash_reset_token(body.token)
    ).first()

    if not record or record.used_at or record.expires_at < datetime.now(timezone.utc):
        raise AppError(400, "RESET_LINK_INVALID",
                       "This link has expired. Request a new one.")

    user = db.get(User, record.user_id)
    user.password_hash = hash_password(body.newPassword)
    record.used_at = datetime.now(timezone.utc)
    db.commit()

    return {"ok": True}

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer),
                 db: Session = Depends(get_db)) -> User:
    if not creds:
        raise AppError(401, "UNAUTHORIZED", "Unauthorized")
    try:
        data = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise AppError(401, "UNAUTHORIZED", "Unauthorized")

    user = db.get(User, data["userId"])
    if not user or not user.is_active:
        raise AppError(401, "UNAUTHORIZED", "Unauthorized")
    return user

@app.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_json(user, db)