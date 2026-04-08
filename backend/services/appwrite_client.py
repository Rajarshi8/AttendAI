from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from appwrite.client import Client
from appwrite.exception import AppwriteException
from appwrite.id import ID
from appwrite.query import Query
from appwrite.services.account import Account
from appwrite.services.databases import Databases

from core.config import get_settings

settings = get_settings()


class AppwriteService:
    def __init__(self) -> None:
        self._admin_client = (
            Client()
            .set_endpoint(settings.appwrite_endpoint)
            .set_project(settings.appwrite_project_id)
            .set_key(settings.appwrite_api_key)
        )
        self._databases = Databases(self._admin_client)

    @property
    def databases(self) -> Databases:
        return self._databases

    @staticmethod
    def _account_client(jwt_token: str) -> Account:
        client = (
            Client()
            .set_endpoint(settings.appwrite_endpoint)
            .set_project(settings.appwrite_project_id)
            .set_jwt(jwt_token)
        )
        return Account(client)

    def validate_jwt(self, jwt_token: str) -> dict[str, Any]:
        account = self._account_client(jwt_token)
        return account.get()

    def get_all_users(self) -> list[dict[str, Any]]:
        response = self.databases.list_documents(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_users_collection_id,
            queries=[Query.limit(5000)],
        )
        return response.get("documents", [])

    def create_user_doc(self, user_id: str, name: str, email: str) -> dict[str, Any]:
        try:
            return self.databases.get_document(
                database_id=settings.appwrite_database_id,
                collection_id=settings.appwrite_users_collection_id,
                document_id=user_id,
            )
        except AppwriteException as exc:
            if getattr(exc, "code", None) != 404:
                raise

        now_iso = datetime.now(timezone.utc).isoformat()
        return self.databases.create_document(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_users_collection_id,
            document_id=user_id,
            data={
                "user_id": user_id,
                "name": name,
                "email": email,
                "embedding": [],
                "created_at": now_iso,
            },
        )

    def store_embedding(self, user_id: str, embedding: list[float]) -> dict[str, Any]:
        return self.databases.update_document(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_users_collection_id,
            document_id=user_id,
            data={"embedding": embedding},
        )

    def create_attendance(self, user_id: str, status: str = "present") -> tuple[bool, dict[str, Any], str]:
        today = datetime.now(timezone.utc).date().isoformat()

        existing = self.databases.list_documents(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_attendance_collection_id,
            queries=[Query.equal("user_id", [user_id]), Query.equal("date", [today]), Query.limit(1)],
        )
        existing_docs = existing.get("documents", [])
        if existing_docs:
            return False, existing_docs[0], "Attendance already marked for today."

        doc_id = ID.unique()
        timestamp = datetime.now(timezone.utc).isoformat()
        record = self.databases.create_document(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_attendance_collection_id,
            document_id=doc_id,
            data={
                "id": doc_id,
                "user_id": user_id,
                "timestamp": timestamp,
                "date": today,
                "status": status,
            },
        )
        return True, record, "Attendance marked successfully."

    def get_attendance(self, filters: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
        search = (filters.get("search") or "").strip().lower()
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        limit = int(filters.get("limit", 100))
        offset = int(filters.get("offset", 0))

        attendance_docs = self.databases.list_documents(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_attendance_collection_id,
            queries=[Query.limit(5000)],
        ).get("documents", [])

        users = self.get_all_users()
        user_by_id = {doc.get("user_id"): doc for doc in users}

        enriched: list[dict[str, Any]] = []
        for doc in attendance_docs:
            uid = doc.get("user_id", "")
            user_doc = user_by_id.get(uid, {})
            attendance_date = doc.get("date") or ""

            if start_date and attendance_date and attendance_date < start_date:
                continue
            if end_date and attendance_date and attendance_date > end_date:
                continue

            row = {
                "id": doc.get("id") or doc.get("$id"),
                "user_id": uid,
                "user_name": user_doc.get("name") or "Unknown",
                "user_code": uid,
                "email": user_doc.get("email") or "",
                "status": doc.get("status") or "present",
                "timestamp": doc.get("timestamp") or doc.get("$createdAt"),
                "attendance_date": attendance_date,
            }

            haystack = f"{row['user_name']} {row['email']} {row['user_code']}".lower()
            if search and search not in haystack:
                continue

            enriched.append(row)

        enriched.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
        total = len(enriched)
        paged = enriched[offset : offset + limit]
        return total, paged


appwrite_service = AppwriteService()
