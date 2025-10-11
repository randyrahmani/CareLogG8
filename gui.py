# carelog/gui.py

import streamlit as st
from modules.models import PatientNote
import json
import datetime
import pandas as pd

# --- Page navigation helpers ---
def set_page_welcome():
    st.session_state.auth_page = 'welcome'

def set_page_login():
    st.session_state.auth_page = 'login'

def set_page_register():
    st.session_state.auth_page = 'register'

# --- Authentication Pages ---

def show_welcome_page():
    """Displays a welcome screen with buttons to navigate."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("Welcome to CareLog 🏥")
        st.write("A multi-hospital platform for empathetic logging.")
        st.info("To begin, please select an option below. You will be asked for your hospital's unique ID.")
        
        st.button("Login to an Existing Account", on_click=set_page_login, width='stretch', type="primary")
        st.button("Create a New Account", on_click=set_page_register, width='stretch')

def show_login_form(service):
    """Displays the login form, requiring a role selection."""
    st.button("← Back to Welcome", on_click=set_page_welcome)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("Account Login")
        with st.form("login_form"):
            hospital_id = st.text_input("Hospital ID", help="Enter the unique ID for your hospital.")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Login as", ["patient", "clinician", "admin"])
            submitted = st.form_submit_button("Login", width='stretch')

            if submitted:
                if not hospital_id or not username:
                    st.error("Hospital ID and Username are required.")
                else:
                    user = service.login(username, password, role, hospital_id)
                    if user:
                        st.session_state.current_user = user
                        st.session_state.hospital_id = hospital_id
                        st.session_state.auth_page = 'welcome'
                        st.rerun()
                    else:
                        st.error("Invalid credentials for the selected role.")

def show_register_form(service):
    """Displays the registration form."""
    st.button("← Back to Welcome", on_click=set_page_welcome)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("Create a New Account")
        with st.form("register_form"):
            hospital_id = st.text_input("Hospital ID", help="If your hospital is new, this will create it. If it exists, you will join it.")
            username = st.text_input("Choose a Username")
            password = st.text_input("Choose a Password", type="password")
            role = st.selectbox("Select your role", ["patient", "clinician", "admin"])
            submitted = st.form_submit_button("Register", width='stretch')

            if submitted:
                if not hospital_id or not username or not password:
                    st.error("All fields are required.")
                else:
                    if service.register_user(username, password, role, hospital_id):
                        st.success(f"User '{username}' registered for '{hospital_id}'! Please go back to log in.")
                        st.balloons()
                    else:
                        st.error(f"A profile for username '{username}' with the role '{role}' already exists at this hospital.")

# --- Main Application UI ---

def show_main_app(service):
    """Displays the main app UI after successful login."""
    user = st.session_state.current_user
    hospital_id = st.session_state.hospital_id

    st.sidebar.title(f"Welcome, {user.username}!")
    st.sidebar.info(f"**Hospital:** {hospital_id}")
    st.sidebar.write(f"**Role:** {user.role.capitalize()}")

    if st.sidebar.button("Logout"):
        service.logout()
        st.session_state.current_user = None
        st.session_state.hospital_id = None
        st.session_state.auth_page = 'welcome'
        st.rerun()

    st.sidebar.divider()

    if user.role == 'clinician':
        page = st.sidebar.radio("Navigation", ["Add Patient Note", "View Patient Notes"])
        if page == "Add Patient Note":
            _render_add_note_page(service, hospital_id)
        elif page == "View Patient Notes":
            _render_view_notes_page(service, hospital_id)
    elif user.role == 'patient':
        page = st.sidebar.radio("Navigation", ["View My Notes", "Add My Entry"])
        if page == "View My Notes":
            _render_view_notes_page(service, hospital_id, patient_id=user.username)
        elif page == "Add My Entry":
            _render_add_patient_entry_page(service, hospital_id)
    elif user.role == 'admin':
        page = st.sidebar.radio("Navigation", ["User Management & Export"])
        if page == "User Management & Export":
            _render_admin_page(service, hospital_id)

def _render_add_note_page(service, hospital_id):
    st.header("Add a New Patient Note")
    patients = service.get_all_patients(hospital_id)
    if not patients:
        st.warning("No patients found for this hospital.")
        return
    patient_usernames = [p['username'] for p in patients]

    with st.form("add_note_form"):
        selected_patient = st.selectbox("Select Patient", patient_usernames)
        mood = st.slider("Mood (0-10)", 0, 10, 5)
        pain = st.slider("Pain (0-10)", 0, 10, 5)
        appetite = st.slider("Appetite (0-10)", 0, 10, 5)
        notes = st.text_area("Narrative Notes (patient stories, cultural needs, etc.)")
        diagnoses = st.text_input("Medical Notes and Diagnoses")
        submitted = st.form_submit_button("Save Note")
        if submitted:
            author_id = st.session_state.current_user.username
            note = PatientNote(
                patient_id=selected_patient, author_id=author_id, mood=mood, pain=pain,
                appetite=appetite, notes=notes, diagnoses=diagnoses, source="clinician", hospital_id=hospital_id
            )
            service.add_note(note, hospital_id)
            st.success(f"Note added successfully for patient '{selected_patient}'.")

def _render_add_patient_entry_page(service, hospital_id):
    st.header("Add a New Entry")
    with st.form("add_patient_entry_form"):
        mood = st.slider("My Mood (0-10)", 0, 10, 5)
        pain = st.slider("My Pain Level (0-10)", 0, 10, 5)
        appetite = st.slider("My Appetite (0-10)", 0, 10, 5)
        notes = st.text_area("How are you feeling today?")
        submitted = st.form_submit_button("Save Entry")
        if submitted:
            user = st.session_state.current_user
            note = PatientNote(
                patient_id=user.username, author_id=user.username, mood=mood, pain=pain,
                appetite=appetite, notes=notes, diagnoses="", source="patient", hospital_id=hospital_id
            )
            service.add_note(note, hospital_id)
            st.success("Your entry has been saved successfully.")

def _render_view_notes_page(service, hospital_id, patient_id=None):
    if patient_id:
        st.header("My Medical Notes & Entries")
        notes = service.get_notes_for_patient(hospital_id, patient_id)
    else:
        st.header("View All Patient Notes & Entries")
        patients = service.get_all_patients(hospital_id)
        if not patients:
            st.warning("No patients found for this hospital.")
            return
        patient_usernames = [p['username'] for p in patients]
        selected_patient = st.selectbox("Select a patient to view their notes", patient_usernames)
        notes = service.get_notes_for_patient(hospital_id, selected_patient)

    if not notes:
        st.info("No notes or entries found for this patient.")
    else:
        for note in sorted(notes, key=lambda x: x['timestamp'], reverse=True):
            source = note.get("source", "clinician")
            if source == "patient":
                expander_title = f"Patient Entry from {note['timestamp']}"
                st.info(f"Entry from Patient: {note['author_id']}")
            else:
                expander_title = f"Clinical Note from {note['timestamp']} (by {note['author_id']})"
                st.warning(f"Note from Clinician: {note['author_id']}")
            
            with st.expander(expander_title):
                st.metric("Mood", f"{note['mood']}/10")
                st.metric("Pain", f"{note['pain']}/10")
                st.metric("Appetite", f"{note['appetite']}/10")
                if source == "patient":
                    st.write("**Patient wrote:**")
                else:
                    st.write("**Narrative Notes:**")
                st.write(note['notes'] or "_No notes provided._")
                if source == "clinician":
                    st.write("**Diagnoses/Medical Notes:**")
                    st.write(note['diagnoses'] or "_No diagnoses provided._")

def _render_admin_page(service, hospital_id):
    st.header(f"Admin Panel for {hospital_id}")
    st.subheader("User Management")
    users_dict = service.get_all_users(hospital_id)
    if not users_dict:
        st.info("No users found for this hospital.")
    else:
        user_data_list = [
            {"Username": user_data['username'], "Role": user_data['role']}
            for user_data in users_dict.values()
        ]
        df = pd.DataFrame(user_data_list)
        df.index = pd.RangeIndex(start=1, stop=len(df) + 1, step=1)
        st.dataframe(df, use_container_width=True)
    
    st.divider()
    st.header("Data Export")
    st.warning(f"The following exports contain data for **{hospital_id} ONLY**.")
    hospital_data = service.get_hospital_dataset(hospital_id)

    st.subheader("1. Export as Raw JSON")
    json_string = json.dumps(hospital_data, indent=4)
    st.download_button(
       "Download Hospital Data (JSON)", json_string,
       f"carelog_{hospital_id}_export_{datetime.date.today()}.json", "application/json"
    )
    st.divider()

    st.subheader("2. Export as CSV")
    col1, col2 = st.columns(2)
    with col1:
        users_dict_export = hospital_data.get('users', {})
        if users_dict_export:
            display_users = [
                {'username': u_data['username'], 'role': u_data['role']}
                for u_data in users_dict_export.values()
            ]
            users_df = pd.DataFrame(display_users)
            st.download_button(
                "Download Users (CSV)", users_df.to_csv(index=False).encode('utf-8'),
                f"carelog_{hospital_id}_users_{datetime.date.today()}.csv", "text/csv"
            )
    with col2:
        notes_list = hospital_data.get('notes', [])
        if notes_list:
            notes_df = pd.DataFrame(notes_list)
            desired_columns = ['timestamp', 'patient_id', 'author_id', 'source', 'mood', 'pain', 'appetite', 'notes', 'diagnoses']
            for col in desired_columns:
                if col not in notes_df.columns: notes_df[col] = None
            st.download_button(
                "Download Notes (CSV)", notes_df[desired_columns].to_csv(index=False).encode('utf-8'),
                f"carelog_{hospital_id}_notes_{datetime.date.today()}.csv", "text/csv"
            )
    st.divider()

    st.subheader("3. Export as Human-Readable Report")
    st.write("Download all notes as a simple, formatted text file for easy reading or printing.")
    notes_list = hospital_data.get('notes', [])
    if notes_list:
        report_content = [f"CareLog Notes Report - Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", "="*80 + "\n"]
        for note in sorted(notes_list, key=lambda x: x['timestamp']):
            report_content.extend([
                f"Timestamp: {note['timestamp']}",
                f"Patient ID: {note['patient_id']}",
                f"Author ID: {note['author_id']}",
                f"Entry Source: {note.get('source', 'clinician').capitalize()}",
                f"Mood: {note['mood']}/10 | Pain: {note['pain']}/10 | Appetite: {note['appetite']}/10",
                "\nPatient Wrote:\n" + "-"*15 if note.get('source') == 'patient' else "\nNarrative Notes:\n" + "-"*18,
                note['notes'] or "N/A"
            ])
            if note.get('source', 'clinician') == 'clinician':
                report_content.extend(["\nDiagnoses/Medical Notes:\n" + "-"*25, note['diagnoses'] or "N/A"])
            report_content.append("\n" + "="*80 + "\n")
        
        final_report = "\n".join(report_content)
        st.download_button(
            label="Download Notes Report (.txt)", data=final_report.encode('utf-8'),
            file_name=f"carelog_report_notes_{datetime.date.today()}.txt", mime="text/plain"
        )