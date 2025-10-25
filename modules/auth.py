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

    def register_user(self, username, password, role, hospital_id, full_name, dob, sex, pronouns, bio):
        is_new_hospital = hospital_id not in self._data['hospitals']

        # Enforce that only an admin can create a new hospital
        if is_new_hospital and role != 'admin':
            return 'hospital_not_found'

        if is_new_hospital:
            self._data['hospitals'][hospital_id] = {"users": {}, "notes": [], "alerts": []}
        
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
            'status': status,
            'full_name': full_name,
            'dob': dob,
            'sex': sex,
            'pronouns': pronouns,
            'bio': bio,
            'assigned_clinicians': [] # For patients
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
                self.current_user = User(
                    username=user_data['username'],
                    password_hash=user_data['password_hash'],
                    role=user_data['role'],
                    full_name=user_data.get('full_name'),
                    dob=user_data.get('dob'),
                    sex=user_data.get('sex'),
                    pronouns=user_data.get('pronouns'),
                    bio=user_data.get('bio')
                )
                return self.current_user
        return None
        
    def logout(self):
        self.current_user = None

    def add_note(self, note: PatientNote, hospital_id):
        if hospital_id in self._data['hospitals']:
            self._data['hospitals'][hospital_id]['notes'].append(note.__dict__)
            # Create an alert if pain is 10
            if note.pain == 10 and note.source == 'patient':
                alert = {"alert_id": str(note.note_id), "patient_id": note.patient_id, "timestamp": note.timestamp, "status": "new"}
                if 'alerts' not in self._data['hospitals'][hospital_id]: self._data['hospitals'][hospital_id]['alerts'] = []
                self._data['hospitals'][hospital_id]['alerts'].append(alert)
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
        all_patient_notes = [n for n in hospital_data.get('notes', []) if n.get('patient_id') == patient_id]
        
        # If the current user is a clinician, apply access control
        if self.current_user and self.current_user.role == 'clinician':
            patient_user_key = f"{patient_id}_patient"
            patient_data = hospital_data.get('users', {}).get(patient_user_key, {})
            assigned_clinicians = patient_data.get('assigned_clinicians', [])

            if self.current_user.username in assigned_clinicians:
                # Clinician is assigned, filter out private notes from patient
                # Only show notes that are not private patient notes
                return [n for n in all_patient_notes if not (n.get('source') == 'patient' and n.get('is_private'))]
            return [] # Clinician not assigned or not assigned to this patient, return no notes
        return all_patient_notes # Patient or admin can see all their notes

    def get_pending_feedback(self, hospital_id):
        pending_feedback = []
        
        # For clinicians, get a set of their assigned patient IDs for efficient filtering.
        assigned_patient_ids = None
        if self.current_user and self.current_user.role == 'clinician':
            assigned_patients_data = self.get_all_patients(hospital_id)
            assigned_patient_ids = {p['username'] for p in assigned_patients_data}

        if hospital_id in self._data['hospitals']:
            for note in self._data['hospitals'][hospital_id]['notes']:
                if note.get('ai_feedback') and note['ai_feedback']['status'] == 'pending':
                    # If the user is a clinician, only add feedback for their assigned patients.
                    if assigned_patient_ids is not None:
                        if note.get('patient_id') in assigned_patient_ids:
                            pending_feedback.append(note)
                    else: # Admins and other roles (if any) see all pending feedback.
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

    def delete_user(self, hospital_id, username, role):
        user_key = f"{username}_{role}"
        hospital_users = self._data['hospitals'].get(hospital_id, {}).get('users', {})
        if user_key in hospital_users:
            # Prevent an admin from deleting their own account
            if self.current_user and self.current_user.username == username and self.current_user.role == role:
                return False

            del hospital_users[user_key]

            # If a patient is deleted, remove their notes for data privacy and integrity.
            if role == 'patient':
                notes = self._data['hospitals'].get(hospital_id, {}).get('notes', [])
                self._data['hospitals'][hospital_id]['notes'] = [n for n in notes if n.get('patient_id') != username]
            
            # If a clinician is deleted, remove them from any patient's assigned list AND remove their authored notes.
            if role == 'clinician':
                # Remove from assignment lists
                for u_data in hospital_users.values():
                    if u_data.get('role') == 'patient' and 'assigned_clinicians' in u_data:
                        if username in u_data['assigned_clinicians']:
                            u_data['assigned_clinicians'].remove(username)
                # Remove authored notes
                notes = self._data['hospitals'].get(hospital_id, {}).get('notes', [])
                self._data['hospitals'][hospital_id]['notes'] = [n for n in notes if n.get('author_id') != username or n.get('source') != 'clinician']

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
        current_user = self.current_user
        patient_list = []
        for user_data in hospital_users.values():
            if user_data.get('role') == 'patient':
                # If clinician, only show assigned patients
                if current_user.role == 'clinician':
                    if current_user.username in user_data.get('assigned_clinicians', []):
                        patient_list.append(user_data)
                else: # Admins see all patients
                    patient_list.append(user_data)
        return patient_list

    # --- New/Modified Methods for Features ---

    def get_all_users(self, hospital_id):
        return self._data['hospitals'].get(hospital_id, {}).get('users', {})
        
    def get_user_by_username(self, hospital_id, username, role):
        """Retrieves a single user's data by username and role."""
        user_key = f"{username}_{role}"
        return self._data['hospitals'].get(hospital_id, {}).get('users', {}).get(user_key, {})

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

    def update_user_profile(self, hospital_id, username, role, details):
        user_key = f"{username}_{role}"
        user_data = self._data['hospitals'].get(hospital_id, {}).get('users', {}).get(user_key)
        if not user_data:
            return False

        user_data['full_name'] = details.get('full_name', user_data.get('full_name'))
        user_data['dob'] = details.get('dob', user_data.get('dob'))
        user_data['sex'] = details.get('sex', user_data.get('sex'))
        user_data['pronouns'] = details.get('pronouns', user_data.get('pronouns'))
        user_data['bio'] = details.get('bio', user_data.get('bio'))

        if 'new_password' in details and details['new_password']:
            salt = os.urandom(16).hex()
            password_to_hash = salt + details['new_password']
            password_hash = hashlib.sha256(password_to_hash.encode()).hexdigest()
            user_data['salt'] = salt
            user_data['password_hash'] = password_hash

        self._save_data()
        return True

    def update_note(self, hospital_id, note_id, updated_data):
        notes = self._data['hospitals'].get(hospital_id, {}).get('notes', [])
        for note in notes:
            if note.get('note_id') == note_id:
                note.update(updated_data)
                self._save_data()
                return True
        return False

    def get_all_clinicians(self, hospital_id):
        hospital_users = self._data['hospitals'].get(hospital_id, {}).get('users', {})
        return [data for data in hospital_users.values() if data.get('role') == 'clinician' and data.get('status') == 'approved']

    def assign_clinician_to_patient(self, hospital_id, patient_username, clinician_username):
        patient_key = f"{patient_username}_patient"
        patient_data = self._data['hospitals'].get(hospital_id, {}).get('users', {}).get(patient_key)
        if patient_data:
            if 'assigned_clinicians' not in patient_data:
                patient_data['assigned_clinicians'] = []
            if clinician_username not in patient_data['assigned_clinicians']:
                patient_data['assigned_clinicians'].append(clinician_username)
                self._save_data()
                return True
        return False

    def unassign_clinician_from_patient(self, hospital_id, patient_username, clinician_username):
        patient_key = f"{patient_username}_patient"
        patient_data = self._data['hospitals'].get(hospital_id, {}).get('users', {}).get(patient_key)
        if patient_data and 'assigned_clinicians' in patient_data:
            if clinician_username in patient_data['assigned_clinicians']:
                patient_data['assigned_clinicians'].remove(clinician_username)
                self._save_data()
                return True
        return False

    def search_notes(self, hospital_id, patient_id, search_term):
        all_notes = self.get_notes_for_patient(hospital_id, patient_id)
        if not search_term:
            return all_notes
        
        search_term = search_term.lower()
        
        def note_matches(note):
            notes_text = note.get('notes', '').lower()
            diagnoses_text = note.get('diagnoses', '').lower()
            return search_term in notes_text or search_term in diagnoses_text

        return [note for note in all_notes if note_matches(note)]

    def get_pain_alerts(self, hospital_id):
        alerts = self._data['hospitals'].get(hospital_id, {}).get('alerts', [])
        # Clinicians and Admins should see all alerts for the hospital.
        # Patients do not have access to this function.
        return alerts

    def dismiss_alert(self, hospital_id, alert_id):
        alerts = self._data['hospitals'].get(hospital_id, {}).get('alerts', [])
        self._data['hospitals'][hospital_id]['alerts'] = [a for a in alerts if a.get('alert_id') != alert_id]
        self._save_data()
        return True
