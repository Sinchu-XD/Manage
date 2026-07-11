from threading import RLock
from time import time

from bson import Int64
from Powers import LOGGER
from Powers.database import MongoDB

INSERTION_LOCK = RLock()


class Users(MongoDB):
    db_name = "users"

    def __init__(self, user_id: int) -> None:
        super().__init__(self.db_name)
        self.user_id = user_id
        self.user_info = self.__ensure_in_db()

    def update_user(self, name: str, username: str = None):
        with INSERTION_LOCK:
            return self.collection.update_one(
                {"_id": self.user_id},
                {"$set": {
                    "username": username or "",
                    "name": name or "unknown_till_now",
                }},
                upsert=True
            )

    def delete_user(self):
        with INSERTION_LOCK:
            return self.delete_one({"_id": self.user_id})

    @staticmethod
    def remove_invalid_user(user_id: int):
        collection = MongoDB(Users.db_name)
        collection.delete_one({"_id": user_id})

    @staticmethod
    def count_users():
        with INSERTION_LOCK:
            collection = MongoDB(Users.db_name)
            return collection.count() or 0

    def get_my_info(self):
        with INSERTION_LOCK:
            return self.find_one({"_id": self.user_id})

    @staticmethod
    def list_users():
        with INSERTION_LOCK:
            collection = MongoDB(Users.db_name)
            return collection.find_all()

    @staticmethod
    def list_user_ids():
        with INSERTION_LOCK:
            collection = MongoDB(Users.db_name)
            users = collection.find_all()
            ids = []

            for u in users:
                uid = u.get("_id")
                if isinstance(uid, (int, Int64)) and uid is not None:
                    ids.append(int(uid))

            return list(set(ids))

    @staticmethod
    def get_user_info(user_id: int or str):
        with INSERTION_LOCK:
            collection = MongoDB(Users.db_name)

            if isinstance(user_id, (int, Int64)):
                curr = collection.find_one({"_id": int(user_id)})

            elif isinstance(user_id, str):
                username = user_id.replace("@", "")
                curr = collection.find_one({"username": username})

            else:
                curr = None

            return curr or {}

    def __ensure_in_db(self):
        new_data = {
            "_id": self.user_id,
            "username": "",
            "name": "unknown_till_now"
        }

        self.collection.update_one(
            {"_id": self.user_id},
            {"$setOnInsert": new_data},
            upsert=True
        )

        return self.find_one({"_id": self.user_id})

    @staticmethod
    def load_from_db():
        with INSERTION_LOCK:
            collection = MongoDB(Users.db_name)
            return collection.find_all()

    @staticmethod
    def repair_db(collection):
        all_data = collection.find_all()
        keys = {"username": "", "name": "unknown_till_now"}

        for data in all_data:
            for key, val in keys.items():
                if key not in data or data[key] is None:
                    LOGGER.warning(
                        f"Repairing Users Database - setting '{key}:{val}' for {data['_id']}"
                    )
                    collection.update({"_id": data["_id"]}, {key: val})


def __pre_req_users():
    start = time()
    LOGGER.info("Starting Users Database Repair...")
    collection = MongoDB(Users.db_name)
    Users.repair_db(collection)
    LOGGER.info(f"Done in {round((time() - start), 3)}s!")
