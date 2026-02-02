import json
import logging
import os
import sys
import uuid

from sqlalchemy import inspect, text

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.orm_models.roles import Role
from shared_libraries.database import sync_engine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "System Administrator",
        "is_system": True,
        "permissions": {"*": ["*"]},
    },
    {
        "name": "nurse",
        "description": "Medical Staff",
        "is_system": True,
        "permissions": {
            "infants": ["read", "write"],
            "mothers": ["read", "write"],
            "pairings": ["read", "write"],
            "alerts": ["read", "ack"],
        },
    },
    {
        "name": "security",
        "description": "Security Personnel",
        "is_system": True,
        "permissions": {
            "alerts": ["read", "ack", "escalate"],
            "gates": ["read", "control"],
            "cameras": ["read"],
            "rtls": ["read"],
            "zones": ["read"],
        },
    },
    {
        "name": "viewer",
        "description": "Read-only access",
        "is_system": True,
        "permissions": {"*": ["read"]},
    },
]


def migrate():
    with sync_engine.connect() as conn:
        inspector = inspect(sync_engine)

        # 1. Create roles table if not exists
        if not inspector.has_table("roles"):
            logger.info("Creating roles table...")
            # We use the ORM definition to create the table
            Role.__table__.create(conn)
            conn.commit()
        else:
            logger.info("Roles table already exists.")

        # 2. Populate default roles
        logger.info("Populating default roles...")
        role_map = {}  # name -> uuid

        for role_data in DEFAULT_ROLES:
            # Check if exists
            result = conn.execute(
                text("SELECT id FROM roles WHERE name = :name"),
                {"name": role_data["name"]},
            ).fetchone()

            if result:
                role_id = result[0]
                logger.info(f"Role {role_data['name']} exists ({role_id})")
            else:
                role_id = uuid.uuid4()
                conn.execute(
                    text("""
                        INSERT INTO roles (id, name, description, permissions, is_system, created_at, updated_at)
                        VALUES (:id, :name, :description, :permissions, :is_system, NOW(), NOW())
                    """),
                    {
                        "id": role_id,
                        **role_data,
                        "permissions": json.dumps(role_data["permissions"]),
                    },
                )
                logger.info(f"Created role {role_data['name']} ({role_id})")

            role_map[role_data["name"]] = role_id

        conn.commit()

        # 3. Add role_id to users if not exists
        columns = [c["name"] for c in inspector.get_columns("users")]
        if "role_id" not in columns:
            logger.info("Adding role_id column to users table...")
            conn.execute(
                text("ALTER TABLE users ADD COLUMN role_id UUID REFERENCES roles(id)")
            )
            conn.commit()

        # 4. Migrate data
        # Users have 'role' column which is an enum (admin, nurse, etc.)
        if "role" in columns:
            logger.info("Migrating user roles...")
            # We can't easily join because 'role' is an enum type on DB side often
            # But we can update one by one or using CASE

            # Simple approach: Update for each role type
            for name, r_id in role_map.items():
                # Cast role to text to compare
                stmt = text(
                    f"UPDATE users SET role_id = :rid WHERE CAST(role AS TEXT) = :name"
                )
                result = conn.execute(stmt, {"rid": r_id, "name": name})
                logger.info(f"Updated {result.rowcount} users to role {name}")

            conn.commit()

            # 5. Drop old role column
            # logger.info("Dropping old role column...")
            # conn.execute(text("ALTER TABLE users DROP COLUMN role"))
            # conn.commit()
            logger.warning(
                "Skipping DROP COLUMN role for safety. Please verify data and drop manually or update code references first."
            )

        else:
            logger.info("User 'role' column not found (already migrated?)")

        logger.info("Migration complete!")


if __name__ == "__main__":
    migrate()
