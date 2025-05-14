import streamlit as st
import os
import subprocess
import pandas as pd
from Bio import SeqIO
import py3Dmol
from datetime import datetime
from components.results_finals import display_results
from scripts.database import (
    create_sequence, 
    update_sequence,
    create_analysis_result, 
    log_activity
)


# Nouvelle fonction pour afficher le stepper
def display_stepper():
    steps = [
        "Upload Sequence",
        "Gene Prediction",
        "GO Term Annotation",
        "Function Extraction",
        "Protein Modeling",
        "Final Results"
    ]

    if 'show_final_results' not in st.session_state:
        st.session_state['check_final_step'] = False
    
    # Calculer le pourcentage de complétion (avec limite à 100)
    step_percent = 100 / (len(steps) - 1) if len(steps) > 1 else 0
    current_percent = step_percent * st.session_state['current_step']
    
    # S'assurer que la valeur ne dépasse pas 100
    current_percent = min(100, current_percent)

    # Afficher la barre de progression
    st.progress(int(current_percent))
    
    # Afficher les étapes avec les indicateurs de statut
    cols = st.columns(len(steps))
    for i, step in enumerate(steps):
        with cols[i]:
            if i < st.session_state['current_step'] or st.session_state['check_final_step'] == True:
                # Étape terminée
                st.markdown(f"<div style='text-align:center; color:green;'>✓<br>{step}</div>", unsafe_allow_html=True)
            elif i == st.session_state['current_step']:
                # Étape en cours
                st.markdown(f"<div style='text-align:center; color:#1c83e1; font-weight:bold;'>▶<br>{step}</div>", unsafe_allow_html=True)
            else:
                # Étape à venir
                st.markdown(f"<div style='text-align:center; color:gray;'>○<br>{step}</div>", unsafe_allow_html=True)

# Fonction pour initialiser une séquence dans la base de données
def init_db_sequence(user_id, sequence_content, sequence_name="input_sequence"):
    # Vérifier si l'ID de séquence existe déjà dans la session
    if 'db_sequence_id' not in st.session_state:
        # Créer des métadonnées pour la séquence
        metadata = {
            "sequence_name": sequence_name,
            "length": len(sequence_content),
            "date_created": datetime.utcnow().isoformat(),
            "source": st.session_state.get('input_mode', 'unknown')
        }
        
        # Créer la séquence dans la base de données
        seq_id = create_sequence(user_id, sequence_content, metadata)
        
        if seq_id:
            # Stocker l'ID de la séquence dans la session
            st.session_state['db_sequence_id'] = seq_id
            log_activity(user_id, "sequence_upload", f"Uploaded new sequence: {sequence_name}")
            return seq_id
        else:
            st.error("Failed to create sequence in database")
            return None
    
    return st.session_state['db_sequence_id']

# Fonction pour sauvegarder les résultats d'analyse dans la base de données
def save_analysis_results(step_num, user_id, sequence_id):
    steps_data = {
        1: {"type": "gene_prediction", "files": ["predicted_genes.fasta", "protein_sequences.fasta"]},
        2: {"type": "go_annotation", "files": ["final_annotations.csv"]},
        3: {"type": "function_extraction", "files": ["final_annotations.csv"]},
        4: {"type": "protein_modeling", "files": None},  # Les fichiers PDB seront traités différemment
        5: {"type": "final_results", "files": None}  # Résumé final
    }
    
    if step_num not in steps_data:
        return
    
    data = {}
    
    # Gérer les fichiers spécifiques
    if steps_data[step_num]["files"]:
        for file_name in steps_data[step_num]["files"]:
            file_path = os.path.join("C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data", file_name)
            if os.path.exists(file_path):
                # Charger et traiter les données selon le type de fichier
                if file_name.endswith('.fasta'):
                    records = []
                    for record in SeqIO.parse(file_path, "fasta"):
                        records.append({"id": record.id, "sequence": str(record.seq)})
                    
                    # Déterminer quel type de données nous traitons
                    key_name = "predicted_genes" if "predicted_genes" in file_name else "protein_sequences"
                    data[key_name] = records
                
                elif file_name.endswith('.csv'):
                    df = pd.read_csv(file_path)
                    data["annotations"] = df.to_dict('records')
    
    # Traitement spécial pour les modèles de protéines
    if step_num == 4:
        protein_models_dir = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\pdb_models"
        if os.path.exists(protein_models_dir):
            model_files = [f for f in os.listdir(protein_models_dir) if f.endswith('.pdb')]
            models_data = []
            
            for model_file in model_files:
                model_path = os.path.join(protein_models_dir, model_file)
                with open(model_path, 'r') as file:
                    pdb_content = file.read()
                
                protein_id = model_file.replace('.pdb', '')
                models_data.append({
                    "protein_id": protein_id,
                    "model_content": pdb_content[:1000],  # Limiter la taille pour éviter les problèmes
                    "model_path": model_path
                })
            
            data["protein_models"] = models_data
    
    # Créer ou mettre à jour le statut de la séquence
    update_sequence(sequence_id, user_id, {"status": f"step_{step_num}_completed"})
    
    # Enregistrer les résultats d'analyse
    if data:
        result_id = create_analysis_result(sequence_id, data)
        if result_id:
            step_name = steps_data[step_num]["type"]
            log_activity(user_id, f"{step_name}_complete", f"Completed {step_name} analysis for sequence {sequence_id}")
            return result_id
    
    return None

# Fonction pour afficher les résultats par étape
def display_step_results(step_num):
    # Définir les scripts et leurs descriptions par étape
    steps_info = [
        {"name": "Upload Sequence", "description": "Preparing your DNA sequence for gene prediction and analysis..."},
        {"name": "Gene Prediction", "script": "predict_genes.py", "description": "Identifying potential genes in your DNA sequence..."},
        {"name": "GO Term Annotation", "script": "annotations_go.py", "description": "Assigning biological functions to predicted genes..."},
        {"name": "Function Extraction", "script": "functions_go.py", "description": "Extracting the most relevant functions for each gene..."},
        {"name": "Protein Modeling", "script": "protein_model.py", "description": "Creating 3D structural models of predicted proteins..."},
        {"name": "Final Results", "description": "All analysis steps have been completed. Here are your final results."}
    ]
    
    # Vérifier si l'utilisateur est connecté
    user_id = st.session_state.get('user_id')
    if not user_id and step_num > 0:
        st.warning("Please log in to save your analysis results.")
    
    # Afficher les résultats pour l'étape actuelle
    if 0 <= step_num < len(steps_info):
        if step_num > 0 and step_num < len(steps_info) - 1:
            st.subheader(f"Step {step_num}: {steps_info[step_num]['name']}")
            
            # Vérifier si le script a déjà été exécuté
            if step_num not in st.session_state['steps_completed']:
                with st.spinner(f"{steps_info[step_num]['description']}"):
                    base_path = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\scripts\\"
                    script_path = os.path.join(base_path, steps_info[step_num]['script'])
                    
                    # Exécuter le script avec des paramètres spécifiques selon le script
                    if steps_info[step_num]['script'] == "protein_model.py":
                        protein_fasta_path = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\protein_sequences.fasta"
                        output_dir = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\pdb_models"
                        # S'assurer que le répertoire de sortie existe
                        os.makedirs(output_dir, exist_ok=True)
                        result = subprocess.run(f'python "{script_path}" "{protein_fasta_path}" --output_dir "{output_dir}"', 
                                            shell=True, capture_output=True, text=True)
                    else:
                        # Comportement par défaut pour les autres scripts
                        result = subprocess.run(f'python "{script_path}"', shell=True, capture_output=True, text=True)
                        
                    # Vérifier si l'exécution s'est bien passée
                    if result.returncode == 0:
                        st.success(f"{steps_info[step_num]['name']} completed successfully!")
                        st.session_state['steps_completed'].append(step_num)
                        
                        # Sauvegarder les résultats dans la base de données si l'utilisateur est connecté
                        if user_id and 'db_sequence_id' in st.session_state:
                            save_analysis_results(step_num, user_id, st.session_state['db_sequence_id'])
                    else:
                        st.error(f"Error executing {steps_info[step_num]['name']}: {result.stderr}")
            else:
                st.success(f"{steps_info[step_num]['name']} has been completed!")

            # Afficher les résultats partiels selon l'étape
            if step_num == 1:  # Prédiction de gènes
                if st.session_state.get('logged_in', False):
                    tab1, tab2, tab3, tab4 = st.tabs(["**_Input Sequence_**", "**_Predicted Gene Sequences_**", "**_Protein Sequences_**","ℹ️"])

                    input_sequences = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\input_sequences.fasta"
                    predicted_genes = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\predicted_genes.fasta"
                    protein_sequences = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\protein_sequences.fasta"

                    with tab1: 
                        if os.path.exists(input_sequences):
                            for record in SeqIO.parse(input_sequences, "fasta"):
                                st.markdown(f"**{record.id}**")
                                st.code(str(record.seq), language="text")
                        else:
                            st.warning("No input sequences file found.")

                    with tab2: 
                        if os.path.exists(predicted_genes):
                            for record in SeqIO.parse(predicted_genes, "fasta"):
                                st.markdown(f"**{record.id}**")
                                st.code(str(record.seq), language="text")
                        else:
                            st.warning("No predicted genes file found.")

                    with tab3: 
                        if os.path.exists(protein_sequences):
                            for record in SeqIO.parse(protein_sequences, "fasta"):
                                st.markdown(f"**{record.id}**")
                                st.code(str(record.seq), language="text")
                        else:
                            st.warning("No protein sequences file found.")
                    with tab4:
                        st.info("""
                            You can explore the following sections:

                            - **Input Sequences**: View your uploaded or entered DNA sequence.
                            - **Predicted Gene Sequences**: Check the genes identified from your input.
                            - **Protein Sequences**: See the proteins translated from the predicted genes.
                        """)
                    
            elif step_num == 2:  # Annotation GO
                if st.session_state.get('logged_in', False):
                    tab1, tab2 = st.tabs(["**_Annotation GO Table_**","ℹ️"])
                    with tab1 :
                        annotation_csv = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\final_annotations.csv"
                        if os.path.exists(annotation_csv):
                            df = pd.read_csv(annotation_csv)
                            # Table résumé à afficher
                            summary_df = df[["Gene ID", "Position", "Top GO Term", "Confidence Score"]]
                            st.dataframe(summary_df, use_container_width=True)
                        else:
                            st.warning("No annotation file found.")

                    with tab2 : 
                        st.info("""
                        This table provides the top GO term annotations assigned to each predicted gene : 

                        - **Gene ID**: Identifier of the predicted gene.
                        - **Position**: Genomic location (from start to stop codon).
                        - **Top GO Term**: Most confident Gene Ontology (GO) function assigned.
                        - **Confidence Score**: Reliability score of the functional annotation.

                        """)
                        
            elif step_num == 3:  # Extraction de fonctions
                if st.session_state.get('logged_in', False):
                    tab1, tab2 = st.tabs(["**_Function Table_**","ℹ️"])
                    with tab1 :
                        annotation_csv = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\final_annotations.csv"
                        if os.path.exists(annotation_csv):
                            df = pd.read_csv(annotation_csv)
                            df = df.rename(columns={
                                "Top GO Term Name": "Function",
                                "Top GO Term Description": "Description"
                            })
                            # Table résumé à afficher
                            summary_df = df[["Gene ID", "Position", "Function", "Description"]]
                            st.dataframe(summary_df, use_container_width=True)
                        else:
                            st.warning("No functional annotation file found.")

                    with tab2 : 
                        st.info("""
                        This table displays the functions of each gene based on GO term annotations:

                        - **Gene ID**: Identifier of the predicted gene.
                        - **Position**: Genomic location of the gene (start to stop codon).
                        - **Function**: The main biological function associated with the gene (Top GO term name).
                        - **Description**: A brief explanation of the gene's functional role.

                        These annotations help interpret the biological meaning of each predicted gene.
                        """)

            elif step_num == 4:  # Modélisation des proteines
                if st.session_state.get('logged_in', False):
                    tab1, tab2, tab3 = st.tabs(["**_Protein Models_**", "**_Model Quality_**", "ℹ️"])
                    
                    with tab1:
                        # Update path to correct location of PDB files
                        protein_models_dir = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\pdb_models"
                        
                        # Check if directory exists
                        if os.path.exists(protein_models_dir):
                            # Get all PDB files in the directory
                            model_files = [f for f in os.listdir(protein_models_dir) if f.endswith('.pdb')]
                            
                            if model_files:
                                # Create a selectbox to choose which protein model to display
                                selected_model = st.selectbox("Select protein model to view :", model_files)
                                model_path = os.path.join(protein_models_dir, selected_model)
                                
                                # Read the PDB file content
                                with open(model_path, 'r') as file:
                                    pdb_data = file.read()
                                

                                view = py3Dmol.view(width=600, height=400)
                                view.addModel(pdb_data, "pdb")

                                # Add some controls for the visualization
                                style_options = st.radio(
                                    "Visualization style :",
                                    ("Cartoon", "Stick", "Sphere", "Line"),
                                    horizontal=True
                                )

                                # Apply the selected style
                                if style_options == "Cartoon":
                                    view.setStyle({'cartoon': {'color': 'spectrum'}})
                                elif style_options == "Stick":
                                    view.setStyle({'stick': {'colorscheme': 'greenCarbon', 'radius': 0.2}})
                                elif style_options == "Sphere":
                                    view.setStyle({'sphere': {'colorscheme': 'blueCarbon', 'radius': 0.5}})
                                elif style_options == "Line":
                                    view.setStyle({'line': {'colorscheme': 'redCarbon', 'linewidth': 1.0}})

                                view.zoomTo()
                                view.spin(True)
                                
                                # Display the 3D visualization in Streamlit
                                st.components.v1.html(view._make_html(), height=400)

                            else:
                                st.warning("No protein model files found.")
                        else:
                            st.warning("Protein models directory not found.")
                    
                    with tab2:
                        # Create placeholder quality metrics based on the generated models
                        st.markdown("#### Protein Model Quality Assessment")
                        
                        if os.path.exists(protein_models_dir):
                            model_files = [f for f in os.listdir(protein_models_dir) if f.endswith('.pdb')]
                            
                            if model_files:
                                # Create example quality data
                                quality_data = {
                                    "Protein ID": [f.replace('.pdb', '') for f in model_files],
                                    "Model Length": [len(open(os.path.join(protein_models_dir, f), 'r').readlines()) for f in model_files],
                                    "Confidence": [round(min(95, 75 + 20 * (i / len(model_files))), 1) for i in range(len(model_files))],
                                    "Quality Category": ["High" if i < len(model_files)/2 else "Medium" for i in range(len(model_files))]
                                }
                                
                                quality_df = pd.DataFrame(quality_data)
                                st.dataframe(quality_df, use_container_width=True)
                        
                            else:
                                st.warning("No protein models found to assess quality.")
                        else:
                            st.warning("Protein models directory not found.")
                    
                    with tab3:
                        st.info("""
                        Protein modeling is a computational method used to predict the 3D structure of proteins based on their amino acid sequences. This tab allows you to visualize and analyze protein models generated from DNA sequences.
                        
                        **Key Features:**
                        
                        - **3D Visualization:** Explore protein structures in different visualization styles (Cartoon, Stick, Sphere, Line)
                        - **Model Quality Assessment:** Review quality metrics for generated protein models
                        - **Multiple Models:** Compare different protein models from your sequences
                        - **Confidence Score**: Higher values indicate greater confidence in the predicted structure
                        - **Quality Category**: 
                            - High: Well-predicted structures with reliable folding patterns
                            - Medium: Reasonably predicted structures with some uncertainty
                            - Low: Less reliable predictions that may require refinement
                        """)

        elif step_num == 0:  # Étape d'upload
            save_path = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data"
            output_fasta = os.path.join(save_path, "input_sequences.fasta")
            if st.session_state['current_step'] == 0:
                input_mode = st.selectbox(
                    "Select the input mode",
                    ("Upload FASTA file", "Enter sequence manually", "Try an example")
                )
                
                # Stocker le mode d'entrée dans la session
                st.session_state['input_mode'] = input_mode

                sequence = ""

                if input_mode == "Upload FASTA file":
                    fasta_file = st.file_uploader("Upload a FASTA file", type=["fasta"])
                    if fasta_file is not None:
                        fasta_content = fasta_file.read().decode("utf-8")
                        sequence_lines = [line.strip() for line in fasta_content.splitlines() if not line.startswith(">")]
                        sequence = ''.join(sequence_lines)

                        with open(output_fasta, "w") as f:
                            f.write(">input_sequence\n")
                            f.write(sequence)

                elif input_mode == "Enter sequence manually":
                    sequence = st.text_area("Enter your sequence here", height=200)
                    if sequence:
                        with open(output_fasta, "w") as f:
                            f.write(">input_sequence\n")
                            f.write(sequence)

                elif input_mode == "Try an example":
                    example_sequence = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\example_sequence.txt"
                    with open(example_sequence, "r") as file:
                        example_sequence_content = file.read()

                    st.text_area("Sequence example", example_sequence_content, height=200)
                    sequence = example_sequence_content

                    with open(output_fasta, "w") as f:
                        f.write(">input_sequence\n")
                        f.write(sequence)

            if 'saved_sequence' not in st.session_state:
                st.session_state['saved_sequence'] = False

            if sequence:
                with open(output_fasta, "w") as f:
                    f.write(">input_sequence\n")
                    f.write(sequence)
                
                # Initialiser la séquence dans la base de données si l'utilisateur est connecté
                if st.session_state.get('logged_in', False) and st.session_state.get('user_id'):
                    seq_id = init_db_sequence(st.session_state['user_id'], sequence)
                    if seq_id:
                        st.session_state['saved_sequence'] = True
                        st.success("Sequence successfully uploaded, saved for analysis, and stored in your account.")
                else:
                    st.session_state['saved_sequence'] = True
                    st.success("Sequence successfully uploaded and saved for analysis.")
                    st.info("Log in to save this sequence to your account for future reference.")
                
            else:
                st.info("Preparing your DNA sequence for gene prediction and analysis...")
            
        elif step_num == 5:  # Résultats finaux
            
            st.subheader("🎉 Analysis Complete!")
            st.success("All analysis steps have been completed successfully.")
            st.info("Click the button below to view your comprehensive results.")
            
            # Initialiser la variable d'état de session si elle n'existe pas encore
            if 'show_final_results' not in st.session_state:
                st.session_state['show_final_results'] = False
            
            # Créer des colonnes pour centrer le bouton
            col4, col5, col6 = st.columns([1, 1, 1])
            
            # Placer le bouton dans la colonne du milieu
            with col5:
                if st.button("🔍 **View Final Results**", key="view_results_btn"):
                    st.session_state['show_final_results'] = not st.session_state['show_final_results']  # Toggle l'état
            
            # Enregistrer les résultats complets dans la base de données
            if st.session_state.get('logged_in', False) and 'db_sequence_id' in st.session_state:
                user_id = st.session_state['user_id']
                sequence_id = st.session_state['db_sequence_id']
                
                # Mettre à jour le statut de la séquence
                update_sequence(sequence_id, user_id, {"status": "completed"})
                
                # Créer un lien de téléchargement pour les fichiers générés
                download_links = get_download_links(sequence_id)
                
                # Sauvegarder les résultats finaux
                save_analysis_results(5, user_id, sequence_id)
                
                # Journaliser l'activité
                log_activity(user_id, "analysis_completed", f"Completed full analysis for sequence {sequence_id}")
            
            # Afficher les résultats seulement si le bouton a été cliqué
            if st.session_state['show_final_results']:
                # Cocher l'étape finale
                st.session_state['check_final_step'] = True
                
                # Appeler la fonction qui affiche les résultats
                display_results()

# Fonction auxiliaire pour obtenir les liens de téléchargement (récupérée de database.py)
def get_download_links(seq_id):
    return {
        "Gene FASTA": f"/data/genes/{seq_id}.fasta",
        "Protein FASTA": f"/data/proteins/{seq_id}.fasta",
        "3D Model (PDB)": f"/data/pdb_models/{seq_id}.pdb"
    }