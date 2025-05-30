from typing import Any, Dict, Optional, Union
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


def get(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_by_email(db: Session, email: str) -> Optional[User]:

    return db.query(User).filter(User.email == email).first()


def get_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def authenticate(
    db: Session, email: Optional[str], username: Optional[str], password: str
) -> Optional[User]:
    # Check if the identifier is email or username by checking if username is not None
    if username is not None and username != "":
        print(f"Authenticating with username: {username}")
        user = get_by_username(db, username=username)
    else:
        print(f"Authenticating with email: {email}")
        user = get_by_email(db, email=email)

    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create(db: Session, *, obj_in: UserCreate) -> User:
    db_obj = User(
        email=obj_in.email,
        username=obj_in.username,
        hashed_password=get_password_hash(obj_in.password),
        is_active=obj_in.is_active,
        is_superuser=obj_in.is_superuser,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update(
    db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
) -> User:
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.model_dump(exclude_unset=True)
    if update_data.get("password"):
        hashed_password = get_password_hash(update_data["password"])
        update_data["hashed_password"] = hashed_password
        update_data.pop("password")

    for field in update_data:
        if field in update_data and hasattr(db_obj, field):
            setattr(db_obj, field, update_data[field])

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def remove(db: Session, *, user_id: int) -> User:
    obj = db.query(User).get(user_id)
    db.delete(obj)
    db.commit()
    return obj
