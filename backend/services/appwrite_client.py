from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

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

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_role(value: Any) -> Literal["admin", "student"]:
        return "admin" if str(value).lower() == "admin" else "student"

    def get_user_doc(self, user_id: str) -> dict[str, Any] | None:
        try:
            return self.databases.get_document(
                database_id=settings.appwrite_database_id,
                collection_id=settings.appwrite_users_collection_id,
                document_id=user_id,
            )
        except AppwriteException as exc:
            if getattr(exc, "code", None) == 404:
                return None
            raise

    def get_all_users(self) -> list[dict[str, Any]]:
        response = self.databases.list_documents(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_users_collection_id,
            queries=[Query.limit(5000)],
        )
        return response.get("documents", [])

    def ensure_user_doc(
        self,
        user_id: str,
        name: str,
        email: str,
        role: Literal["admin", "student"] = "student",
    ) -> dict[str, Any]:
        existing = self.get_user_doc(user_id)
        normalized_role = self._normalize_role(role)

        if existing:
            update_payload: dict[str, Any] = {
                "name": name or existing.get("name") or "User",
                "email": email or existing.get("email") or "",
            }
            existing_role = self._normalize_role(existing.get("role"))
            if "role" not in existing:
                update_payload["role"] = existing_role

            return self.databases.update_document(
                database_id=settings.appwrite_database_id,
                collection_id=settings.appwrite_users_collection_id,
                document_id=user_id,
                data=update_payload,
            )

        return self.databases.create_document(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_users_collection_id,
            document_id=user_id,
            data={
                "user_id": user_id,
                "name": name,
                "email": email,
                "role": normalized_role,
                "embedding": [],
                "created_at": self._now_iso(),
            },
        )

    def ensure_user_doc_from_account(self, account: dict[str, Any]) -> dict[str, Any]:
        user_id = str(account.get("$id") or "")
        if not user_id:
            raise ValueError("Account payload missing $id.")

        name = str(account.get("name") or account.get("email") or "User")
        email = str(account.get("email") or "")
        return self.ensure_user_doc(user_id=user_id, name=name, email=email, role="student")

    def create_user_doc(self, user_id: str, name: str, email: str) -> dict[str, Any]:
        return self.ensure_user_doc(user_id=user_id, name=name, email=email, role="student")

    def get_user_role(self, user_id: str) -> Literal["admin", "student"]:
        user_doc = self.get_user_doc(user_id)
        if not user_doc:
            return "student"
        return self._normalize_role(user_doc.get("role"))

    def store_embedding(self, user_id: str, embedding: list[float]) -> dict[str, Any]:
        return self.databases.update_document(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_users_collection_id,
            document_id=user_id,
            data={"embedding": embedding},
        )

    def list_sessions(self, admin_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        queries: list[Any] = [Query.limit(limit), Query.order_desc("start_time")]
        if admin_id:
            queries.append(Query.equal("admin_id", [admin_id]))

        response = self.databases.list_documents(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_sessions_collection_id,
            queries=queries,
        )
        return response.get("documents", [])

    def get_session_by_id(self, session_id: str) -> dict[str, Any] | None:
        try:
            return self.databases.get_document(
                database_id=settings.appwrite_database_id,
                collection_id=settings.appwrite_sessions_collection_id,
                document_id=session_id,
            )
        except AppwriteException as exc:
            if getattr(exc, "code", None) == 404:
                return None
            raise

    def get_active_session(self) -> dict[str, Any] | None:
        response = self.databases.list_documents(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_sessions_collection_id,
            queries=[Query.equal("is_active", [True]), Query.order_desc("start_time"), Query.limit(1)],
        )
        docs = response.get("documents", [])
        return docs[0] if docs else None

    def deactivate_active_sessions(self) -> None:
        response = self.databases.list_documents(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_sessions_collection_id,
            queries=[Query.equal("is_active", [True]), Query.limit(200)],
        )

        for doc in response.get("documents", []):
            self.databases.update_document(
                database_id=settings.appwrite_database_id,
                collection_id=settings.appwrite_sessions_collection_id,
                document_id=doc.get("$id"),
                data={"is_active": False, "end_time": doc.get("end_time") or self._now_iso()},
            )

    def create_session(
        self,
        admin_id: str,
        class_name: str,
        latitude: float,
        longitude: float,
        radius_meters: float,
        end_time: str | None,
    ) -> dict[str, Any]:
        self.deactivate_active_sessions()

        session_id = ID.unique()
        now_iso = self._now_iso()

        return self.databases.create_document(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_sessions_collection_id,
            document_id=session_id,
            data={
                "session_id": session_id,
                "admin_id": admin_id,
                "class_name": class_name,
                "start_time": now_iso,
                "end_time": end_time,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "radius_meters": float(radius_meters),
                "is_active": True,
            },
        )

    def stop_session(self, session_id: str) -> dict[str, Any]:
        return self.databases.update_document(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_sessions_collection_id,
            document_id=session_id,
            data={"is_active": False, "end_time": self._now_iso()},
        )

    def find_attendance_for_session(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        response = self.databases.list_documents(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_attendance_collection_id,
            queries=[Query.equal("user_id", [user_id]), Query.equal("session_id", [session_id]), Query.limit(1)],
        )
        docs = response.get("documents", [])
        return docs[0] if docs else None

    def create_session_attendance(
        self,
        user_id: str,
        session_id: str,
        status: str,
        distance: float,
    ) -> tuple[bool, dict[str, Any], str]:
        existing = self.find_attendance_for_session(user_id=user_id, session_id=session_id)
        if existing:
            return False, existing, "Attendance already submitted for this session."

        doc_id = ID.unique()
        timestamp = self._now_iso()
        record = self.databases.create_document(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_attendance_collection_id,
            document_id=doc_id,
            data={
                "id": doc_id,
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": timestamp,
                "date": timestamp.split("T", 1)[0],
                "status": status,
                "distance": float(distance),
            },
        )
        return True, record, "Attendance processed successfully."

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
                "session_id": "",
                "timestamp": timestamp,
                "date": today,
                "status": status,
                "distance": 0.0,
            },
        )
        return True, record, "Attendance marked successfully."

    def get_attendance(self, filters: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
        search = (filters.get("search") or "").strip().lower()
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        session_id = filters.get("session_id")
        limit = int(filters.get("limit", 100))
        offset = int(filters.get("offset", 0))

        attendance_docs = self.databases.list_documents(
            database_id=settings.appwrite_database_id,
            collection_id=settings.appwrite_attendance_collection_id,
            queries=[Query.limit(5000)],
        ).get("documents", [])

        users = self.get_all_users()
        user_by_id = {doc.get("user_id"): doc for doc in users}
        sessions = self.list_sessions(limit=5000)
        session_by_id = {doc.get("session_id") or doc.get("$id"): doc for doc in sessions}

        enriched: list[dict[str, Any]] = []
        for doc in attendance_docs:
            uid = doc.get("user_id", "")
            user_doc = user_by_id.get(uid, {})
            attendance_date = doc.get("date") or ""
            row_session_id = str(doc.get("session_id") or "")

            if session_id and row_session_id != session_id:
                continue

            if start_date and attendance_date and attendance_date < start_date:
                continue
            if end_date and attendance_date and attendance_date > end_date:
                continue

            session_doc = session_by_id.get(row_session_id, {})

            row = {
                "id": doc.get("id") or doc.get("$id"),
                "user_id": uid,
                "session_id": row_session_id or None,
                "user_name": user_doc.get("name") or "Unknown",
                "user_code": uid,
                "email": user_doc.get("email") or "",
                "status": doc.get("status") or "present",
                "distance": doc.get("distance"),
                "timestamp": doc.get("timestamp") or doc.get("$createdAt"),
                "attendance_date": attendance_date,
                "class_name": session_doc.get("class_name") or "",
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
