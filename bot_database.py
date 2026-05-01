import motor.motor_asyncio
import os
from datetime import datetime

class BotDatabase:
    def __init__(self):
        self.client = None
        self.db = None
        
    def setup(self, mongo_uri: str):
        """Initialize the connection to MongoDB."""
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        self.db = self.client.paradox_bot
        print("  [DATABASE] Connected to MongoDB!")

    # ── VOUCHES ──
    async def get_vouches(self, user_id: str) -> int:
        user = await self.db.users.find_one({"_id": user_id})
        return user.get("vouches", 0) if user else 0

    async def set_vouches(self, user_id: str, count: int):
        await self.db.users.update_one(
            {"_id": user_id},
            {"$set": {"vouches": count}},
            upsert=True
        )

    # ── SCAM STRIKES ──
    async def get_scam_strikes(self, user_id: str) -> int:
        user = await self.db.users.find_one({"_id": user_id})
        return user.get("scam_strikes", 0) if user else 0

    async def add_scam_strike(self, user_id: str) -> int:
        result = await self.db.users.find_one_and_update(
            {"_id": user_id},
            {"$inc": {"scam_strikes": 1}},
            upsert=True,
            return_document=motor.motor_asyncio.AsyncIOMotorCollection.RETURN_DOCUMENT_AFTER
        )
        return result.get("scam_strikes", 0)

    async def clear_scam_strikes(self, user_id: str):
        await self.db.users.update_one(
            {"_id": user_id},
            {"$unset": {"scam_strikes": ""}}
        )

    # ── SWEAR INFRACTIONS ──
    async def get_infractions(self, user_id: str) -> list:
        user = await self.db.users.find_one({"_id": user_id})
        return user.get("infractions", []) if user else []

    async def add_infraction(self, user_id: str, word: str, channel_name: str) -> int:
        infraction = {
            "word": word,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "channel": channel_name
        }
        result = await self.db.users.find_one_and_update(
            {"_id": user_id},
            {"$push": {"infractions": infraction}},
            upsert=True,
            return_document=motor.motor_asyncio.AsyncIOMotorCollection.RETURN_DOCUMENT_AFTER
        )
        return len(result.get("infractions", []))

    async def set_infractions(self, user_id: str, infractions: list):
        """Used for resetting or migration"""
        if not infractions:
            await self.clear_infractions(user_id)
        else:
            await self.db.users.update_one(
                {"_id": user_id},
                {"$set": {"infractions": infractions}},
                upsert=True
            )

    async def clear_infractions(self, user_id: str):
        await self.db.users.update_one(
            {"_id": user_id},
            {"$unset": {"infractions": ""}}
        )

    async def get_all_infractions(self) -> dict:
        """Returns a dict of user_id: list_of_infractions for the leaderboard"""
        cursor = self.db.users.find({"infractions": {"$exists": True, "$ne": []}})
        results = {}
        async for doc in cursor:
            results[doc["_id"]] = doc["infractions"]
        return results

    # ── QUARANTINE ──
    async def save_quarantine_roles(self, user_id: str, roles: list):
        await self.db.users.update_one(
            {"_id": user_id},
            {"$set": {"quarantine_roles": roles}},
            upsert=True
        )

    async def get_quarantine_roles(self, user_id: str) -> list:
        user = await self.db.users.find_one({"_id": user_id})
        return user.get("quarantine_roles", []) if user else []

    async def clear_quarantine_roles(self, user_id: str):
        await self.db.users.update_one(
            {"_id": user_id},
            {"$unset": {"quarantine_roles": ""}}
        )

    async def get_all_users(self) -> list:
        """Returns all user documents from the database."""
        if not self.db: return []
        cursor = self.db.users.find({})
        users = []
        async for doc in cursor:
            users.append(doc)
        return users

# Global database instance
db = BotDatabase()
