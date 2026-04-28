"""
Create default admin user for NSG VisionAI Platform.

Usage:
    python scripts/create_admin.py

Creates:
    Service Number: NSG/ADMIN/0001
    Password:       Admin@NSG2024
    Role:           ADMIN
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.repositories.user import UserRepository


DEFAULT_USERS = [
    {
        "service_number": "NSG/ADMIN/0001",
        "full_name": "System Administrator",
        "role": UserRole.ADMIN,
        "unit": "NSG IT Cell",
        "password": "Admin@NSG2024",
    },
    {
        "service_number": "NSG/CMD/0001",
        "full_name": "Commander Demo",
        "role": UserRole.COMMANDER,
        "unit": "SAG",
        "password": "Commander@2024",
    },
    {
        "service_number": "NSG/OP/0001",
        "full_name": "Operator Demo",
        "role": UserRole.OPERATOR,
        "unit": "SFC",
        "password": "Operator@2024",
    },
    {
        "service_number": "NSG/ANL/0001",
        "full_name": "Analyst Demo",
        "role": UserRole.ANALYST,
        "unit": "Intelligence",
        "password": "Analyst@2024",
    },
]


async def create_users():
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)

        for user_data in DEFAULT_USERS:
            existing = await repo.get_by_service_number(user_data["service_number"])
            if existing:
                print(f"  [SKIP] {user_data['service_number']} already exists")
                continue

            user = await repo.create(
                service_number=user_data["service_number"],
                full_name=user_data["full_name"],
                role=user_data["role"].value,
                unit=user_data["unit"],
                password_hash=hash_password(user_data["password"]),
                is_active=True,
                failed_login_attempts=0,
            )
            print(f"  [OK]   {user_data['service_number']} ({user_data['role'].value}) created")

        await session.commit()


if __name__ == "__main__":
    print("\nNSG VisionAI — Creating default users...\n")
    asyncio.run(create_users())
    print("\nDefault credentials:")
    print("─" * 50)
    for u in DEFAULT_USERS:
        print(f"  Role:     {u['role'].value}")
        print(f"  Service#: {u['service_number']}")
        print(f"  Password: {u['password']}")
        print()
