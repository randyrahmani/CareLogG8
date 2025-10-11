# carelog/modules/auth.py

import json
import hashlib
import os
from modules.encryption import encryptor
from modules.models import User, PatientNote

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
                decrypted_data = encryptor.decrypt(encrypted_data.encode())
                return json.loads(decrypted_data.decode())
        except FileNotFoundError:
            return {"hospitals": {}}

    def _save_data(self):
        with open(DATA_FILE, 'w') as f:
            data_to_encrypt = json.dumps(self._data, indent=4)
            encrypted_data = encryptor.encrypt(data_to_encrypt.encode())
            f.write(encrypted_data.decode())

    def register_user(self, username, password, role, hospital_id):
        if hospital_id not in self._data['hospitals']:
            self._data['hospitals'][hospital_id] = {"users": {}, "notes": []}
        
        hospital_users = self._data['hospitals'][hospital_id]['users']
        user_key = f"{username}_{role}"
        
        if user_key in hospital_users:
            return False

        salt = os.urandom(16).hex()
        password_to_hash = salt + password
        password_hash = hashlib.sha256(password_to_hash.encode()).hexdigest()
        
        hospital_users[user_key] = {
            'username': username,
            'password_hash': password_hash,
            'role': role,
            'salt': salt
        }
        self._save_data()
        return True

    def login(self, username, password, role, hospital_id):
        hospital_data = self._data['hospitals'].get(hospital_id)
        if not hospital_data:
            return None
        hospital_users = hospital_data.get('users', {})
        user_key = f"{username}_{role}"
        user_data = hospital_users.get(user_key)

        if user_data:
            salt = user_data.get('salt')
            if not salt:
                 return None
            password_to_check = salt + password
            hash_to_check = hashlib.sha256(password_to_check.encode()).hexdigest()

            if user_data['password_hash'] == hash_to_check:
                self.current_user = User(user_data['username'], user_data['password_hash'], user_data['role'])
                return self.current_user
        return None
        
    def logout(self):
        self.current_user = None

    def add_note(self, note: PatientNote, hospital_id):
        if hospital_id in self._data['hospitals']:
            self._data['hospitals'][hospital_id]['notes'].append(note.__dict__)
            self._save_data()

    def get_notes_for_patient(self, hospital_id, patient_id):
        hospital_data = self._data['hospitals'].get(hospital_id, {})
        return [n for n in hospital_data.get('notes', []) if n['patient_id'] == patient_id]

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