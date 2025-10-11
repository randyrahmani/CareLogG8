import streamlit as st
from modules.models import PatientNote
import json
import datetime
import pandas as pd

# --- NEW: Helper functions to change the page state ---
def set_page_welcome():
    st.session_state.auth_page = 'welcome'

def set_page_login():
    st.session_state.auth_page = 'login'

def set_page_register():
    st.session_state.auth_page = 'register'


# --- NEW: The Welcome Page ---
def show_welcome_page():
    """Displays a welcome screen with buttons to navigate."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("Welcome to CareLog 🩺")
        st.write("A culturally aware, reflective, and empathetic logging system.")
        st.write("Please select an option to continue.")
        
        st.button("Login to an Existing Account", on_click=set_page_login, use_container_width=True, type="primary")
        st.button("Create a New Account", on_click=set_page_register, use_container_width=True)


# --- NEW: The Login Page/Form ---
def show_login_form(service):
    """Displays only the login form."""
    st.button("← Back to Welcome", on_click=set_page_welcome)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("Account Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                user = service.login(username, password)
                if user:
                    st.session_state.current_user = user
                    st.session_state.auth_page = 'welcome' # Reset for next time
                    st.rerun()
                else:
                    st.error("Invalid username or password.")


# --- NEW: The Register Page/Form ---
def show_register_form(service):
    """Displays only the registration form."""
    st.button("← Back to Welcome", on_click=set_page_welcome)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.header("Create a New Account")
        with st.form("register_form"):
            username = st.text_input("Choose a Username")
            password = st.text_input("Choose a Password", type="password")
            role = st.selectbox(
                "Select your role",
                ["patient", "clinician", "admin"],
                help="Patients can view notes and add their own entries. Clinicians can add/view notes for all patients. Admins can manage users."
            )
            submitted = st.form_submit_button("Register", use_container_width=True)

            if submitted:
                if service.register_user(username, password, role):
                    st.success(f"User '{username}' registered successfully! Please go back to the welcome page to log in.")
                    st.balloons()
                else:
                    st.error("Username already exists. Please choose another one.")


# --- DELETED: The old show_login_page function is now gone ---


# --- The rest of the file remains the same ---
def show_main_app(service):
    # ... (This function is unchanged)
    user = st.session_state.current_user
    st.sidebar.title(f"Welcome, {user.username}!")
    st.sidebar.write(f"**Role:** {user.role.capitalize()}")

    if st.sidebar.button("Logout"):
        service.logout()
        st.session_state.current_user = None
        st.session_state.auth_page = 'welcome' # Reset state on logout
        st.rerun()

    st.sidebar.divider()

    if user.role == 'clinician':
        page = st.sidebar.radio("Navigation", ["Add Patient Note", "View Patient Notes"])
        if page == "Add Patient Note":
            _render_add_note_page(service)
        elif page == "View Patient Notes":
            _render_view_notes_page(service)

    elif user.role == 'patient':
        page = st.sidebar.radio("Navigation", ["View My Notes", "Add My Entry"])
        if page == "View My Notes":
            _render_view_notes_page(service, patient_id=user.username)
        elif page == "Add My Entry":
            _render_add_patient_entry_page(service)

    elif user.role == 'admin':
        page = st.sidebar.radio("Navigation", ["User Management & Export"])
        if page == "User Management & Export":
            _render_admin_page(service)

# ... (The _render_* functions for the main app are also unchanged)
def _render_add_note_page(service):
    # ... (code is the same)
    st.header("Add a New Patient Note")
    patients = service.get_all_patients()
    if not patients:
        st.warning("No patients found. Please register a patient account first.")
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
                appetite=appetite, notes=notes, diagnoses=diagnoses, source="clinician"
            )
            service.add_note(note)
            st.success(f"Note added successfully for patient '{selected_patient}'.")


def _render_add_patient_entry_page(service):
    # ... (code is the same)
    st.header("Add a New Entry")
    st.write("Share how you're feeling. Your care team will be able to see this entry.")

    with st.form("add_patient_entry_form"):
        mood = st.slider("My Mood (0-10)", 0, 10, 5)
        pain = st.slider("My Pain Level (0-10)", 0, 10, 5)
        appetite = st.slider("My Appetite (0-10)", 0, 10, 5)
        notes = st.text_area("How are you feeling today? (e.g., worries, successes, questions for your doctor)")
        submitted = st.form_submit_button("Save Entry")

        if submitted:
            user = st.session_state.current_user
            note = PatientNote(
                patient_id=user.username, author_id=user.username, mood=mood, pain=pain,
                appetite=appetite, notes=notes, diagnoses="", source="patient"
            )
            service.add_note(note)
            st.success("Your entry has been saved successfully.")


def _render_view_notes_page(service, patient_id=None):
    # ... (code is the same)
    if patient_id:
        st.header("My Medical Notes & Entries")
        notes = service.get_notes_for_patient(patient_id)
    else:
        st.header("View All Patient Notes & Entries")
        patients = service.get_all_patients()
        if not patients:
            st.warning("No patients found.")
            return
        patient_usernames = [p['username'] for p in patients]
        selected_patient = st.selectbox("Select a patient to view their notes", patient_usernames)
        notes = service.get_notes_for_patient(selected_patient)

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


def _render_admin_page(service):
    # ... (code is the same)
    st.header("User Management")
    users = service.get_all_users()
    user_data = [{"Username": u, "Role": users[u]['role']} for u in users]
    st.table(user_data)
    st.divider()

    st.header("Data Export")
    full_data = service.get_full_dataset()

    st.subheader("1. Export as Raw JSON")
    st.write("This is the complete, raw backup of the application's database.")
    json_string = json.dumps(full_data, indent=4)
    st.download_button(
       label="Download Raw Data (JSON)", data=json_string,
       file_name=f"carelog_export_raw_{datetime.date.today()}.json", mime="application/json"
    )
    st.divider()

    st.subheader("2. Export as CSV (for Excel, Google Sheets)")
    st.write("Download user and note data in separate CSV files, ideal for analysis.")
    col1, col2 = st.columns(2)
    
    with col1:
        users_dict = full_data.get('users', {})
        if users_dict:
            users_df = pd.DataFrame([{'username': u, 'role': d['role']} for u, d in users_dict.items()])
            st.download_button(
                label="Download Users (CSV)", data=users_df.to_csv(index=False).encode('utf-8'),
                file_name=f"carelog_export_users_{datetime.date.today()}.csv", mime="text/csv"
            )
    with col2:
        notes_list = full_data.get('notes', [])
        if notes_list:
            notes_df = pd.DataFrame(notes_list)
            desired_columns = ['timestamp', 'patient_id', 'author_id', 'source', 'mood', 'pain', 'appetite', 'notes', 'diagnoses']
            for col in desired_columns:
                if col not in notes_df.columns: notes_df[col] = None
            st.download_button(
                label="Download Notes (CSV)", data=notes_df[desired_columns].to_csv(index=False).encode('utf-8'),
                file_name=f"carelog_export_notes_{datetime.date.today()}.csv", mime="text/csv"
            )
    st.divider()

    st.subheader("3. Export as Human-Readable Report")
    st.write("Download all notes as a simple, formatted text file for easy reading or printing.")
    notes_list = full_data.get('notes', [])
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