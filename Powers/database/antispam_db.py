from datetime import datetime
from threading import RLock

from Powers import TIME_ZONE as TZ
from Powers.database import MongoDB

INSERTION_LOCK = RLock()
ANTISPAM_BANNED = set()


class GBan(MongoDB):
    """Class for managing Gbans in bot."""

    db_name = "gbans"

    def __init__(self) -> None:
        super().__init__(self.db_name)

    # ==============================
    # 🔍 CHECK GBAN (FAST - MEMORY BASED)
    # ==============================
    def check_gban(self, user_id: int):
        return user_id in ANTISPAM_BANNED

    # ==============================
    # ➕ ADD GBAN
    # ==============================
    def add_gban(self, user_id: int, reason: str, by_user: int):
        global ANTISPAM_BANNED

        with INSERTION_LOCK:

            # Already exists → update reason
            if user_id in ANTISPAM_BANNED:
                return self.update_gban_reason(user_id, reason)

            time_rn = datetime.now(TZ)

            # Add to DB
            self.insert_one(
                {
                    "_id": user_id,
                    "reason": reason,
                    "by": by_user,
                    "time": time_rn,
                },
            )

            # Add to memory
            ANTISPAM_BANNED.add(user_id)

            return True

    # ==============================
    # ➖ REMOVE GBAN (SAFE)
    # ==============================
    def remove_gban(self, user_id: int):
        global ANTISPAM_BANNED

        with INSERTION_LOCK:

            # Always safe remove from memory
            ANTISPAM_BANNED.discard(user_id)

            # Remove from DB
            return self.delete_one({"_id": user_id})

    # ==============================
    # 📄 GET GBAN
    # ==============================
    def get_gban(self, user_id: int):
        if user_id in ANTISPAM_BANNED:
            if curr := self.find_one({"_id": user_id}):
                return True, curr.get("reason", "No Reason")
        return False, ""

    # ==============================
    # 🔄 UPDATE REASON
    # ==============================
    def update_gban_reason(self, user_id: int, reason: str):
        with INSERTION_LOCK:
            return self.update(
                {"_id": user_id},
                {"reason": reason},
            )

    # ==============================
    # 📊 COUNT
    # ==============================
    def count_gbans(self):
        return len(ANTISPAM_BANNED)

    # ==============================
    # 📂 LOAD FROM DB
    # ==============================
    def load_from_db(self):
        with INSERTION_LOCK:
            return self.find_all()

    def list_gbans(self):
        return self.load_from_db()


# ==============================
# 🚀 LOAD GBANS INTO MEMORY (IMPORTANT)
# ==============================
def load_gban_into_memory():
    global ANTISPAM_BANNED

    db = GBan()
    all_users = db.find_all()

    for user in all_users:
        ANTISPAM_BANNED.add(user["_id"])
