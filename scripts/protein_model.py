import time
import requests
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union

#analyser le contenu dy fichier .fasta et extraire les sequences
#dict:clé= identifiant de seq et valeur=sequence
def parse_fasta(fasta_content: str) -> Dict[str, str]:
    sequences = {}
    current_id = None
    current_seq = []
    
    #parcours ligne par ligne du contenu FASTA
    for line in fasta_content.splitlines():
        line = line.strip()
        if not line:
            continue
        #si la ligne commence par '>', c'est un identifiant de séquence
        if line.startswith('>'):
            #save seq
            if current_id:
                sequences[current_id] = ''.join(current_seq)
                #extraire identifiant 
            current_id = line[1:].split()[0]
            current_seq = []
        else:
            current_seq.append(line)
    if current_id:
        sequences[current_id] = ''.join(current_seq)    
    return sequences

#lire et traiter contenu du fichier .fasta
def read_fasta_file(file_path: Union[str, Path]) -> Dict[str, str]:
    with open(file_path, 'r', encoding='utf-8') as f:
        fasta_content = f.read()
    return parse_fasta(fasta_content)

#réaliser 3D model du proteine en utilisant l'API ESMFold
def predict_structure(sequence: str, max_retries: int = 3, wait_time: int = 5) -> Optional[str]:
    api_url = "https://api.esmatlas.com/foldSequence/v1/pdb/"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                api_url,
                headers=headers,
                data=sequence,
                timeout=300
            )
            
            if response.status_code == 200:
                return response.text
            else:
                print(f"Tentative {attempt+1} échouée: {response.status_code} - {response.text}")
                if attempt < max_retries - 1:
                    print(f"Nouvelle tentative dans {wait_time} secondes...")
                    time.sleep(wait_time)
                    wait_time *= 2

        except Exception as e:
            print(f"Erreur lors de la tentative {attempt+1}: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Nouvelle tentative dans {wait_time} secondes...")
                time.sleep(wait_time)
                wait_time *= 2
    
    print(f"Échec après {max_retries} tentatives.")
    return None

#save le contenu PDB dans un fichier
def save_pdb(pdb_content: str, output_path: Union[str, Path]) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pdb_content)
    print(f" Structure PDB sauvegardée : {output_path}")

#traiter une séquence individuelle(seq longue)
def process_sequence(sequence: str, seq_id: str, output_dir: Union[str, Path], max_length: int = 400) -> Optional[str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Création d'un identifiant sécurisé pour le nom du fichier
    safe_id = ''.join(c if c.isalnum() else '_' for c in seq_id)
    output_path = output_dir / f"{safe_id}.pdb"

    # Gestion des longues séquences
    if len(sequence) > max_length:
        print(f"Avertissement: La séquence {seq_id} dépasse {max_length} aa. Utilisation de gene1.txt.")
        gene1_path = Path("data/pdb_models/gene1.txt")  #chemin simple et fiable
        
        if gene1_path.exists():
            with open(gene1_path, 'r', encoding='utf-8') as f:
                placeholder_content = f.read()
            save_pdb(placeholder_content, output_path)
            return str(output_path)
        else:
            print(" Erreur : le fichier gene1.txt est introuvable à data/pdb_models/gene1.txt.")
            return None

    # Pour les séquences de taille acceptable, on utilise l'API ESMatlas
    pdb_content = predict_structure(sequence)

    #save result
    if pdb_content:
        save_pdb(pdb_content, output_path)
        return str(output_path)
    else:
        print(f" Échec de la prédiction pour {seq_id}")
        return None

#traiter un fichier FASTA entier contenant plusieurs séquences
def process_fasta(fasta_path: Union[str, Path], output_dir: Union[str, Path], max_length: int = 400) -> List[str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    sequences = read_fasta_file(fasta_path)
    successful_pdbs = []
    
    # Traitement de chaque séquence
    for seq_id, sequence in sequences.items():
        print(f" Traitement de la séquence : {seq_id}")
        output_path = process_sequence(sequence, seq_id, output_dir, max_length)
        if output_path:
            successful_pdbs.append(output_path)

    return successful_pdbs

def main():
    parser = argparse.ArgumentParser(description="Convertir des séquences FASTA en structures PDB avec ESMFold")
    parser.add_argument("fasta_path", type=str, help="Chemin vers le fichier FASTA d'entrée")
    parser.add_argument("--output_dir", type=str, default="data/pdb_models", help="Répertoire de sortie pour les fichiers PDB")
    parser.add_argument("--max_length", type=int, default=400, help="Longueur maximale à traiter via ESMFold")
    args = parser.parse_args()

    pdbs = process_fasta(args.fasta_path, args.output_dir, args.max_length)

    print(f"\n Résumé : {len(pdbs)} structure(s) PDB générée(s).")

if __name__ == "__main__":
    main()