from sqlalchemy.orm import Session

from app.models import User


def get_user(
    db: Session,
    username: str
):
    """
    Find a user in the database by username.
    """

    return (
        db.query(User)
        .filter(User.username == username)
        .first()
    )


def create_user(
    db: Session,
    username: str,
    password_hash: str,
    user_id: str,
    tenant_id: str,
    role: str
):
    """
    Create a user in the database.
    """

    user = User(
        user_id=user_id,
        username=username,
        password_hash=password_hash,
        tenant_id=tenant_id,
        role=role
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user