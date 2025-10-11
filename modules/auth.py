# carelog/modules/auth.py

import json
import hashlib
from modules.encryption import encryptor
from modules.models import User, PatientNote

DATA_FILE = 'records.json'

class CareLogService:
    """Handles data management for users and notes."""
    def __init__(self):
        self.current_user = None
        self._data = self._load_data()

    def _load_data(self):
        """Loads the entire JSON data file."""
        try:
            with open(DATA_FILE, 'r') as f:
                encrypted_data = f.read()
                if not encrypted_data:
                    return {"users": {}, "notes": []}
                decrypted_data = encryptor.decrypt(encrypted_data.encode())
                return json.loads(decrypted_data.decode())
        except FileNotFoundError:
            return {"users": {}, "notes": []}

    def _save_data(self):
        """Saves the entire JSON data file."""
        with open(DATA_FILE, 'w') as f:
            data_to_encrypt = json.dumps(self._data, indent=4)
            encrypted_data = encryptor.encrypt(data_to_encrypt.encode())
            f.write(encrypted_data.decode())

    def register_user(self, username, password, role):
        """Registers a new user."""
        if username in self._data['users']:
            return False
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self._data['users'][username] = {'password_hash': password_hash, 'role': role}
        self._save_data()
        return True

    def login(self, username, password):
        """Logs in a user and returns a User object."""
        user_data = self._data['users'].get(username)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user_data and user_data['password_hash'] == password_hash:
            self.current_user = User(username, user_data['password_hash'], user_data['role'])
            return self.current_user
        return None
        
    def logout(self):
        """Logs out the current user."""
        self.current_user = None

    def add_note(self, note: PatientNote):
        """Adds a patient note to the database."""
        self._data['notes'].append(note.__dict__)
        self._save_data()

    def get_notes_for_patient(self, patient_id):
        """Retrieves all notes for a specific patient."""
        return [note for note in self._data['notes'] if note['patient_id'] == patient_id]

    def get_all_patients(self):
        """Returns a list of all users with the 'patient' role."""
        return [
            {"username": u, "role": d['role']} 
            for u, d in self._data['users'].items() if d['role'] == 'patient'
        ]

    def get_all_users(self):
        """Returns the dictionary of all users."""
        return self._data['users']
        
    def get_full_dataset(self):
        """
        Returns the entire decrypted dataset (users and notes) as a dictionary.
        This is intended for admin export purposes.
        """
        return self._data