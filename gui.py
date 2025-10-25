# carelog/gui.py

import streamlit as st
from modules.models import PatientNote
import json
import datetime
import time
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
                    with st.spinner("Logging in..."):
                        time.sleep(1)
                        user = service.login(username, password, role, hospital_id)
                        if user == 'pending':
                            st.warning("Your account creation is successful but pending approval by an administrator.")
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
            full_name = st.text_input("Full Name")
            role = st.selectbox("Select your role", ["patient", "clinician", "admin"])
            hospital_id = st.text_input("Hospital ID", help="If your hospital is new, this will create it. If it exists, you will join it.")
            username = st.text_input("Choose a Username")
            password = st.text_input("Choose a Password", type="password")
            
            st.markdown("---")
            dob = st.date_input("Date of Birth", min_value=datetime.date(1900, 1, 1))
            sex = st.selectbox("Sex", ["Male", "Female", "Intersex", "Prefer not to say"])
            pronouns = st.text_input("Pronouns (e.g., she/her, they/them)")
            bio = st.text_area("Bio (Optional)")

            submitted = st.form_submit_button("Register", width='stretch')

            if submitted:
                if not hospital_id or not username or not password or not full_name:
                    st.error("All fields are required.")
                else:
                    with st.spinner("Registering..."):
                        time.sleep(1)
                        result = service.register_user(username, password, role, hospital_id, full_name, dob.isoformat(), sex, pronouns, bio)
                        if result == 'pending':
                            st.info("Your account registration is successful but pending approval by an administrator.")
                        elif result == 'hospital_not_found':
                            st.error(f"Hospital with ID '{hospital_id}' does not exist. An admin must create it first.")
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
        with st.spinner("Logging out..."):
            time.sleep(1)
            service.logout()
            st.session_state.current_user = None
            st.session_state.hospital_id = None
            st.session_state.auth_page = 'welcome'
            st.rerun()

    st.sidebar.divider()

    # Page router
    if 'page' not in st.session_state:
        st.session_state.page = None

    # Reset page state if role changes or on first load
    if 'current_role' not in st.session_state or st.session_state.current_role != user.role:
        st.session_state.page = None
        st.session_state.current_role = user.role

    if user.role == 'clinician':
        # Display alerts for clinicians
        alerts = service.get_pain_alerts(hospital_id)
        if alerts:
            st.sidebar.subheader(f"🚨 {len(alerts)} High-Priority Alerts")
            for alert in sorted(alerts, key=lambda x: x.get('timestamp', ''), reverse=True):
                timestamp_str = alert.get('timestamp')
                timestamp = datetime.datetime.fromisoformat(timestamp_str).strftime('%H:%M') if timestamp_str else "Time N/A"
                st.sidebar.error(f"**{alert.get('patient_id')}** at {timestamp}")
            if st.sidebar.button("Manage Alerts"):
                with st.spinner("Loading..."):
                    time.sleep(1)
                    st.session_state.page = "Pain Alerts"
                    st.rerun()
            st.sidebar.divider()

        # Navigation
        pages = ["View Patient Notes", "Add Patient Note", "Review AI Feedback", "Pain Alerts", "My Profile"]
        if st.session_state.page not in pages: st.session_state.page = "View Patient Notes"
        page_selection = st.sidebar.radio("Navigation", pages, index=pages.index(st.session_state.page))
        if page_selection != st.session_state.page:
            st.session_state.page = page_selection
            # No spinner for radio buttons as it feels unnatural
            st.rerun()

        # Page rendering
        if st.session_state.page == "Add Patient Note":
            _render_add_note_page(service, hospital_id)
        elif st.session_state.page == "View Patient Notes":
            _render_view_notes_page(service, hospital_id)
        elif st.session_state.page == "Review AI Feedback":
            _render_review_feedback_page(service, hospital_id)
        elif st.session_state.page == "Pain Alerts":
            _render_pain_alerts_page(service, hospital_id)
        elif st.session_state.page == "My Profile":
            _render_profile_page(service, hospital_id)

    elif user.role == 'patient':
        pages = ["Add My Entry", "View My Notes", "My Profile"]
        if st.session_state.page not in pages: st.session_state.page = "Add My Entry"
        page_selection = st.sidebar.radio("Navigation", pages, index=pages.index(st.session_state.page))
        if page_selection != st.session_state.page:
            st.session_state.page = page_selection
            # No spinner for radio buttons
            st.rerun()

        # Page rendering
        if st.session_state.page == "View My Notes":
            _render_view_notes_page(service, hospital_id, patient_id=user.username)
        elif st.session_state.page == "Add My Entry":
            _render_add_patient_entry_page(service, hospital_id)
        elif st.session_state.page == "My Profile":
            _render_profile_page(service, hospital_id)

    elif user.role == 'admin':
        pages = ["User Management & Export", "Approve New Users", "Assign Clinicians", "My Profile"]
        if st.session_state.page not in pages: st.session_state.page = "User Management & Export"
        page_selection = st.sidebar.radio("Navigation", pages, index=pages.index(st.session_state.page))
        if page_selection != st.session_state.page:
            st.session_state.page = page_selection
            # No spinner for radio buttons
            st.rerun()

        # Page rendering
        if st.session_state.page == "User Management & Export":
            _render_admin_page(service, hospital_id)
        elif st.session_state.page == "Approve New Users":
            _render_approval_page(service, hospital_id)
        elif st.session_state.page == "Assign Clinicians":
            _render_assign_clinicians_page(service, hospital_id)
        elif st.session_state.page == "My Profile":
            _render_profile_page(service, hospital_id)

def _render_profile_page(service, hospital_id):
    st.markdown("<h2 style='text-align: center;'>My Profile</h2>", unsafe_allow_html=True)
    user = st.session_state.current_user
    user_data = service.get_all_users(hospital_id).get(f"{user.username}_{user.role}")

    if not user_data:
        st.error("Could not load user profile.")
        return

    with st.form("profile_form"):
        st.write(f"**Username:** {user_data['username']}")
        st.write(f"**Role:** {user_data['role'].capitalize()}")

        full_name = st.text_input("Full Name", value=user_data.get('full_name', ''))
        
        dob_val = user_data.get('dob')
        dob = st.date_input("Date of Birth", value=datetime.date.fromisoformat(dob_val) if dob_val else None, min_value=datetime.date(1900, 1, 1))
        
        sex_options = ["Male", "Female", "Intersex", "Prefer not to say"]
        sex = st.selectbox("Sex", options=sex_options, index=sex_options.index(user_data.get('sex')) if user_data.get('sex') in sex_options else 0)
        
        pronouns = st.text_input("Pronouns", value=user_data.get('pronouns', ''))
        bio = st.text_area("Bio", value=user_data.get('bio', ''))

        st.markdown("---")
        st.subheader("Change Password")
        new_password = st.text_input("New Password (leave blank to keep current password)", type="password")

        submitted = st.form_submit_button("Update Profile")
        if submitted:
            update_details = {
                "full_name": full_name, "dob": dob.isoformat() if dob else None, "sex": sex,
                "pronouns": pronouns, "bio": bio, "new_password": new_password
            }
            with st.spinner("Updating profile..."):
                time.sleep(1)
                if service.update_user_profile(hospital_id, user.username, user.role, update_details):
                    st.success("Profile updated successfully!")
                else:
                    st.error("Failed to update profile.")

def _display_user_profile_details(user_data):
    """Renders a read-only view of a user's profile details."""
    st.write(f"**Username:** {user_data.get('username', 'N/A')}")
    st.write(f"**Role:** {user_data.get('role', 'N/A').capitalize()}")
    st.write(f"**Full Name:** {user_data.get('full_name', 'N/A')}")
    
    dob_val = user_data.get('dob')
    dob_display = datetime.date.fromisoformat(dob_val).strftime('%B %d, %Y') if dob_val else "N/A"
    st.write(f"**Date of Birth:** {dob_display}")
    
    st.write(f"**Sex:** {user_data.get('sex', 'N/A')}")
    st.write(f"**Pronouns:** {user_data.get('pronouns', 'N/A')}")
    st.write(f"**Bio:**")
    st.info(user_data.get('bio') or "_No bio provided._")

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
            with st.spinner("Saving note..."):
                time.sleep(1)
                author_id = st.session_state.current_user.username
                note = PatientNote(
                    patient_id=selected_patient, author_id=author_id, mood=mood, pain=pain,
                    appetite=appetite, notes=notes, diagnoses=diagnoses, source="clinician", hospital_id=hospital_id
                )
                service.add_note(note, hospital_id)
                st.success(f"Note added successfully for patient '{selected_patient}'.")

def _render_add_patient_entry_page(service, hospital_id):
    st.markdown("<h2 style='text-align: center;'>Add a New Entry</h2>", unsafe_allow_html=True)

    # Display a persistent success message after saving an entry
    if st.session_state.get('entry_saved_success'):
        st.success("Your entry has been saved successfully.")
        del st.session_state['entry_saved_success'] # Clear the flag

    form = st.form("add_patient_entry_form")
    with form:
        mood = st.slider("My Mood (0-10)", 0, 10, 5)
        pain = st.slider("My Pain Level (0-10)", 0, 10, 5)
        appetite = st.slider("My Appetite (0-10)", 0, 10, 5)
        notes = st.text_area("How are you feeling today?")
        is_private = st.checkbox("Make this entry private (only you can see it)", value=False)
        submitted = st.form_submit_button("Save Entry")

    if submitted:
        with st.spinner("Saving entry..."):
            time.sleep(1)
            user = st.session_state.current_user
            note = PatientNote(
                patient_id=user.username, author_id=user.username, mood=mood, pain=pain,
                appetite=appetite, notes=notes, diagnoses="", source="patient", hospital_id=hospital_id, is_private=is_private
            )
            service.add_note(note, hospital_id)
            st.session_state.entry_saved_success = True
            st.rerun()

def _render_view_notes_page(service, hospital_id, patient_id=None):
    user = st.session_state.current_user
    if patient_id:
        st.markdown("<h2 style='text-align: center;'>My Medical Notes & Entries</h2>", unsafe_allow_html=True)
        notes = service.get_notes_for_patient(hospital_id, patient_id)
    else:
        st.markdown("<h2 style='text-align: center;'>View All Patient Notes & Entries</h2>", unsafe_allow_html=True)
        patients = service.get_all_patients(hospital_id)
        if not patients:
            st.warning("No patients assigned to you or no patients in this hospital.")
            return
        patient_usernames = [p['username'] for p in patients]
        selected_patient = st.selectbox("Select a patient to view their notes", patient_usernames)
        
        # Add search functionality for clinicians
        if user.role == 'clinician' and selected_patient:
            if st.button("View Patient Profile"):
                # Use session state to toggle profile visibility
                st.session_state.viewing_patient_profile = not st.session_state.get('viewing_patient_profile', False)
            
            if st.session_state.get('viewing_patient_profile'):
                patient_data = service.get_user_by_username(hospital_id, selected_patient, 'patient')
                _display_user_profile_details(patient_data)

        if user.role == 'clinician':
            search_term = st.text_input("Search notes for this patient:")
            if search_term:
                notes = service.search_notes(hospital_id, selected_patient, search_term)
            else:
                notes = service.get_notes_for_patient(hospital_id, selected_patient)
        else:
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

            privacy_icon = "🔒" if note.get('is_private') else ""

            if source == "patient":
                expander_title = f"Patient Entry from {timestamp} {privacy_icon}"
                if user.role != 'patient':
                    st.info(f"Entry from Patient: {author}")
                if note.get('is_private') and user.role != 'patient':
                    st.write("This note is private and cannot be viewed.")
                    continue
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
                
                # Add button to generate AI feedback if it doesn't exist
                elif user.role == 'patient' and note.get('source') == 'patient' and not note.get('is_private'):
                    st.divider()
                    if st.button("Generate AI Feedback", key=f"gen_ai_{note.get('note_id')}"):
                        with st.spinner("Generating AI Feedback..."):
                            # This might take longer, so the spinner is very useful here.
                            success = service.generate_and_store_ai_feedback(note.get('note_id'), hospital_id)
                        if success:
                            st.success("AI feedback is being generated. A clinician will review it shortly.")
                            st.rerun()
                        else:
                            st.error("Could not generate feedback for this note.")


                
                # CRUD buttons
                can_edit_or_delete = (user.role == 'patient' and note.get('source') == 'patient') or \
                                     (user.role == 'clinician' and note.get('source') == 'clinician' and note.get('author_id') == user.username)

                if can_edit_or_delete:
                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Edit Note", key=f"edit_{note.get('note_id', 'unknown_id')}"):
                            st.session_state.editing_note_id = note.get('note_id')
                            st.rerun()
                    with c2:
                        if st.button("Delete Note", key=f"delete_{note.get('note_id', 'unknown_id')}"): # Add default for key
                            # Use .get() for robustness when calling service.delete_note
                            service.delete_note(note['note_id'], hospital_id)
                            st.success("Note deleted successfully.")
                            st.rerun()

                # Note editing form
                if st.session_state.get('editing_note_id') == note.get('note_id'):
                    with st.form(key=f"edit_form_{note.get('note_id')}"):
                        st.subheader("Edit Note")
                        edited_notes = st.text_area("Notes", value=note.get('notes', ''))
                        edited_diagnoses = st.text_area("Diagnoses", value=note.get('diagnoses', '')) if source == "clinician" else None
                        
                        save_changes = st.form_submit_button("Save Changes")
                        if save_changes:
                            updated_data = {'notes': edited_notes}
                            if edited_diagnoses is not None:
                                updated_data['diagnoses'] = edited_diagnoses
                            service.update_note(hospital_id, note.get('note_id'), updated_data)
                            st.session_state.editing_note_id = None
                            st.success("Note updated.")
                            st.rerun()

                elif user.role == 'patient' and note.get('source') != 'patient': # Patient can delete clinician notes
                    if st.button("Delete Note", key=f"delete_{note.get('note_id', 'unknown_id')}", disabled=True):
                        # Use .get() for robustness when calling service.delete_note
                        service.delete_note(note['note_id'], hospital_id)
                        st.success("Note deleted successfully.")
                        st.rerun()

def _render_user_management_entry(user_key, user_data, service, hospital_id):
    """Renders a single user entry in the admin management panel."""
    _display_user_profile_details(user_data)
    
    st.divider()
    c1, c2 = st.columns(2)
    # Edit User Button
    with c1:
        if st.button("Edit User", key=f"edit_{user_key}"):
            st.session_state.editing_user_key = user_key
    # Delete User Button
    with c2:
        current_admin_user = st.session_state.current_user
        # Prevent admin from deleting themselves
        is_self = (current_admin_user.username == user_data.get('username') and current_admin_user.role == user_data.get('role'))
        if st.button("Delete User", key=f"delete_{user_key}", disabled=is_self, type="secondary"):
            if service.delete_user(hospital_id, user_data.get('username'), user_data.get('role')):
                st.success(f"User {user_data.get('username')} deleted successfully.")
                st.rerun()
            else:
                st.error("Failed to delete user.")

    # If this user is being edited, show the edit form
    if st.session_state.get('editing_user_key') == user_key:
        with st.form(key=f"edit_form_{user_key}"):
            st.subheader(f"Editing {user_data.get('username')}")
            full_name = st.text_input("Full Name", value=user_data.get('full_name', ''))
            dob_val = user_data.get('dob')
            dob = st.date_input("Date of Birth", value=datetime.date.fromisoformat(dob_val) if dob_val else None, min_value=datetime.date(1900, 1, 1))
            sex_options = ["Male", "Female", "Intersex", "Prefer not to say"]
            sex = st.selectbox("Sex", options=sex_options, index=sex_options.index(user_data.get('sex')) if user_data.get('sex') in sex_options else 0)
            pronouns = st.text_input("Pronouns", value=user_data.get('pronouns', ''))
            bio = st.text_area("Bio", value=user_data.get('bio', ''))
            
            save_changes = st.form_submit_button("Save Changes")
            if save_changes:
                update_details = {
                    "full_name": full_name, "dob": dob.isoformat() if dob else None, "sex": sex,
                    "pronouns": pronouns, "bio": bio
                }
                if service.update_user_profile(hospital_id, user_data.get('username'), user_data.get('role'), update_details):
                    st.success("Profile updated successfully!")
                    st.session_state.editing_user_key = None
                    st.rerun()
                else:
                    st.error("Failed to update profile.")

def _render_admin_page(service, hospital_id):
    st.markdown(f"<h2 style='text-align: center;'>Admin Panel for {hospital_id}</h2>", unsafe_allow_html=True)
    st.subheader("User Management")
    users_dict = service.get_all_users(hospital_id)

    if not users_dict:
        st.info("No users found for this hospital.")
    else:
        active_users = {k: v for k, v in users_dict.items() if v.get('status') == 'approved'}
        pending_users = {k: v for k, v in users_dict.items() if v.get('status') == 'pending'}

        st.markdown("##### Active Accounts")
        for user_key, user_data in sorted(active_users.items()):
            with st.expander(f"**{user_data.get('username')}** ({user_data.get('role', '').capitalize()})"):
                _render_user_management_entry(user_key, user_data, service, hospital_id)

    
        st.markdown("##### Awaiting Approval")
        for user_key, user_data in sorted(pending_users.items()):
            with st.expander(f"**{user_data.get('username')}** ({user_data.get('role', '').capitalize()})"):
                _render_user_management_entry(user_key, user_data, service, hospital_id)

    st.divider()
    
    # --- Create New User Form for Admins ---
    st.markdown("##### Create a New User")
    with st.expander("Create a New User"):
        with st.form("create_user_form"):
            st.subheader("New User Details")
            new_full_name = st.text_input("Full Name")
            new_role = st.selectbox("Role", ["patient", "clinician", "admin"])
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            
            st.markdown("---")
            new_dob = st.date_input("Date of Birth", min_value=datetime.date(1900, 1, 1), key="new_dob")
            new_sex = st.selectbox("Sex", ["Male", "Female", "Intersex", "Prefer not to say"], key="new_sex")
            new_pronouns = st.text_input("Pronouns (e.g., she/her, they/them)", key="new_pronouns")
            new_bio = st.text_area("Bio (Optional)", key="new_bio")

            create_submitted = st.form_submit_button("Create User")
            if create_submitted:
                if not new_username or not new_password or not new_full_name:
                    st.error("Full Name, Username, and Password are required.")
                else:
                    result = service.register_user(new_username, new_password, new_role, hospital_id, new_full_name, new_dob.isoformat(), new_sex, new_pronouns, new_bio)
                    if result is True or result == 'pending': # Admin-created users might still be pending if they are clinicians/admins
                        st.success(f"User '{new_username}' created successfully!")
                        st.rerun()
                    else:
                        st.error(f"A profile for username '{new_username}' with the role '{new_role}' may already exist.")

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
            # Prepare user data for export, excluding sensitive fields
            export_users_data = []
            for user_key, u_data in users_dict_export.items():
                user_export_data = {
                    'username': u_data.get('username'),
                    'role': u_data.get('role'),
                    'status': u_data.get('status'),
                    'full_name': u_data.get('full_name'),
                    'dob': u_data.get('dob'),
                    'sex': u_data.get('sex'),
                    'pronouns': u_data.get('pronouns'),
                    'bio': u_data.get('bio'),
                    'assigned_clinicians': ', '.join(u_data.get('assigned_clinicians', [])) if u_data.get('role') == 'patient' else ''
                }
                export_users_data.append(user_export_data)
            users_df = pd.DataFrame(export_users_data)
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

def _render_assign_clinicians_page(service, hospital_id):
    st.markdown("<h2 style='text-align: center;'>Assign Clinicians to Patients</h2>", unsafe_allow_html=True)

    patients = service.get_all_patients(hospital_id)
    clinicians = service.get_all_clinicians(hospital_id)

    if not patients or not clinicians:
        st.warning("You need at least one approved patient and one approved clinician to make assignments.")
        return

    patient_usernames = [p['username'] for p in patients]
    selected_patient_username = st.selectbox("Select a Patient", patient_usernames)

    if selected_patient_username:
        patient_user_key = f"{selected_patient_username}_patient"
        all_users = service.get_all_users(hospital_id)
        patient_data = all_users.get(patient_user_key, {})
        assigned_clinicians = patient_data.get('assigned_clinicians', [])

        st.write(f"**Assigned Clinicians for {selected_patient_username}:**")
        if not assigned_clinicians:
            st.info("No clinicians assigned.")
        else:
            for clin in assigned_clinicians:
                col1, col2 = st.columns([4, 1])
                col1.write(clin)
                if col2.button("Unassign", key=f"unassign_{clin}_{selected_patient_username}"):
                    service.unassign_clinician_from_patient(hospital_id, selected_patient_username, clin)
                    st.success(f"Unassigned {clin} from {selected_patient_username}.")
                    st.rerun()

        st.divider()
        st.subheader("Assign a New Clinician")
        available_clinicians = [c['username'] for c in clinicians if c['username'] not in assigned_clinicians]
        if not available_clinicians:
            st.write("All available clinicians are already assigned to this patient.")
        else:
            selected_clinician = st.selectbox("Select Clinician to Assign", available_clinicians)
            if st.button("Assign Clinician"):
                service.assign_clinician_to_patient(hospital_id, selected_patient_username, selected_clinician)
                st.success(f"Assigned {selected_clinician} to {selected_patient_username}.")
                st.rerun()

def _render_pain_alerts_page(service, hospital_id):
    st.markdown("<h2 style='text-align: center;'>Patient Pain Alerts</h2>", unsafe_allow_html=True)
    st.info("This page lists entries where patients have reported a pain level of 10/10.")
    alerts = service.get_pain_alerts(hospital_id)

    if not alerts:
        st.success("No active pain alerts. Great!")
        return

    for alert in sorted(alerts, key=lambda x: x.get('timestamp', ''), reverse=True):
        timestamp_str = alert.get('timestamp')
        timestamp = datetime.datetime.fromisoformat(timestamp_str).strftime('%Y-%m-%d %H:%M') if timestamp_str else "Unknown"
        st.error(f"**Patient:** {alert.get('patient_id')} at **{timestamp}** reported extreme pain (10/10).")
        if st.button("Acknowledge & Dismiss", key=f"dismiss_{alert.get('alert_id')}"):
            service.dismiss_alert(hospital_id, alert.get('alert_id'))
            st.success("Alert dismissed.")
            st.rerun()