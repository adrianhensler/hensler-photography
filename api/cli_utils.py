"""CLI utilities for development and admin tasks

This module provides command-line tools for administrative tasks like
password management, user creation, and database maintenance.

Usage:
    python -m api.cli_utils set-password <username> <password>
    python -m api.cli_utils create-user <username> <display_name> <password>
"""

import asyncio
import sys
import aiosqlite
from pathlib import Path

# Import from our auth module
from api.routes.auth import hash_password, validate_password
from api.database import DATABASE_PATH


async def set_user_password(username: str, password: str) -> bool:
    """Set password for an existing user

    Args:
        username: The username to update
        password: The new password (must meet requirements)

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If password doesn't meet requirements
    """
    # Validate password meets requirements
    validate_password(password)

    # Hash the password
    password_hash = hash_password(password)

    # Update database
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username)
        )
        await db.commit()

        if cursor.rowcount == 0:
            print(f"❌ ERROR: User '{username}' not found in database", file=sys.stderr)
            return False
        else:
            print(f"✓ Password set successfully for user '{username}'")
            return True


async def create_user(username: str, display_name: str, password: str) -> bool:
    """Create a new user

    Args:
        username: Unique username (lowercase, alphanumeric + underscore)
        display_name: Display name for the user
        password: Initial password (must meet requirements)

    Returns:
        True if successful, False otherwise
    """
    # Validate password
    validate_password(password)

    # Hash the password
    password_hash = hash_password(password)

    # Insert into database
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                """INSERT INTO users (username, display_name, password_hash, role)
                   VALUES (?, ?, ?, 'photographer')""",
                (username.lower(), display_name, password_hash),
            )
            await db.commit()
            print(f"✓ User '{username}' created successfully")
            return True
        except aiosqlite.IntegrityError:
            print(f"❌ ERROR: User '{username}' already exists", file=sys.stderr)
            return False


async def list_users():
    """List all users in the database"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT username, display_name, role,
                      CASE WHEN password_hash IS NULL THEN 'NO' ELSE 'YES' END as has_password,
                      created_at
               FROM users
               ORDER BY created_at"""
        )
        rows = await cursor.fetchall()

        if not rows:
            print("No users found in database")
            return

        print(
            f"\n{'Username':<15} {'Display Name':<20} {'Role':<15} {'Password':<10} {'Created':<20}"
        )
        print("-" * 85)
        for row in rows:
            print(
                f"{row['username']:<15} {row['display_name']:<20} {row['role']:<15} {row['has_password']:<10} {row['created_at']:<20}"
            )
        print()


def print_usage():
    """Print usage instructions"""
    print(__doc__)
    print("\nAvailable commands:")
    print("  set-password <username> <password>              Set password for existing user")
    print("  create-user <username> <display_name> <password> Create new user")
    print("  list-users                                       List all users")
    print("\nPassword requirements:")
    print("  - Minimum 12 characters")
    print("  - At least one uppercase letter")
    print("  - At least one lowercase letter")
    print("  - At least one digit")
    print("  - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")
    print()


async def main():
    """Main entry point for CLI"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "set-password":
        if len(sys.argv) != 4:
            print("Usage: python -m api.cli_utils set-password <username> <password>")
            sys.exit(1)

        username = sys.argv[2]
        password = sys.argv[3]

        try:
            success = await set_user_password(username, password)
            sys.exit(0 if success else 1)
        except ValueError as e:
            print(f"❌ ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    elif command == "create-user":
        if len(sys.argv) != 5:
            print("Usage: python -m api.cli_utils create-user <username> <display_name> <password>")
            sys.exit(1)

        username = sys.argv[2]
        display_name = sys.argv[3]
        password = sys.argv[4]

        try:
            success = await create_user(username, display_name, password)
            sys.exit(0 if success else 1)
        except ValueError as e:
            print(f"❌ ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    elif command == "list-users":
        await list_users()
        sys.exit(0)

    else:
        print(f"Unknown command: {command}\n")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
