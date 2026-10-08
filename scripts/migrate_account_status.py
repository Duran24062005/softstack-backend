"""Backfill account_status for users created before the approval workflow."""

import argparse

from app.config.config import database_config
from app.config.database.mongodb_connection import create_mongodb_client
from app.models.auth import AccountStatus


def migrate(*, apply: bool) -> tuple[int, int]:
    client = create_mongodb_client()
    try:
        database = client[database_config["MONGODB_DATABASE"]]
        users = database.users
        cursor = users.find({"account_status": {"$exists": False}}, {"is_active": 1})
        scanned = 0
        changed = 0
        for user in cursor:
            scanned += 1
            status = AccountStatus.ACTIVE.value if user.get("is_active", True) else AccountStatus.INACTIVE.value
            if apply:
                users.update_one(
                    {"_id": user["_id"], "account_status": {"$exists": False}},
                    {"$set": {"account_status": status}},
                )
                changed += 1
        return scanned, changed
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persist the account_status values")
    args = parser.parse_args()
    scanned, changed = migrate(apply=args.apply)
    mode = "applied" if args.apply else "dry-run"
    print(f"account status migration ({mode}): scanned={scanned}, changed={changed}")


if __name__ == "__main__":
    main()
