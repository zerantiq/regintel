"""User account service.

Handles user profile retrieval, account deletion, and data export for the AI SaaS
platform. Core fields: email, phone, first_name, last_name, dob.
"""

import sqlite3

DB_PATH = "users.db"


def get_user_profile(user_id: int) -> dict:
    """Return full user profile including personal details."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT email, phone, first_name, last_name, dob FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {}
    # Returns PII fields directly — no data minimisation applied
    return {
        "email": row[0],
        "phone": row[1],
        "first_name": row[2],
        "last_name": row[3],
        "dob": row[4],
    }


def delete_user_account(user_id: int) -> bool:
    """Permanently remove a user account. Hard delete, no soft-delete or audit trail."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def export_user_data(user_id: int, dest_path: str) -> None:
    """Write a user's data export to a local file."""
    profile = get_user_profile(user_id)
    with open(dest_path, "w") as f:
        f.write(str(profile))
