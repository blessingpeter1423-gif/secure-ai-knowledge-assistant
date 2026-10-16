from app.auth.security import password_hash
from app.database import SessionLocal
from app.models import Role, Tenant, User

# (username, password, tenant, role): demo accounts only
USERS = [
    ("alice", "alice123", "acme", "employee"),
    ("bob", "bob123", "acme", "manager"),
    ("carol", "carol123", "acme", "hr"),
    ("admin", "CHANGE_ME", "acme", "admin"),
    ("david", "david123", "globex", "employee"),
]


def seed_users():
    db = SessionLocal()
    try:
        for username, password, tenant_slug, role_name in USERS:
            if db.query(User).filter(User.username == username).first():
                print(f"User already exists: {username}")
                continue  # safe to run twice

            tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_slug).one()
            role = db.query(Role).filter(Role.name == role_name).one()

            db.add(User(
                user_id=f"user_{db.query(User).count() + 1:03d}",
                username=username,
                password_hash=password_hash.hash(password),
                tenant_id=tenant.id,
                role_id=role.id,
            ))
            db.commit()  # commit each user so the next ID counts correctly
            print(f"Created user: {username} ({tenant_slug}, {role_name})")
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()