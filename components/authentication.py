import streamlit as st
import re
import time
from datetime import datetime, timedelta
from PIL import Image
from scripts.database import verify_user, register_user, reset_user_password

#créer la barre de progression
def simulate_progress(label="..."):
    with st.spinner(label):
        progress_bar = st.progress(0)
        for percent in range(100):
            time.sleep(0.005)  # effet visuel
            progress_bar.progress(percent + 1)
        progress_bar.empty()

#configuration du cookie d'authentification avec user_id MongoDB
def set_auth_cookie(user_id, user_name, expiry_days=30):
    expiry = datetime.now() + timedelta(days=expiry_days)
    st.session_state['auth_expiry'] = expiry.isoformat()
    st.session_state['user_id'] = user_id  # Store MongoDB user_id
    st.session_state['user_name'] = user_name  # Store user's name for display
    st.session_state['logged_in'] = True

#vérification du cookie d'authentification (vide ou non)
def check_auth_cookie():
    if 'auth_expiry' in st.session_state and 'user_id' in st.session_state:
        expiry = datetime.fromisoformat(st.session_state['auth_expiry'])
        if datetime.now() < expiry:
            return True
    return False

#effacer le cookie d'authentification
def clear_auth_cookie():
    if 'auth_expiry' in st.session_state:
        del st.session_state['auth_expiry']
    if 'user_id' in st.session_state:
        del st.session_state['user_id']
    if 'user_name' in st.session_state:
        del st.session_state['user_name']
    st.session_state['logged_in'] = False

#code de la page d'authentification 
def authentication():


    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'show_reset_form' not in st.session_state:
        st.session_state['show_reset_form'] = False

    # If user is already authenticated via cookie
    if check_auth_cookie() and not st.session_state.get('logged_in', False):
        st.session_state['logged_in'] = True
        st.session_state['current_user'] = st.session_state.get('user_name', 'User')

    image = Image.open('./assets/genevision.png')  # Adjusted path
    st.image(image, use_column_width=True)
    st.markdown("#### <i>Please authenticate to continue</i>", unsafe_allow_html=True)

    if not st.session_state.get('logged_in', False):
        """tab1, tab2, tab3 = st.tabs(["**_Login_**", "**_Register_**", "**_Reset Password_**"])"""
        tab1, tab2 = st.tabs(["**_Login_**", "**_Register_**"])
        st.markdown("""
            <style>
                div.stButton { display: flex; justify-content: flex-end; }
            </style>
        """, unsafe_allow_html=True)

        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="Enter your email")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit_login = st.form_submit_button("**Login**")

                if submit_login:
                    # Verify against MongoDB
                    user = verify_user(email, password)
                    if user:
                        # Store MongoDB user_id in session
                        set_auth_cookie(user["_id"], user["username"], 30)
                        st.session_state['current_user'] = user["username"]
                        st.success(f"Login successful! Welcome {user['username']}.")
                        st.session_state['page'] = 'dashboard'
                        st.experimental_rerun()
                    else:
                        st.error("Incorrect email or password.")
                
        with tab2:
            with st.form("signup_form"):
                new_username = st.text_input("Username", placeholder="Enter your username")
                new_email = st.text_input("Email", placeholder="Enter your email")
                new_password = st.text_input("Password", type="password", placeholder="Enter your password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
                col1, col2 = st.columns([1, 1])
                with col1:
                    terms = st.checkbox("I accept the terms of service")
                with col2:
                    submit_signup = st.form_submit_button("**Create Account**")

                if submit_signup:
                    if not new_username or not new_email or not new_password:
                        st.error("All fields are required.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif not terms:
                        st.error("You must accept the terms.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    elif len(re.findall(r"\d", new_password)) < 2:
                        st.error("Password must contain at least 2 digits.")
                    elif not re.search(r"[!@#$%^&*()_\-+=\[\]{};:,.<>?/]", new_password):
                        st.error("Password must include at least 1 special character.")
                    else:
                        simulate_progress("Creating your account...")
                        # Register user directly in MongoDB
                        success, message, user_id = register_user(new_username, new_email, new_password)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                            
        """with tab3: 
        # partie de mdp oublié
            with st.form("'show_reset_form'"):
                reset_email = st.text_input("Email Used During Registration", placeholder="Enter your email")
                new_pass = st.text_input("New Password", type="password", placeholder="Enter your new password")
                confirm_pass = st.text_input("Confirm New Password", type="password", placeholder="Confirm your new password")
                col3, col4 = st.columns([1, 1])
                with col3:
                    terms = st.checkbox("I accept the terms of service")
                with col4:
                    reset_submit = st.form_submit_button("**Reset Password**")

                if reset_submit:
                    if not reset_email or not new_pass or not confirm_pass:
                        st.error("All fields are required.")
                    elif new_pass != confirm_pass:
                        st.error("Passwords do not match.")
                    elif len(new_pass) < 6 or len(re.findall(r"\d", new_pass)) < 2 or not re.search(r"[!@#$%^&*()]", new_pass):
                        st.error("Password must be strong: 6+ chars, 2+ digits, 1+ special character.")
                    else:
                        # Reset password in MongoDB
                        if reset_user_password(reset_email, new_pass):
                            st.success("Password reset successful. You can now log in.")
                        else:
                            st.error("Email not found or password reset failed.")"""

    else:
        st.success(f"Logged in as: {st.session_state['current_user']}")
        if st.button("Logout"):
            clear_auth_cookie()
            st.session_state.pop('current_user', None)
            st.session_state.pop('page', None)
            st.experimental_rerun()
        else:
            st.session_state['page'] = 'dashboard'
            st.experimental_rerun()

    st.markdown("---")
    st.caption("All your data is protected and will never be shared.")
    st.caption("© 2025 GeneVision | All rights reserved.")