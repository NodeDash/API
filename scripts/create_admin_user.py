import sys
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.schemas.user import UserCreate
from app.crud.user import create, get_by_email
from app.models.user import User

db = SessionLocal()


def create_admin(email, username, password):
    # Check if user already exists
    user = get_by_email(db, email=email)
    if user:
        print(f"User with email {email} already exists")
        return

    # Create user
    user_in = UserCreate(
        email=email,
        username=username,
        password=password,
        is_active=True,
        is_superuser=True,
    )
    user = create(db=db, obj_in=user_in)
    print(f"Admin user created: {user.email} (ID: {user.id})")
    return user


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create_admin_user.py <email> <username> <password>")
        sys.exit(1)

    email = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    create_admin(email, username, password)
