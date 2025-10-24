# carelog/modules/auth.py

import json
import hashlib
import os
from modules.encryption import encryptor
from modules.models import User, PatientNote
from modules.gemini import generate_feedback
from cryptography.fernet import InvalidToken

DATA_FILE = 'records.json'

class CareLogService:
    def __init__(self):
        self.current_user = None
        self._data = self._load_data()

    def _load_data(self):
        try:
            with open(DATA_FILE, 'r') as f:
                encrypted_data = f.read()
                if not encrypted_data:
                    return {"hospitals": {}}
                decrypted_data = encryptor.decrypt(encrypted_data.encode()).decode()
                return json.loads(decrypted_data)
        except (FileNotFoundError, InvalidToken, json.JSONDecodeError) as e:
            # If the file doesn't exist, is corrupt, or not valid JSON, start fresh.
            # In a real-world app, you might want to log this error or alert the admin.
            print(f"Warning: Could not load data file ({e}). Starting with a new dataset.")
            return {"hospitals": {}}

    def _save_data(self):
        with open(DATA_FILE, 'w') as f:
            data_to_encrypt = json.dumps(self._data, indent=4)
            encrypted_data = encryptor.encrypt(data_to_encrypt.encode())
            f.write(encrypted_data.decode())

    def register_user(self, username, password, role, hospital_id):
        is_new_hospital = hospital_id not in self._data['hospitals']
        if is_new_hospital:
            self._data['hospitals'][hospital_id] = {"users": {}, "notes": []}
        
        hospital_users = self._data['hospitals'][hospital_id]['users']
        user_key = f"{username}_{role}"
        
        if user_key in hospital_users:
            return False

        salt = os.urandom(16).hex()
        password_to_hash = salt + password
        password_hash = hashlib.sha256(password_to_hash.encode()).hexdigest()
        
        # Approval logic for new admins and clinicians
        status = 'approved'
        if (role == 'admin' or role == 'clinician') and not is_new_hospital:
            status = 'pending'

        hospital_users[user_key] = {
            'username': username,
            'password_hash': password_hash,
            'role': role,
            'salt': salt,
            'status': status
        }
        self._save_data()
        if status == 'pending':
            return 'pending'
        return True

    def login(self, username, password, role, hospital_id):
        hospital_data = self._data['hospitals'].get(hospital_id)
        if not hospital_data:
            return None
        hospital_users = hospital_data.get('users', {})
        user_key = f"{username}_{role}"
        user_data = hospital_users.get(user_key)

        if user_data:
            # Check for approval status
            if user_data.get('status') == 'pending':
                return 'pending' # Special return value to indicate pending approval

            salt = user_data.get('salt')
            if not salt:
                 return 'error' # Indicate a data integrity issue
            password_to_check = salt + password
            hash_to_check = hashlib.sha256(password_to_check.encode()).hexdigest()

            # Use .get() for robustness in case 'password_hash' is missing from user_data
            if user_data.get('password_hash') == hash_to_check:
                self.current_user = User(user_data['username'], user_data['password_hash'], user_data['role'])
                return self.current_user
        return None
        
    def logout(self):
        self.current_user = None

    def add_note(self, note: PatientNote, hospital_id):
        if hospital_id in self._data['hospitals']:
            self._data['hospitals'][hospital_id]['notes'].append(note.__dict__)
            self._save_data()

    def generate_and_store_ai_feedback(self, note_id, hospital_id):
        if hospital_id in self._data['hospitals']:
            for note in self._data['hospitals'][hospital_id]['notes']:
                if note['note_id'] == note_id:
                    # Use .get() for robustness in case of missing keys from old data or corruption
                    notes_text = note.get('notes', '')
                    mood_val = note.get('mood', 5) # Default to 5 if missing
                    pain_val = note.get('pain', 5) # Default to 5 if missing
                    appetite_val = note.get('appetite', 5) # Default to 5 if missing
                    feedback = generate_feedback(notes_text, mood_val, pain_val, appetite_val)
                    if feedback:
                        note['ai_feedback'] = {
                            "text": feedback,
                            "status": "pending"
                        }
                        self._save_data()
                        return True
        return False

    def get_notes_for_patient(self, hospital_id, patient_id):
        hospital_data = self._data['hospitals'].get(hospital_id, {})
        return [n for n in hospital_data.get('notes', []) if n['patient_id'] == patient_id]

    def get_pending_feedback(self, hospital_id):
        pending_feedback = []
        if hospital_id in self._data['hospitals']:
            for note in self._data['hospitals'][hospital_id]['notes']:
                if note.get('ai_feedback') and note['ai_feedback']['status'] == 'pending':
                    pending_feedback.append(note)
        return pending_feedback

    def approve_ai_feedback(self, note_id, hospital_id, edited_feedback_text):
        if hospital_id in self._data['hospitals']:
            for note in self._data['hospitals'][hospital_id]['notes']:
                if note['note_id'] == note_id:
                    if note.get('ai_feedback'):
                        note['ai_feedback']['text'] = edited_feedback_text # Update with edited text
                        note['ai_feedback']['status'] = 'approved' 
                        self._save_data()
                        return True
        return False

    def reject_ai_feedback(self, note_id, hospital_id):
        if hospital_id in self._data['hospitals']:
            for note in self._data['hospitals'][hospital_id]['notes']:
                if note.get('note_id') == note_id:
                    if 'ai_feedback' in note:
                        del note['ai_feedback']
                        self._save_data()
                        return True
        return False

    def delete_note(self, note_id, hospital_id):
        if hospital_id in self._data['hospitals']:
            self._data['hospitals'][hospital_id]['notes'] = [n for n in self._data['hospitals'][hospital_id]['notes'] if n['note_id'] != note_id]
            self._save_data()
            return True
        return False

    def get_all_patients(self, hospital_id):
        hospital_users = self._data['hospitals'].get(hospital_id, {}).get('users', {})
        patient_list = []
        for user_data in hospital_users.values():
            if user_data.get('role') == 'patient':
                patient_list.append({
                    "username": user_data.get('username'),
                    "role": user_data.get('role')
                })
        return patient_list

    def get_all_users(self, hospital_id):
        return self._data['hospitals'].get(hospital_id, {}).get('users', {})
        
    def get_hospital_dataset(self, hospital_id):
        return self._data['hospitals'].get(hospital_id, {"users": {}, "notes": []})

    def get_all_hospitals(self):
        return list(self._data['hospitals'].keys())

    def get_pending_users(self, hospital_id, role):
        hospital_users = self._data['hospitals'].get(hospital_id, {}).get('users', {})
        pending_users = []
        for user_key, user_data in hospital_users.items():
            if user_data.get('role') == role and user_data.get('status') == 'pending':
                pending_users.append(user_data)
        return pending_users

    def approve_user(self, username, role, hospital_id):
        hospital_users = self._data['hospitals'].get(hospital_id, {}).get('users', {})
        user_key = f"{username}_{role}"
        if user_key in hospital_users:
            hospital_users[user_key]['status'] = 'approved'
            self._save_data()
            return True
        return False
