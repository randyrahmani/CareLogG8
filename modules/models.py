# carelog/modules/models.py

from datetime import datetime
import uuid

class User:
    """Base class for a user."""
    def __init__(self, username, password_hash, role, full_name, dob, sex, pronouns, bio, user_id=None):
        self.user_id = user_id or username
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.full_name = full_name
        self.dob = dob
        self.sex = sex
        self.pronouns = pronouns
        self.bio = bio

class PatientNote:
    """Class for patient notes, now requiring a hospital_id."""
    def __init__(self, patient_id, author_id, mood, pain, appetite, notes, diagnoses, source, hospital_id, is_private=False, hidden_from_patient=False, note_id=None, timestamp=None):
        self.note_id = note_id or str(uuid.uuid4())
        self.hospital_id = hospital_id
        self.patient_id = patient_id
        self.author_id = author_id
        self.timestamp = timestamp or datetime.now().isoformat()
        self.mood = mood
        self.pain = pain
        self.appetite = appetite
        self.notes = notes
        self.diagnoses = diagnoses
        self.source = source
        self.is_private = is_private
        self.hidden_from_patient = hidden_from_patient
