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
        st.markdown("<h1 style='text-align: center;'>Welcome to CareLog 🏥</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>A multi-hospital platform for empathetic logging.</p>", unsafe_allow_html=True)
        st.info("To begin, please select an option below. You will be asked for your hospital's unique ID.")
        
        st.button("Login to an Existing Account", on_click=set_page_login, width='stretch', type="primary")
        st.button("Create a New Account", on_click=set_page_register, width='stretch')

def show_login_form(service):
    """Displays the login form, requiring a role selection."""
    st.button("← Back to Welcome", on_click=set_page_welcome)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>Account Login</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            hospital_id = st.text_input("Hospital ID", help="Enter the unique ID for your hospital.")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Login as", ["patient", "clinician", "admin"])
            submitted = st.form_submit_button("Login", width='stretch')

            if submitted:
                if not hospital_id or not username or not password:
                    st.error("Hospital ID, Username, and Password are required.")
                else:
                    user = service.login(username, password, role, hospital_id)
                    if user == 'pending':
                        st.warning("Your account is pending approval by an administrator.")
                    elif user:
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
        st.markdown("<h2 style='text-align: center;'>Create a New Account</h2>", unsafe_allow_html=True)
        with st.form("register_form"):
            role = st.selectbox("Select your role", ["patient", "clinician", "admin"])
            hospital_id = st.text_input("Hospital ID", help="If your hospital is new, this will create it. If it exists, you will join it.")
            username = st.text_input("Choose a Username")
            password = st.text_input("Choose a Password", type="password")
            submitted = st.form_submit_button("Register", width='stretch')

            if submitted:
                if not hospital_id or not username or not password:
                    st.error("All fields are required.")
                else:
                    result = service.register_user(username, password, role, hospital_id)
                    if result == 'pending':
                        st.info("Your account registration is pending approval by an administrator.")
                    elif result:
                        st.success(f"User '{username}' registered for '{hospital_id}'! Please go back to log in.")
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
        page = st.sidebar.radio("Navigation", ["Add Patient Note", "View Patient Notes", "Review AI Feedback"])
        if page == "Add Patient Note":
            _render_add_note_page(service, hospital_id)
        elif page == "View Patient Notes":
            _render_view_notes_page(service, hospital_id)
        elif page == "Review AI Feedback":
            _render_review_feedback_page(service, hospital_id)
    elif user.role == 'patient':
        page = st.sidebar.radio("Navigation", ["View My Notes", "Add My Entry"])
        if page == "View My Notes":
            _render_view_notes_page(service, hospital_id, patient_id=user.username)
        elif page == "Add My Entry":
            _render_add_patient_entry_page(service, hospital_id)
    elif user.role == 'admin':
        page = st.sidebar.radio("Navigation", ["User Management & Export", "Approve New Users"])
        if page == "User Management & Export":
            _render_admin_page(service, hospital_id)
        elif page == "Approve New Users":
            _render_approval_page(service, hospital_id)

def _render_add_note_page(service, hospital_id):
    st.markdown("<h2 style='text-align: center;'>Add a New Patient Note</h2>", unsafe_allow_html=True)
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
        diagnoses = st.text_area("Medical Notes and Diagnoses")
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
    st.markdown("<h2 style='text-align: center;'>Add a New Entry</h2>", unsafe_allow_html=True)
    with st.form("add_patient_entry_form"):
        mood = st.slider("My Mood (0-10)", 0, 10, 5)
        pain = st.slider("My Pain Level (0-10)", 0, 10, 5)
        appetite = st.slider("My Appetite (0-10)", 0, 10, 5)
        notes = st.text_area("How are you feeling today?")
        generate_feedback = st.checkbox("Generate AI Feedback")
        submitted = st.form_submit_button("Save Entry")
        if submitted:
            user = st.session_state.current_user
            note = PatientNote(
                patient_id=user.username, author_id=user.username, mood=mood, pain=pain,
                appetite=appetite, notes=notes, diagnoses="", source="patient", hospital_id=hospital_id
            )
            service.add_note(note, hospital_id)
            if generate_feedback:
                with st.spinner("Generating AI Feedback..."):
                    service.generate_and_store_ai_feedback(note.note_id, hospital_id)
            st.success("Your entry has been saved successfully.")

def _render_view_notes_page(service, hospital_id, patient_id=None):
    user = st.session_state.current_user
    if patient_id:
        st.markdown("<h2 style='text-align: center;'>My Medical Notes & Entries</h2>", unsafe_allow_html=True)
        notes = service.get_notes_for_patient(hospital_id, patient_id)
        if user.role == 'patient':
            notes = [note for note in notes if note.get('source') == 'patient']
    else:
        st.markdown("<h2 style='text-align: center;'>View All Patient Notes & Entries</h2>", unsafe_allow_html=True)
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
        # Use .get() for sorting to prevent crash if timestamp is missing
        for note in sorted(notes, key=lambda x: x.get('timestamp', ''), reverse=True):
            source = note.get("source", "clinician")
            timestamp_str = note.get('timestamp')
            timestamp = datetime.datetime.fromisoformat(timestamp_str).strftime('%Y-%m-%d %H:%M:%S') if timestamp_str else "Unknown Date"
            author = note.get('author_id', 'Unknown')

            if source == "patient":
                expander_title = f"Patient Entry from {timestamp}"
                if user.role != 'patient':
                    st.info(f"Entry from Patient: {author}")
            else:
                expander_title = f"Clinical Note from {timestamp} (by {author})"
                st.warning(f"Note from Clinician: {author}")
            
            with st.expander(expander_title):
                # Use .get() with default values for all note fields to prevent crashes
                st.metric("Mood", f"{note.get('mood', 'N/A')}/10")
                st.metric("Pain", f"{note.get('pain', 'N/A')}/10")
                st.metric("Appetite", f"{note.get('appetite', 'N/A')}/10")
                st.write("**Patient wrote:**" if source == "patient" else "**Narrative Notes:**")
                st.write(note.get('notes') or "_No notes provided._")
                if source == "clinician":
                    st.write("**Diagnoses/Medical Notes:**")
                    st.write(note.get('diagnoses') or "_No diagnoses provided._")
                
                ai_feedback = note.get('ai_feedback')
                if ai_feedback:
                    if ai_feedback.get('status') == 'approved':
                        st.divider()
                        st.markdown("**AI Generated Feedback**")
                        st.success(ai_feedback.get('text'))
                    elif ai_feedback.get('status') == 'pending':
                        st.divider()
                        st.info("Awaiting AI feedback approval from clinician to ensure your safety.")

                if user.role == 'patient':
                    if st.button("Delete Note", key=f"delete_{note.get('note_id', 'unknown_id')}"): # Add default for key
                        # Use .get() for robustness when calling service.delete_note
                        service.delete_note(note['note_id'], hospital_id)
                        st.success("Note deleted successfully.")
                        st.rerun()

def _render_admin_page(service, hospital_id):
    st.markdown(f"<h2 style='text-align: center;'>Admin Panel for {hospital_id}</h2>", unsafe_allow_html=True)
    st.subheader("User Management")
    users_dict = service.get_all_users(hospital_id)
    if not users_dict:
        st.info("No users found for this hospital.")
    else:
        user_data_list = [
            # Use .get() for robustness in case 'username', 'role', or 'status' keys are missing
            {"Username": user_data.get('username'), "Role": user_data.get('role'), "Status": user_data.get('status', 'approved')}
            for user_data in users_dict.values()
        ]
        df = pd.DataFrame(user_data_list)
        df.index = pd.RangeIndex(start=1, stop=len(df) + 1, step=1)
        st.dataframe(df, width=None, use_container_width=True)
    
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
                # Use .get() for robustness in case 'username' or 'role' keys are missing
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
    if not notes_list:
        st.info("There are no notes to export in this report.")
    else:
        report_content = [f"CareLog Notes Report - Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", "="*80 + "\n"]
        # Use .get() for sorting to prevent crash if timestamp is missing
        for note in sorted(notes_list, key=lambda x: x.get('timestamp', '')):
            timestamp_str = note.get('timestamp')
            timestamp = datetime.datetime.fromisoformat(timestamp_str).strftime('%Y-%m-%d %H:%M:%S') if timestamp_str else "Unknown Date"
            report_content.extend([
                f"Timestamp: {timestamp}",
                f"Patient ID: {note.get('patient_id', 'N/A')}",
                f"Author ID: {note.get('author_id', 'N/A')}",
                f"Entry Source: {note.get('source', 'clinician').capitalize()}",
                f"Mood: {note.get('mood', 'N/A')}/10 | Pain: {note.get('pain', 'N/A')}/10 | Appetite: {note.get('appetite', 'N/A')}/10",
                "\nPatient Wrote:\n" + "-"*15 if note.get('source') == 'patient' else "\nNarrative Notes:\n" + "-"*18,
                note.get('notes', 'N/A') or "N/A"
            ])
            if note.get('source', 'clinician') == 'clinician':
                report_content.extend(["\nDiagnoses/Medical Notes:\n" + "-"*25, note.get('diagnoses', 'N/A') or "N/A"])
            
            ai_feedback = note.get('ai_feedback')
            if ai_feedback and ai_feedback.get('status') == 'approved':
                report_content.extend([
                    "\n\nAI Generated Feedback:\n" + "-"*22, # Use .get() for robustness
                    ai_feedback.get('text', 'N/A')
                ])
            report_content.append("\n" + "="*80 + "\n")
        
        final_report = "\n".join(report_content)
        st.download_button(
            label="Download Notes Report (.txt)", data=final_report.encode('utf-8'),
            file_name=f"carelog_report_notes_{datetime.date.today()}.txt", mime="text/plain"
        )

def _render_approval_page(service, hospital_id):
    st.markdown("<h2 style='text-align: center;'>Approve New Users</h2>", unsafe_allow_html=True)
    
    st.subheader("Pending Administrators")
    pending_admins = service.get_pending_users(hospital_id, 'admin')
    if not pending_admins:
        st.info("No new admin accounts are pending approval.")
    else:
        for admin in pending_admins:
            st.text(f"Username: {admin['username']}")
            # Use .get() for robustness in case 'username' key is missing
            if st.button(f"Approve {admin.get('username')}", key=f"approve_admin_{admin.get('username', 'unknown_admin')}"):
                service.approve_user(admin['username'], 'admin', hospital_id)
                st.success(f"User {admin['username']} has been approved.")
                st.rerun()

    st.divider() 
    
    st.subheader("Pending Clinicians")
    pending_clinicians = service.get_pending_users(hospital_id, 'clinician')
    if not pending_clinicians:
        st.info("No new clinician accounts are pending approval.")
    else:
        for clinician in pending_clinicians:
            st.text(f"Username: {clinician['username']}")
            # Use .get() for robustness in case 'username' key is missing
            if st.button(f"Approve {clinician.get('username')}", key=f"approve_clinician_{clinician.get('username', 'unknown_clinician')}"):
                service.approve_user(clinician['username'], 'clinician', hospital_id)
                st.success(f"User {clinician['username']} has been approved.")
                st.rerun()

def _render_review_feedback_page(service, hospital_id):
    st.markdown("<h2 style='text-align: center;'>Review AI Feedback</h2>", unsafe_allow_html=True)
    pending_feedback = service.get_pending_feedback(hospital_id)

    if not pending_feedback:
        st.info("No AI feedback to review.")
        return

    for note in pending_feedback:
        # Use .get() for robustness in case 'patient_id', 'timestamp', or 'notes' keys are missing
        patient_id_display = note.get('patient_id', 'Unknown Patient')
        timestamp_str = note.get('timestamp')
        timestamp_display = datetime.datetime.fromisoformat(timestamp_str).strftime('%Y-%m-%d %H:%M:%S') if timestamp_str else "Unknown Date"
        notes_display = note.get('notes', '_No notes provided._')

        st.subheader(f"Feedback for {patient_id_display}'s note from {timestamp_display}")
        st.write("**Patient's Note:**")
        st.write(notes_display)
        
        # Allow clinician to edit the AI feedback in a text area
        edited_feedback = st.text_area(
            "**AI Generated Feedback (Edit if necessary):**",
            value=note.get('ai_feedback', {}).get('text', 'N/A'),
            height=200,
            key=f"edit_feedback_{note.get('note_id', 'unknown_id')}"
        )

        # Use columns for approve/reject buttons for a cleaner layout
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve Feedback", key=f"approve_{note.get('note_id', 'unknown_id')}", width='stretch', type="primary"):
                # Use .get() for robustness when calling service.approve_ai_feedback
                service.approve_ai_feedback(note.get('note_id'), hospital_id, edited_feedback)
                st.success("Feedback approved!")
                st.rerun()
        with col2:
            if st.button("Reject Feedback", key=f"reject_{note.get('note_id', 'unknown_id')}", width='stretch'):
                service.reject_ai_feedback(note.get('note_id'), hospital_id)
                st.success("Feedback has been rejected and removed.")
                st.rerun()