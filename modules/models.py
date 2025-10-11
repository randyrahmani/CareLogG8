# carelog/modules/models.py

from datetime import datetime

class User:
    """Base class for a user."""
    def __init__(self, username, password_hash, role='patient', user_id=None):
        self.user_id = user_id or username
        self.username = username
        self.password_hash = password_hash
        self.role = role

class PatientNote:
    """Class for patient notes, now requiring a hospital_id."""
    def __init__(self, patient_id, author_id, mood, pain, appetite, notes, diagnoses, source, hospital_id):
        self.note_id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.hospital_id = hospital_id
        self.patient_id = patient_id
        self.author_id = author_id
        self.timestamp = datetime.now().isoformat()
        self.mood = mood
        self.pain = pain
        self.appetite = appetite
        self.notes = notes
        self.diagnoses = diagnoses
        self.source = source