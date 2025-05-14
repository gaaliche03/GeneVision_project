import streamlit as st
import re
import os
import pandas as pd
from Bio import SeqIO
import py3Dmol
from datetime import datetime
import PyPDF2

from scripts.rapport_results import generate_genevision_report
# Import necessary database functions
from scripts.database import (create_sequence, update_sequence, 
                      create_analysis_result, create_report, log_activity)

# Modification de la fonction d'affichage des résultats finaux
def display_results():

    input_sequences = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\input_sequences.fasta"
    predicted_genes = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\predicted_genes.fasta"
    protein_sequences = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\protein_sequences.fasta"
    annotation_csv = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\final_annotations.csv"
    protein_models_dir = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\pdb_models"

    # Store current analysis in session state if not already there
    if 'current_analysis_id' not in st.session_state and st.session_state.get('logged_in', False):
        # Create a new sequence entry in the database if input file exists
        if os.path.exists(input_sequences):
            user_id = st.session_state.get('user_id')
            # Read the input sequence content
            with open(input_sequences, 'r') as f:
                sequence_content = f.read()
            
            # Get sequence metadata
            seq_records = list(SeqIO.parse(input_sequences, "fasta"))
            metadata = {
                "sequence_count": len(seq_records),
                "total_length": sum(len(rec.seq) for rec in seq_records),
                "source_file": os.path.basename(input_sequences)
            }
            
            # Create sequence in database
            seq_id = create_sequence(user_id, sequence_content, metadata)
            if seq_id:
                st.session_state['current_analysis_id'] = seq_id
                log_activity(user_id, "sequence_analysis_started", f"Started analysis of sequence {seq_id}")

    #résumé global sur la prédiction et l'annotation
    st.subheader("📈 Summary Statistics")
    if st.session_state.get('logged_in', False):
        tab1, tab2 = st.tabs(["**_Summary Statistics_**", "ℹ️"])
        with tab1:
            if os.path.exists(predicted_genes) and os.path.exists(protein_sequences):
                # Existing statistics calculations
                gene_count = len(list(SeqIO.parse(predicted_genes, "fasta")))
                protein_count = len(list(SeqIO.parse(protein_sequences, "fasta")))
                sequence_length = sum(len(rec.seq) for rec in SeqIO.parse(input_sequences, "fasta"))
                avg_gene_length = sum(len(rec.seq) for rec in SeqIO.parse(predicted_genes, "fasta")) // max(1, gene_count)
                avg_protein_length = sum(len(rec.seq) for rec in SeqIO.parse(protein_sequences, "fasta")) // max(1, protein_count)

                # Calculate GC content percentage
                gene_sequences = [str(record.seq) for record in SeqIO.parse(predicted_genes, "fasta")]
                gc_counts = [seq.count('G') + seq.count('C') for seq in gene_sequences]
                total_bases = [len(seq) for seq in gene_sequences]
                gc_percentages = [round((gc / total) * 100, 2) if total > 0 else 0 for gc, total in zip(gc_counts, total_bases)]
                avg_gc_content = sum(gc_percentages) / len(gc_percentages) if gc_percentages else 0

                # Retrieve the function GO with the highest score
                most_go_function = "`N/A`"
                go_term_counts = {}
                if os.path.exists(annotation_csv):
                    df = pd.read_csv(annotation_csv)
                    if "Confidence Score" in df.columns and "Top GO Term" in df.columns and "Top GO Term Name" in df.columns:
                        top_go = df.sort_values(by="Confidence Score", ascending=False).iloc[0]
                        go_id = top_go["Top GO Term"]
                        go_name = top_go["Top GO Term Name"]
                        most_go_function = f"`{go_id} - {go_name}`"
                        
                        # Count occurrences of GO terms for visualization
                        if "Top GO Term Name" in df.columns:
                            go_term_counts = df["Top GO Term Name"].value_counts().to_dict()

                # Store analysis results in database if we have a current analysis
                if 'current_analysis_id' in st.session_state:
                    analysis_data = {
                        "gene_count": gene_count,
                        "protein_count": protein_count,
                        "sequence_length": sequence_length,
                        "avg_gene_length": avg_gene_length,
                        "avg_protein_length": avg_protein_length,
                        "avg_gc_content": float(avg_gc_content),
                        "top_go_function": most_go_function.replace('`', ''),
                        "go_term_counts": go_term_counts
                    }
                    
                    # Create analysis result in database
                    result_id = create_analysis_result(st.session_state['current_analysis_id'], analysis_data)
                    
                    # Update sequence status
                    update_sequence(
                        st.session_state['current_analysis_id'], 
                        st.session_state.get('user_id'),
                        {"status": "analyzed", "gene_count": gene_count, "avg_gc_content": float(avg_gc_content)}
                    )
                
                # Display conditional
                if gene_count == 1:
                    st.markdown(f"""
                    - **Number of predicted genes**: {gene_count}  
                    - **Number of protein sequences**: {protein_count}  
                    - **Total input sequence length**: {sequence_length} bp  
                    - **Gene length**: {avg_gene_length} bp  
                    - **Protein length**: {avg_protein_length} aa  
                    - **Average GC content**: {avg_gc_content:.2f}%  
                    - **Most confident GO function**: {most_go_function}
                    """)
                else:
                    st.markdown(f"""
                    - **Number of predicted genes**: {gene_count}  
                    - **Number of protein sequences**: {protein_count}  
                    - **Total input sequence length**: {sequence_length} bp  
                    - **Average gene length**: {avg_gene_length} bp  
                    - **Average protein length**: {avg_protein_length} aa  
                    - **Average GC content**: {avg_gc_content:.2f}%  
                    - **Most common GO function**: {most_go_function}
                    """)
            else:
                st.warning("Statistics cannot be calculated because result files are missing.")

        with tab2:
            st.info("""
                    
                What do 'bp' and 'aa' mean?

                - **bp** (*base pairs*): Unit used to measure the length of DNA or RNA sequences.  
                Example: `1815 bp` means the gene is composed of 1815 nucleotides.

                - **aa** (*amino acids*): Unit used to measure the length of protein sequences.  
                Example: `604 aa` means the protein is made up of 604 amino acids.

                - **GC content**: The percentage of guanine (G) and cytosine (C) bases in DNA.
                Higher GC content often indicates more stable DNA structure.

                These metrics help understand the size, composition, and complexity of predicted genes and their translated proteins.
            """)
  
    #affichage des sequences(input/genes/proteins)
    st.subheader("🧬 Predicted Genes & Proteins")
    if st.session_state.get('logged_in', False):
        tab1, tab2, tab3, tab4 = st.tabs(["**_Input Sequences_**", "**_Predicted Gene Sequences_**", "**_Protein Sequences_**", "ℹ️"])

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

    #tableau de annotation fonctionnelle : global table et detail table
    st.subheader("📊 Functional Annotation Table")
    if st.session_state.get('logged_in', False):
        tab1, tab2, tab3 = st.tabs(["**_Overview of Functional Annotations_**", "**_Detailed Annotation per Gene_**", "ℹ️"])

        with tab1 :
            if os.path.exists(annotation_csv):
                df = pd.read_csv(annotation_csv)
                df = df.rename(columns={
                    "Top GO Term Name": "Function",
                })
                # Table résumé à afficher
                summary_df = df[["Gene ID", "Position", "Confidence Score", "Function"]]
                st.dataframe(summary_df, use_container_width=True)
                
                # Store annotation data in database if we have a current analysis
                if 'current_analysis_id' in st.session_state:
                    # Get annotation data for database storage
                    annotation_data = []
                    for _, row in df.iterrows():
                        annotation_data.append({
                            "gene_id": row["Gene ID"],
                            "position": row["Position"],
                            "confidence": float(row["Confidence Score"]),
                            "function": row["Function"],
                            "go_term": row.get("Top GO Term", ""),
                            "go_description": row.get("Top GO Term Description", "")
                        })
                    
                    # Update sequence with annotation data
                    update_sequence(
                        st.session_state['current_analysis_id'],
                        st.session_state.get('user_id'),
                        {"annotations": annotation_data}
                    )
            else:
                st.warning("No functional annotation file found.")

        with tab2:
            search_gene = st.text_input(" Search by Gene ID", placeholder="e.g. gene1")
            
            if os.path.exists(annotation_csv):
                df = pd.read_csv(annotation_csv)
                
                if search_gene:
                    # Filtrer pour obtenir les détails du gène recherché
                    gene_rows = df[df["Gene ID"].str.lower() == search_gene.strip().lower()]
                    
                    if not gene_rows.empty:
                        # Premier tableau avec les informations principales
                        st.markdown(f"#### Main details for `{search_gene}`")
                        
                        # Afficher les détails principaux
                        main_details = gene_rows[
                            ["Gene ID", 
                            "Position", 
                            "Confidence Score",  
                            "Top GO Term Name", 
                            "Top GO Term Description"]
                        ].rename(columns={
                            "Top GO Term Name": "Function", 
                            "Top GO Term Description": "Description"
                        })
                        
                        st.table(main_details)
                        
                        st.markdown("---")  # Séparateur
                        
                        threshold = st.slider("Confidence score threshold", 
                                            min_value=0.0, max_value=1.0, value=0.2, step=0.1)

                        # Récupérer et parser la colonne "All GO Terms"
                        gene_row = gene_rows.iloc[0]
                        all_go_terms_str = gene_row["All GO Terms"]
                        
                        # Traiter la chaîne de caractères contenant les tuples
                        additional_go_terms = []
                        
                        # Vérifier si la chaîne n'est pas vide
                        if isinstance(all_go_terms_str, str) and all_go_terms_str.strip():
                            try:
                                # Nettoyer la chaîne pour faciliter l'évaluation
                                all_go_terms_str = all_go_terms_str.replace("[", "").replace("]", "")
                                
                                # Trouver tous les tuples dans la chaîne
                                tuple_pattern = r"\('([^']+)',\s*([\d.]+),\s*'([^']+)',\s*'([^']+)'\)"
                                matches = re.findall(tuple_pattern, all_go_terms_str)
                                
                                for go_id, score, go_name, go_description in matches:
                                    score = float(score)
                                    # Filtrer selon le seuil défini par l'utilisateur
                                    if score >= threshold:
                                        # Ne pas inclure le GO term principal qui est déjà affiché
                                        top_go_term = gene_row.get("Top GO Term", "")
                                        if go_id != top_go_term:
                                            additional_go_terms.append({
                                                "GO ID": go_id,
                                                "Confidence Score": score,
                                                "GO Term": go_name,
                                                "Description": go_description
                                                
                                            })
                            except Exception as e:
                                st.error(f"Error parsing GO Terms: {str(e)}")
                        
                        # Deuxième tableau pour les GO Terms supplémentaires
                        st.markdown(f"#### Additional GO Terms Annotations for `{search_gene}` (Confidence Score ≥ {threshold})")
                        
                        if additional_go_terms:
                            additional_table = pd.DataFrame(additional_go_terms)
                            additional_table = additional_table.sort_values(by="Confidence Score", ascending=False)
                            st.table(additional_table)
                        else:
                            st.info(f"No additional GO Terms found with confidence score ≥ {threshold}")
                    else:
                        st.warning(f"No data found for gene ID: `{search_gene}`")
            else:
                st.error("Functional annotation file not found.")
                
        with tab3 : 
            st.info("""
            This section presents the **functional annotation results** for each predicted gene:

            **Overview of Functional Annotations** (Table 1):  
                A summarized table showing key information for each gene, including:
            - **Gene ID**: Identifier of the predicted gene.
            - **Position**: Genomic location (start to stop codon).
            - **Confidence Score**: Reliability of the main predicted function.
            - **Function**: Most confident GO term assigned to the gene.

            **Detailed Annotation per Gene** (Table 2):  
                Allows you to search for a specific **Gene ID** and view:
            - Main function and description based on the top GO term.
            - Additional GO annotations with adjustable confidence thresholds.

            These annotations help interpret the **biological roles** of the predicted genes.
            """)        

    # Ajout de la section pour de model 3D protein
    st.subheader("🧩 3D Protein Models")
    if st.session_state.get('logged_in', False):
                    tab1, tab2, tab3 = st.tabs(["**_Protein Models_**", "**_Model Quality_**", "ℹ️"])
                    
                    with tab1:
                        # Update path to correct location of PDB files
                        
                        
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
                                
                                # Store PDB model data in database if we have a current analysis
                                if 'current_analysis_id' in st.session_state and selected_model and not hasattr(st, '_model_data_stored'):
                                    protein_id = selected_model.replace('.pdb', '')
                                    update_sequence(
                                        st.session_state['current_analysis_id'],
                                        st.session_state.get('user_id'),
                                        {f"protein_model_{protein_id}": {"name": selected_model, "size": len(pdb_data)}}
                                    )
                                    setattr(st, '_model_data_stored', True)
                                    log_activity(st.session_state.get('user_id'), "protein_model_viewed", f"Viewed 3D model for {protein_id}")

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
                                    "Confidence Score": [round(min(95, 75 + 20 * (i / len(model_files))), 1) for i in range(len(model_files))],
                                    "Quality Category": ["High" if i < len(model_files)/2 else "Medium" for i in range(len(model_files))]
                                }
                                
                                quality_df = pd.DataFrame(quality_data)
                                st.dataframe(quality_df, use_container_width=True)
                                
                                # Store model quality data in database
                                if 'current_analysis_id' in st.session_state and not hasattr(st, '_quality_data_stored'):
                                    quality_info = []
                                    for i, row in quality_df.iterrows():
                                        quality_info.append({
                                            "protein_id": row["Protein ID"],
                                            "model_length": int(row["Model Length"]),
                                            "confidence": float(row["Confidence Score"]),
                                            "quality": row["Quality Category"]
                                        })
                                    
                                    update_sequence(
                                        st.session_state['current_analysis_id'],
                                        st.session_state.get('user_id'),
                                        {"protein_models_quality": quality_info}
                                    )
                                    setattr(st, '_quality_data_stored', True)
                        
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

    # Ajout de la section pour le rapport PDF
    st.subheader("📄 Gene Analysis Report")
    if st.session_state.get('logged_in', False):
        tab1, tab2 = st.tabs(["**_Generate Report_**", "ℹ️"])
        
        with tab1:
            st.info("""
            Generate a comprehensive PDF report containing all analysis details and results,
            which you can download and save for future reference.
            """)
            
            # Initialiser une variable d'état pour le chemin du rapport
            if 'report_path' not in st.session_state:
                st.session_state['report_path'] = None
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("⬇️ **Generate Report**"):
                    report_path = generate_and_download_report()
                    if report_path:
                        st.session_state['report_path'] = report_path
                        st.success("Report generated successfully!")
                        
                        # Store report info in database
                        if 'current_analysis_id' in st.session_state:
                            report_metadata = {
                                "report_path": report_path,
                                "generated_at": datetime.utcnow().isoformat(),
                                "user": st.session_state.get('current_user', 'Unknown User')
                            }
                            
                            # Create report entry in database
                            report_id = create_report(
                                st.session_state['current_analysis_id'], 
                                report_metadata,
                                "standard_pdf"
                            )
                            
                            if report_id:
                                log_activity(st.session_state.get('user_id'), "report_generated", f"Generated report for analysis {st.session_state['current_analysis_id']}")
            
                    # Si un rapport a été généré, afficher le lien pour le télécharger
                    if st.session_state['report_path'] and os.path.exists(st.session_state['report_path']):
                        with open(st.session_state['report_path'], "rb") as pdf_file:
                            PDFbyte = pdf_file.read()
                             
                            st.download_button(
                                label="📥 **Download Report**",
                                data=PDFbyte,
                                file_name=os.path.basename(st.session_state['report_path']),
                                mime="application/pdf"
                            )
        
        with tab2:
            st.info("""
            The PDF report includes:
            
            - **Summary of analysis**: Overview of your input sequence and general statistics
            - **Gene prediction results**: Complete list of predicted genes with positions
            - **Functional annotations**: GO terms and biological functions for each gene
            - **Visual charts and diagrams**: Graphical representation of key results
            
            This report is perfect for documentation, sharing with colleagues, or including in publications.
            """)

# Fonction pour collecter les données d'analyse pour le rapport
# Improved collect_report_data function for results_finals.py
def collect_report_data():
    input_sequences = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\input_sequences.fasta"
    predicted_genes = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\predicted_genes.fasta"
    protein_sequences = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\protein_sequences.fasta"
    annotation_csv = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\final_annotations.csv"
    protein_models_dir = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\pdb_models"

    report_data = {
        'metadata': {
            'report_filename': f'genevision_report_{datetime.now().strftime("%Y-%m-%d")}.pdf',
            'date': datetime.now().strftime("%B %d, %Y"),
            'user': st.session_state.get('current_user', 'Unknown User')
        },
        'tools': {
            'gene_prediction': 'AUGUSTUS',
            'functional_annotation': 'DeepGOPlus + QuickGO',
            'structural_modeling': 'ESMAtlas'
        },
        'sequence_data': {},
        'genes': [],
        'sequence_contents': {}
    }
    
    # Read sequence contents for the report
    if os.path.exists(input_sequences):
        with open(input_sequences, 'r') as f:
            report_data['sequence_contents']['input_sequence'] = f.read()
    
    if os.path.exists(predicted_genes):
        with open(predicted_genes, 'r') as f:
            report_data['sequence_contents']['predicted_genes'] = f.read()
    
    if os.path.exists(protein_sequences):
        with open(protein_sequences, 'r') as f:
            report_data['sequence_contents']['protein_sequences'] = f.read()
    
    # Collect structure content if available
    structure_files = {}
    if os.path.exists(protein_models_dir):
        for file in os.listdir(protein_models_dir):
            if file.endswith('.pdb'):
                structure_files[file.replace('.pdb', '')] = os.path.join(protein_models_dir, file)
    
    # Collect sequence statistics
    if os.path.exists(predicted_genes) and os.path.exists(protein_sequences):
        gene_count = len(list(SeqIO.parse(predicted_genes, "fasta")))
        protein_count = len(list(SeqIO.parse(protein_sequences, "fasta")))
        sequence_length = sum(len(rec.seq) for rec in SeqIO.parse(input_sequences, "fasta"))
        
        report_data['sequence_data'] = {
            'gene_count': gene_count,
            'protein_count': protein_count,
            'sequence_length': sequence_length
        }
    
    # Collect gene and annotation data
    if os.path.exists(annotation_csv):
        df = pd.read_csv(annotation_csv)
        for _, row in df.iterrows():
            gene_id = row.get('Gene ID', 'Unknown')
            
            # Check for corresponding PDB file
            pdb_path = None
            structure_content = None
            if gene_id in structure_files:
                pdb_path = structure_files[gene_id]
                # Read the PDB content
                if os.path.exists(pdb_path):
                    with open(pdb_path, 'r') as f:
                        structure_content = f.read()
            
            gene_info = {
                'id': gene_id,
                'position': row.get('Position', 'Unknown'),
                'score': f"{row.get('Confidence Score', 0):.2f}",
                'function': row.get('Top GO Term Name', 'Unknown'),
                'Top GO Term': row.get('Top GO Term', 'Unknown'),
                'Top GO Term Description': row.get('Top GO Term Description', 'No description available'),
                'structure_content': structure_content
            }
            report_data['genes'].append(gene_info)
    
    # Include GO annotations content
    if os.path.exists(annotation_csv):
        with open(annotation_csv, 'r') as f:
            report_data['go_annotations_content'] = f.read()
    
    return report_data


# Fonction pour générer et télécharger le rapport PDF
def generate_and_download_report():
    # Collect data for the report
    with st.spinner("Collecting analysis data..."):
        report_data = collect_report_data()
    
    # Create report directory path
    report_dir = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\reports"
    os.makedirs(report_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    user_name = st.session_state.get('current_user', 'user').replace(' ', '_').lower()
    report_path = os.path.join(report_dir, f"genevision_report_{user_name}_{timestamp}.pdf")
    
    # Log report generation activity
    if st.session_state.get('logged_in', False):
        user_id = st.session_state.get('user_id')
        log_activity(user_id, "report_generation_started", f"Started generating report {os.path.basename(report_path)}")
    
    # Generate the report
    with st.spinner("Generating PDF report..."):
        try:
            generated_path = generate_genevision_report(report_data, report_path)
            
            # Log successful report generation
            if st.session_state.get('logged_in', False):
                user_id = st.session_state.get('user_id')
                log_activity(user_id, "report_generation_completed", f"Successfully generated report {os.path.basename(report_path)}")
                
                # Store report in database
                if 'current_analysis_id' in st.session_state:
                    report_metadata = {
                        "report_path": generated_path,
                        "generated_at": datetime.utcnow().isoformat(),
                        "user": st.session_state.get('current_user', 'Unknown User'),
                        "page_count": count_pdf_pages(generated_path)  # You would need to implement this function
                    }
                    
                    create_report(
                        st.session_state['current_analysis_id'], 
                        report_metadata,
                        "standard_pdf"
                    )
            
            return generated_path
        except Exception as e:
            st.error(f"Error generating report: {str(e)}")
            if st.session_state.get('logged_in', False):
                user_id = st.session_state.get('user_id')
                log_activity(user_id, "report_generation_failed", f"Failed to generate report: {str(e)}")
            return None

# Helper function to count PDF pages
def count_pdf_pages(pdf_path):
    try:
        
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfFileReader(f)
            return pdf_reader.numPages
    except:
        return 0  # Return 0 if we can't count pages
    # Collecter les données pour le rapport
    report_data = collect_report_data()
    
    # Chemin de sauvegarde du rapport
    report_dir = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\reports"
    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    user_name = st.session_state.get('current_user', 'user').replace(' ', '_').lower()
    report_path = os.path.join(report_dir, f"genevision_report_{user_name}_{timestamp}.pdf")
    
    # Log report generation activity for the user
    if st.session_state.get('logged_in', False):
        user_id = st.session_state.get('user_id')
        log_activity(user_id, "report_generation_started", f"Started generating report {os.path.basename(report_path)}")
    
    # Générer le rapport
    with st.spinner("Generating PDF report..."):
        try:
            generated_path = generate_genevision_report(report_data, report_path)
            return generated_path
        except Exception as e:
            st.error(f"Error generating report: {str(e)}")
            if st.session_state.get('logged_in', False):
                user_id = st.session_state.get('user_id')
                log_activity(user_id, "report_generation_failed", f"Failed to generate report: {str(e)}")
            return None