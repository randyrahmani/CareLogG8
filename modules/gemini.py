import streamlit as st
import google.generativeai as genai

# Configure the Gemini API key
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Create the model
model = genai.GenerativeModel('gemma-3-27b-it')

def generate_feedback(patient_notes, mood, pain, appetite):
    """Generates feedback for a patient based on their notes."""

    prompt = f"""
    You are an AI in a hospital that gives feedback to patients based on their notes. 
    The patient reported the following:
    - Mood: {mood}/10
    - Pain: {pain}/10
    - Appetite: {appetite}/10

    Patient Notes:
    {patient_notes}

    Provide useful feedbacks and things that the patients can do to make themselves feel better. Be kind and encouraging. 
    Do not assume things. Provide one paragraph of around 200 words. Only print the paragraph and nothing else. 


    Feedback:
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating feedback: {e}")
        return None
