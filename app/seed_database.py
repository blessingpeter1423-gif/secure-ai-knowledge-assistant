from app.database import SessionLocal
from app.models import Tenant, Role


def seed_database():

    db = SessionLocal()

    try:

        tenants = [
            {
                "tenant_id": "acme",
                "name": "Acme Technology"
            },
            {
                "tenant_id": "globex",
                "name": "Globex Corporation"
            }
        ]

        for tenant_data in tenants:

            existing_tenant = db.query(Tenant).filter(
                Tenant.tenant_id == tenant_data["tenant_id"]
            ).first()

            if not existing_tenant:

                db.add(
                    Tenant(
                        tenant_id=tenant_data["tenant_id"],
                        name=tenant_data["name"]
                    )
                )

                print(
                    f"Created tenant: "
                    f"{tenant_data['name']}"
                )

            else:

                print(
                    f"Tenant already exists: "
                    f"{tenant_data['name']}"
                )

        roles = [
            "employee",
            "manager",
            "hr",
            "admin"
        ]

        for role_name in roles:

            existing_role = db.query(Role).filter(
                Role.name == role_name
            ).first()

            if not existing_role:

                db.add(
                    Role(
                        name=role_name
                    )
                )

                print(
                    f"Created role: {role_name}"
                )

            else:

                print(
                    f"Role already exists: {role_name}"
                )

        db.commit()

        print("\nDatabase seeding completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()