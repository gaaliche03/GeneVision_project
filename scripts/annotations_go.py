#dans cette partie on va utiliser model gLLM DeepGOPlus pour attribuer des fonctions biologiques aux gènes prédits
#entrée: fichier FASTA (proteins_sequences.fasta)
#sortie: fichier TSV (deepgoplus_output.tsv) qui contient les tous les annotations fonctionnelles pour chaque gène prédit
#et le fichier CSV (final_annotations.csv) qui contient les informations à afficher à la fin

import subprocess
import pandas as pd
import os
import re

#exécution duu model deepgoplus
def run_deepgoplus(input_fasta, output_file, data_root):
    
    # vérification de l'existance des fichiers
    """if not os.path.exists(input_fasta):
        print(f"**Le fichier d'entrée {input_fasta} n'existe pas")
        return
    
    if not os.path.exists(data_root):
        print(f"**Le répertoire DeepGOPlus {data_root} est introuvable")
        return"""
    
    # commande d'exécution du model deepgoplus
    cmd = [
        "deepgoplus",
        "--data-root", data_root,
        "--in-file", input_fasta,
        "--out-file", output_file
    ]
    
    try:
        print("**Exécution de DeepGOPlus en cours")
        subprocess.run(cmd, check=True)
        print("**DeepGOPlus exécuté avec succès")
        
    except subprocess.CalledProcessError as e:
        print(f"**Erreur d'exécution de DeepGOPlus : {e}")
        exit(1)
        
# fonction pour extraire start_codon et stop_codon de la ligne de description du fichier FASTA
def extract_gene_position(header):
    # Rechercher les informations start_codon et stop_codon dans la ligne de description
    match = re.search(r"\[start_codon=(\d+)\] \[stop_codon=(\d+)\]", header)
    if match:
        start_codon = int(match.group(1))
        stop_codon = int(match.group(2))
        return start_codon, stop_codon
    return None, None

def extract_annotation(deepgoplus_output_tsv, predicted_genes_fasta):
    #analyser le fichier de sortie de deepgoplus et extrait les annotations fonctionnelles.
    
    if not os.path.exists(deepgoplus_output_tsv):
        print(f"**Le fichier {deepgoplus_output_tsv} est introuvable.")
        return pd.DataFrame()
    
    try:
        # charger le fichier de sortie
        df = pd.read_csv(deepgoplus_output_tsv, sep="\t", header=None, dtype=str)
        
        if df.shape[1] < 2:
            print("**Format incorrect, nombre de colonnes insuffisant")
            return pd.DataFrame()
        
        # définir les noms de colonnes
        df.columns = ["Gene ID"] + [f"Annotation_{i}" for i in range(1, df.shape[1])]
        
        # extraction des autres annotations 
        results = []

        # lire le fichier FASTA pour obtenir les positions des gènes
        with open(predicted_genes_fasta, "r") as f:
            fasta_headers = [line.strip() for line in f.readlines() if line.startswith(">")]
        
         # assurer que chaque en-tête FASTA correspond à un identifiant de gène dans les résultats de DeepGOPlus
        for idx, row in df.iterrows():
            gene_id = row["Gene ID"]

            # trouver la position correspondante pour ce gène dans le fichier predicted_genes_fasta 
            fasta_header = next((header for header in fasta_headers if header[1:].startswith(gene_id)), None)
            if fasta_header:
                start_codon, stop_codon = extract_gene_position(fasta_header)
                if start_codon is not None and stop_codon is not None:
                    position = f"{start_codon} - {stop_codon}"
                else:
                    position = "Position inconnue"
            else:
                position = "En-tête FASTA manquant"

            annotations = row[1:].dropna().tolist()
            
            go_terms = []
            
            for annotation in annotations:
                if "|" in annotation:
                    try:
                        term, score = annotation.split("|")
                        score = float(score)
                        go_terms.append((term, score))  # stocker sous forme de tuple (terme, score)
                    except ValueError:
                        print(f"**Erreur de format sur l'annotation {annotation}")
            
            if go_terms:
                # trouver le Top GO Term
                top_go_term, top_score = max(go_terms, key=lambda x: x[1])

                # sélectionner les termes ayant un score ≥ 0.5
                all_terms = [(term, score) for term, score in go_terms]  # garder tout

                results.append({
                    "Gene ID": gene_id,
                    "Position": position,
                    "Top GO Term": top_go_term,
                    "Confidence Score": top_score,
                    "All GO Terms": all_terms
                })
        return pd.DataFrame(results)
    
    except Exception as e:
        print(f"**Erreur lors de l'analyse du fichier : {e}")
        return pd.DataFrame()

def main():
    # définir les fichiers utilisés
    input_proteins_fasta = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\protein_sequences.fasta"
    deepgoplus_output_tsv = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\deepgoplus_output.tsv"
    final_annotations_csv = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\final_annotations.csv"
    deepgoplus_data_root = "C:\\Users\\MSI\\Downloads\\data_deepgoplus\\data"
    predicted_genes_fasta = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\predicted_genes.fasta"
    
    # exécution de deepgoplus
    run_deepgoplus(input_proteins_fasta, deepgoplus_output_tsv, deepgoplus_data_root)
    
    # vérification de l'existence du fichier de sortie
    if not os.path.exists(deepgoplus_output_tsv):
        print("**Le fichier de sortie DeepGOPlus est manquant")
        return
    
    # analyser les annotations réalisées
    annotations_df = extract_annotation(deepgoplus_output_tsv, predicted_genes_fasta)
    
    if annotations_df.empty:
        print("**Aucune annotation extraite")
        return
    
    # sauvegarder les annotations réalisés dans un fichier csv pour les utiliser dans l'affichage
    annotations_df.to_csv(final_annotations_csv, index=False)
    print(f"**Annotations terminées avec succès")

if __name__ == "__main__":
    main()