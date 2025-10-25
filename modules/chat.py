# carelog/modules/chat.py

from __future__ import annotations

from datetime import datetime
import uuid
from typing import Dict, List, Optional


class ChatService:
    """Manages patient ↔ clinician conversations, including general and direct channels."""

    def __init__(self, carelog_service) -> None:
        self._service = carelog_service

    def _ensure_chat_store(self, hospital_id: str) -> Dict[str, Dict]:
        """Ensures the base chat structure exists for a hospital and returns it."""
        hospitals = self._service._data.setdefault('hospitals', {})
        hospital = hospitals.setdefault(
            hospital_id,
            {
                "users": {},
                "notes": [],
                "alerts": [],
                "chats": {
                    "general": {},
                    "direct": {}
                }
            }
        )
        chats = hospital.setdefault('chats', {})
        chats.setdefault('general', {})
        chats.setdefault('direct', {})
        return chats

    def _ensure_general_thread(self, hospital_id: str, patient_username: str) -> List[Dict]:
        chats = self._ensure_chat_store(hospital_id)
        general = chats.setdefault('general', {})
        return general.setdefault(patient_username, [])

    def _ensure_direct_thread(self, hospital_id: str, patient_username: str, clinician_username: str) -> List[Dict]:
        chats = self._ensure_chat_store(hospital_id)
        direct = chats.setdefault('direct', {})
        patient_threads = direct.setdefault(patient_username, {})
        return patient_threads.setdefault(clinician_username, [])

    def add_general_message(
        self,
        hospital_id: str,
        patient_username: str,
        sender_username: str,
        sender_role: str,
        message: str
    ) -> Optional[Dict]:
        """Adds a message to the patient's general channel (visible to all clinicians)."""
        text = (message or "").strip()
        if not text:
            return None

        thread = self._ensure_general_thread(hospital_id, patient_username)
        entry = self._build_message(
            sender_username,
            sender_role,
            text,
            channel="general",
            patient_username=patient_username
        )
        thread.append(entry)
        self._service._save_data()
        return entry

    def get_general_messages(
        self,
        hospital_id: str,
        patient_username: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Retrieves the ordered message history for the patient's general channel."""
        thread = list(self._ensure_general_thread(hospital_id, patient_username))
        thread.sort(key=lambda item: item.get("timestamp", ""))
        if limit is not None:
            return thread[-limit:]
        return thread

    def add_direct_message(
        self,
        hospital_id: str,
        patient_username: str,
        clinician_username: str,
        sender_username: str,
        sender_role: str,
        message: str
    ) -> Optional[Dict]:
        """Adds a message to the direct channel between a patient and a specific clinician."""
        text = (message or "").strip()
        if not text:
            return None

        assigned = self._service.get_assigned_clinicians_for_patient(hospital_id, patient_username)
        if assigned and clinician_username not in assigned:
            return None

        thread = self._ensure_direct_thread(hospital_id, patient_username, clinician_username)
        entry = self._build_message(
            sender_username,
            sender_role,
            text,
            channel="direct",
            patient_username=patient_username,
            clinician_username=clinician_username
        )
        thread.append(entry)
        self._service._save_data()
        return entry

    def get_direct_messages(
        self,
        hospital_id: str,
        patient_username: str,
        clinician_username: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Retrieves the ordered message history between a patient and clinician."""
        thread = list(self._ensure_direct_thread(hospital_id, patient_username, clinician_username))
        thread.sort(key=lambda item: item.get("timestamp", ""))
        if limit is not None:
            return thread[-limit:]
        return thread

    def list_general_patients(self, hospital_id: str) -> List[str]:
        """Lists patients with activity on the general channel, newest first."""
        chats = self._ensure_chat_store(hospital_id)
        general = chats.get('general', {})
        patients = []
        for patient_username, messages in general.items():
            last_ts = messages[-1].get("timestamp") if messages else ""
            patients.append((patient_username, last_ts))
        patients.sort(key=lambda item: item[1] or "", reverse=True)
        return [username for username, _ in patients]

    def list_direct_threads_for_clinician(self, hospital_id: str, clinician_username: str) -> List[str]:
        """Lists patient usernames with direct chat history for a clinician, newest first."""
        chats = self._ensure_chat_store(hospital_id)
        direct = chats.get('direct', {})
        patients = []
        for patient_username, clinician_threads in direct.items():
            if clinician_username in clinician_threads:
                messages = clinician_threads[clinician_username]
                last_ts = messages[-1].get("timestamp") if messages else ""
                patients.append((patient_username, last_ts))
        patients.sort(key=lambda item: item[1] or "", reverse=True)
        return [username for username, _ in patients]

    def _build_message(self, sender_username: str, sender_role: str, text: str, **extra: Dict) -> Dict:
        """Creates a persisted chat message entry."""
        timestamp = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": timestamp,
            "sender": sender_username,
            "sender_role": sender_role,
            "text": text
        }
        message.update(extra)
        return message
