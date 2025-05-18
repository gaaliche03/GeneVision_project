import streamlit as st
import os
from PIL import Image
from datetime import datetime
import base64
import io

from streamlit_option_menu import option_menu

from components.authentication import check_auth_cookie, clear_auth_cookie
from components.results_steps import display_step_results, display_stepper
from scripts.database import (
    get_user_by_id,
    create_sequence,
    update_sequence,
    log_activity
)

from components.history import display_history_page
from components.account_settings import display_profile_page

# Fonction principale du dashboard modifiée avec le stepper
def dashboard():
    # Vérifier si l'utilisateur est authentifié
    if not check_auth_cookie():
        st.session_state['logged_in'] = False
        st.session_state.pop('current_user', None)
        st.session_state['page'] = 'authentication'
        st.experimental_rerun()

    user_id = st.session_state.get('user_id')
    
    if not user_id:
        st.error("User ID not found in session. Please log in again.")
        clear_auth_cookie()
        st.session_state['logged_in'] = False
        st.session_state['page'] = 'authentication'
        st.experimental_rerun()
    
    # Ensure user_id is set in both auth_user_id and user_id for consistency
    st.session_state['user_id'] = user_id
    
    user_data = get_user_by_id(user_id) if user_id else None
    
    if not user_data:
        st.error("User information not found. Please log in again.")
        clear_auth_cookie()
        st.session_state['logged_in'] = False
        st.session_state['page'] = 'authentication'
        st.experimental_rerun()
    
    username = user_data.get('username', 'Unknown User')
    st.session_state['current_user'] = username

    # Sidebar with option_menu
    with st.sidebar:
        selected = option_menu(
            "GeneVision Menu",
            ["Annotate Sequence", "Analysis History", "Account Settings"],
            icons=["file-earmark-plus", "clock-history", "person-gear"],
            menu_icon="list",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#ff4e4c", "font-size": "16px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "#d3effb",
                },
                "nav-link-selected": {"background-color": "#62acef"},
            }
        )
        
        # Based on the selected option, set the page in session state
        if selected != st.session_state.get('dashboard_page'):
            st.session_state['dashboard_page'] = selected
            # Reset current step if we're not in the sequence entry page
            if selected != "Annotate Sequence":
                st.session_state['current_step'] = 0
            st.experimental_rerun()
        

    # Main content based on selected page
    selected_page = st.session_state.get('dashboard_page', selected)
    
    if selected_page == "Annotate Sequence":
        display_sequence_entry(user_id, username)
    elif selected_page == "Analysis History":
        display_history_page()
    elif selected_page == "Account Settings":
        display_profile_page()

    st.markdown("---")
    st.caption("© 2025 GeneVision | All rights reserved.")

    with st.sidebar :
        # Bouton de déconnexion (keep this at the bottom of sidebar)
        st.markdown("---")
        if st.button("↩️ **Logout**",use_container_width=True):
            # Log the logout action
            if user_id:
                log_activity(user_id, "user_logout", "User logged out")
            
            clear_auth_cookie()
            st.session_state['page'] = 'authentication'
            st.session_state['logged_in'] = False
            st.experimental_rerun()

        # Check if user is logged in
        if 'user_id' not in st.session_state or not st.session_state['user_id']:
            return
        
        user_id = st.session_state['user_id']
        user = get_user_by_id(user_id)
        
        if not user:
            return
        
        st.markdown("---")

        # Create a container with a light background for the profile section
        with st.sidebar.container():
            # Add some padding and styling
            st.markdown("""
            <style>
            .profile-container {
                background-color: #f0f2f6;
                border-radius: 10px

            }
            .profile-header {
                font-weight: bold;
                font-size: 16px;
                margin-bottom: 5px;
                color: #1f77b4
            }
            .profile-email {
                font-size: 14px;
                color: #666

            }
            .sidebar-circular-image {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                object-fit: cover;
                border: 2px solid #e6e6e6
            }
            </style>
            <div class="profile-container">
            """, unsafe_allow_html=True)
            
            # Create columns for photo and user info
            col1, col2, col3 = st.columns([1,2,4])
            
            with col2:
                # Display profile photo in circular shape
                if 'profile_photo' in user and user['profile_photo']:
                    try:
                        photo_data = base64.b64decode(user['profile_photo'])
                        image = Image.open(io.BytesIO(photo_data))
                        
                        # Save the image to a bytes buffer
                        buffered = io.BytesIO()
                        image.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        # Display the image with circular CSS
                        st.markdown(f"""
                        <img src="data:image/png;base64,{img_str}" class="sidebar-circular-image">
                        """, unsafe_allow_html=True)
                    except Exception:
                        # Use a better default profile icon with circular shape
                        st.markdown("""
                        <img src="https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png" 
                            class="sidebar-circular-image" alt="Default Profile">
                        """, unsafe_allow_html=True)
                else:
                    # Use a better default profile icon with circular shape
                    st.markdown("""
                    <img src="https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png" 
                        class="sidebar-circular-image" alt="Default Profile">
                    """, unsafe_allow_html=True)
            
            with col3:
                # Display username with better styling
                username = user.get('username', 'User')
                st.markdown(f"<div class='profile-header'>{username}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='profile-email'>{user.get('email', '')}</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)


#Affiche l'interface d'entrée de séquence et gère l'analyse étape par étape
def display_sequence_entry(user_id, username):
    
    
    # Use relative path for image file
    image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'genevision.png')
    image = Image.open(image_path)
    st.image(image, use_column_width=True)
    
    st.markdown(f"""
    <div style="text-align: center; font-size: 18px; margin-top: 10px;">
        <h5><i>Welcome {username}! Get ready to unlock the secrets hidden in your genomic sequences.</i></h5>
    </div>
    """, unsafe_allow_html=True)

    with st.expander('**How to Use GeneVision Application**'):
        st.write(f"""
        This application allows you to predict genes from an unannotated genomic sequence and perform structural annotation of proteins. Here's how to get started:

        1. 📥 **Upload Your DNA Sequence**  
        To begin, click the "Upload" button and select a `.fasta` file containing your DNA sequence. Alternatively, you can paste a sequence directly into the provided text area or choose the sequence example.

        2. 🧬 **Step-by-Step Analysis**  
        After uploading your sequence, you'll be guided through each step of the analysis:
           - **Gene Prediction**: Identify potential genes in your sequence
           - **GO Term Annotation**: Assign biological functions to your genes
           - **Function Extraction**: Extract the most relevant functions
           - **Protein Structure Modeling**: Create 3D models of your proteins
           
        3. ✔️ **Review & Validate Results**  
        At each step, you'll have the opportunity to review the results before moving to the next step. This gives you complete control over the analysis process.

        4. 🎯 **Final Results**  
        When all steps are completed, you'll see a comprehensive report with all your analysis results.
        """, unsafe_allow_html=True)

    # Afficher le stepper
    st.markdown("### Analysis Progress")

    # Initialiser les variables d'état si nécessaire
    if 'current_step' not in st.session_state:
        st.session_state['current_step'] = 0
    
    if 'steps_completed' not in st.session_state:
        st.session_state['steps_completed'] = []
    
    if 'saved_sequence' not in st.session_state:
        st.session_state['saved_sequence'] = False
    
    if 'sequence_id' not in st.session_state:
        st.session_state['sequence_id'] = None
    
    # Chemin de sauvegarde des fichiers - using relative paths
    base_dir = os.path.dirname(os.path.dirname(__file__))
    save_path = os.path.join(base_dir, "data")
    os.makedirs(save_path, exist_ok=True)
    output_fasta = os.path.join(save_path, "input_sequences.fasta")
    
    # Option de réinitialisation
    if st.session_state.get('current_step', 0) >= 1:
        st.sidebar.markdown("---")
        st.sidebar.info("Click the button below to reset and start a new analysis.")
        if st.sidebar.button("🔄 **Reset Input Sequence**", key="reset_btn",use_container_width=True):
            # Supprimer le fichier de séquence d'entrée
            if os.path.exists(output_fasta):
                os.remove(output_fasta)
            
            # Réinitialiser toutes les variables d'état de session
            st.session_state['current_step'] = 0
            st.session_state['steps_completed'] = []
            st.session_state['saved_sequence'] = False
            st.session_state['sequence_id'] = None
            
            # Réinitialiser les résultats finaux
            if 'show_final_results' in st.session_state:
                st.session_state['show_final_results'] = False
            if 'check_final_step' in st.session_state:
                st.session_state['check_final_step'] = False
                
            # Supprimer les fichiers générés
            try:
                output_files = ["predicted_genes.fasta", "protein_sequences.fasta", "final_annotations.csv"]
                for file in output_files:
                    file_path = os.path.join(save_path, file)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            except Exception as e:
                st.warning(f"Error while deleting generated files: {str(e)}")
                
            log_activity(user_id, "sequence_reset", "Reset sequence analysis")
            st.success("Input sequence has been reset. You can start a new analysis.")
            st.experimental_rerun()
    
    # Afficher le stepper

    display_stepper()
    
    # Affichage des résultats de l'étape actuelle et sauvegarde en DB si nécessaire
    current_step = st.session_state['current_step']
    
    # Si nous sommes à l'étape 1 et que la séquence n'a pas été sauvegardée, la sauvegarder en DB
    if current_step == 1 and not st.session_state['saved_sequence'] and 'input_sequence' in st.session_state:
        sequence = st.session_state['input_sequence']
        metadata = {
            "name": st.session_state.get('sequence_name', 'Unnamed Sequence'),
            "length": len(sequence),
            "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Créer la séquence dans la base de données
        seq_id = create_sequence(user_id, sequence, metadata)
        
        if seq_id:
            st.session_state['sequence_id'] = seq_id
            st.session_state['saved_sequence'] = True
            log_activity(user_id, "sequence_create", f"Created new sequence (ID: {seq_id})")
            st.success("Sequence saved to database")
        else:
            st.error("Failed to save sequence to database")
    
    # Mettre à jour le statut de la séquence à chaque étape complétée
    if current_step > 0 and current_step not in st.session_state['steps_completed'] and st.session_state.get('sequence_id'):
        step_statuses = {
            1: "processing",  # Première étape terminée, analyse en cours
            2: "processing",  # Deuxième étape terminée
            3: "processing",  # Troisième étape terminée
            4: "processing",  # Quatrième étape terminée
            5: "completed"    # Analyse complétée
        }
        
        # Mettre à jour le statut dans la base de données
        if current_step in step_statuses:
            update_sequence(
                st.session_state['sequence_id'], 
                user_id, 
                {"status": step_statuses[current_step]}
            )
            log_activity(user_id, f"step_complete_{current_step-1}", f"Completed step {current_step} of analysis")
            
            # Ajouter l'étape aux étapes complétées
            st.session_state['steps_completed'].append(current_step)
    
    # Afficher les résultats de l'étape actuelle
    display_step_results(current_step)
    
    # Boutons de navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if current_step > 0:
            if st.button("⬅️ **Previous Step**"):
                st.session_state['current_step'] -= 1
                st.experimental_rerun()

    with col3:
        max_steps = 5  # Nombre total d'étapes (0 à 5)
        if (st.session_state.get('saved_sequence', False) or current_step > 0) and current_step < max_steps:
            if st.button("**Next Step** ➡️"):
                st.session_state['current_step'] += 1
                st.experimental_rerun()


# Point d'entrée pour l'exécution directe
if __name__ == "__main__":
    dashboard()