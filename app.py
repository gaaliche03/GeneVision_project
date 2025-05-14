import streamlit as st
from components.authentication import authentication
from components.dashboard import dashboard

# Page configuration
st.set_page_config(
    page_title="GeneVision",
    page_icon="./assets/logo.ico",
    layout="centered"
)

if __name__ == "__main__":
    # Initialize session variables for the stepper if needed
    if 'current_step' not in st.session_state:
        st.session_state['current_step'] = 0
    if 'steps_completed' not in st.session_state:
        st.session_state['steps_completed'] = []
    
    # Check login status and show appropriate page
    if st.session_state.get('logged_in', False):
        dashboard()
    else:
        authentication()