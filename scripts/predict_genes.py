#entrée: sequence génomique ni prédite ni annotée sous forme d'un fichier FASTA qui est inséré par user (input_sequences.fasta)
#sortie: les régions codantes prédites dans la seq insérée sous forme d'un fichier FASTA (predicted_genes.fasta)
#et un autre fichier FASTA qui contient la traduction proteique des genes predits (protein_sequences.fasta)
#et un fichier GFF qui contient les informations des genes predits (output_augustus.gff)

import re
from Bio import SeqIO
import subprocess

#exécuter outil augustus installé sur WSL via windows
def run_augustus(input_fasta, augustus_output, species="human"):
    

    input_fasta_wsl = input_fasta.replace("C:\\", "/mnt/c/").replace("\\", "/")
    output_gff_wsl = augustus_output.replace("C:\\", "/mnt/c/").replace("\\", "/")

    cmd = [
        "wsl",
        "augustus",
        f"--species={species}",
        input_fasta_wsl,
        f"--outfile={output_gff_wsl}"
    ]

    try:
        print("**Exécution de AUGUSTUS en cours")
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        print("**AUGUSTUS exécuté avec succès")
    except subprocess.CalledProcessError as e:
        print(f"**Erreur lors de l'exécution d'AUGUSTUS : {e}")
        exit(1)

# extraire les coordonnées des gènes et les séquences protéiques prédits par augustus
def extract_prediction(gff_file):

    genes = {}
    proteins = {}
    current_gene = None
    protein_seq = ""

    with open(gff_file, "r") as file:
        for line in file:
            # détecter début d'un gène
            if line.startswith("# start gene"):
                gene_number = len(genes) + 1
                current_gene = f"gene{gene_number}"
                genes[current_gene] = []
            # détecter fin d'un gène et enregistrer la séquence protéique
            elif line.startswith("# end gene"):
                if current_gene and protein_seq:
                    proteins[current_gene] = protein_seq
                current_gene = None
                protein_seq = ""
            # récupérer les coordonnées des CDS pour le gène en cours
            elif current_gene and "\tCDS\t" in line:
                cols = line.strip().split("\t")
                start, end = int(cols[3]), int(cols[4])
                genes[current_gene].append((start, end))
            # extraire la séquence protéique à partir de la ligne spécifique
            elif line.startswith("# protein sequence = ["):
                protein_seq = re.sub(r"[\[\]#\s]", "", line.split("=")[-1])
            # ajouter les lignes suivantes à la séquence protéique sans métadonnées
            elif protein_seq and not line.startswith("# Evidence for and against this transcript:"):
                protein_seq += re.sub(r"[\s#]", "", line.strip())
            # arrêter la collecte de la séquence quand la ligne contient des informations supplémentaires
            elif line.startswith("# Evidence for and against this transcript:"):
                if current_gene and protein_seq:
                    proteins[current_gene] = protein_seq[:-1] #supprimer dernier caractere qui est ]
                protein_seq = ""  # réinitialiser après avoir ajouté la séquence
                current_gene = None

    return genes, proteins

# extraire les séquences des gènes à partir du fichier input_seq.fasta inséré par l'utilisateur
def extract_gene_sequences(fasta_file, genes):
    
    sequences = SeqIO.to_dict(SeqIO.parse(fasta_file, "fasta"))
    gene_sequences = {}

    for gene_id, coords in genes.items():
        seq_id = list(sequences.keys())[0] # on suppose une seule séquence
        seq = sequences[seq_id].seq
        gene_seq = "".join(str(seq[start-1:end]) for start, end in sorted(coords))

        # ajouter les informations de start et stop codon
        start_codon = min(start for start, end in coords)
        stop_codon = max(end for start, end in coords)

        gene_sequences[gene_id] = {
            "sequence": gene_seq,
            "start_codon": start_codon,
            "stop_codon": stop_codon
        }

    return gene_sequences

#ecrire les séquences ADN des gènes dans un fichier FASTA
def write_fasta(file_path, sequences):
    
    with open(file_path, "w") as f:
        for gene, data in sequences.items():
            header = f">{gene} [organism=Homo sapiens] [start_codon={data['start_codon']}] [stop_codon={data['stop_codon']}]"
            f.write(f"{header}\n{data['sequence']}\n")

#écrire les séquences protéiques dans un fichier FASTA
def write_protein_fasta(file_path, proteins):

    with open(file_path, "w") as f:
        for gene, protein_seq in proteins.items():
            f.write(f">{gene}\n{protein_seq}\n")

def main():
    
    input_fasta = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\input_sequences.fasta"
    augustus_output = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\augustus_output.gff"
    predicted_genes_fasta = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\predicted_genes.fasta"
    protein_sequences_fasta = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\protein_sequences.fasta"

    # E1: lancer augustus
    run_augustus(input_fasta, augustus_output)

    # E2: extraire les informations de augustus
    genes, proteins = extract_prediction(augustus_output)

    # E3: extraire les séquences ADN correspondantes
    gene_sequences = extract_gene_sequences(input_fasta, genes)

    # E4: écrire les résultats dans les fichiers fasta de sortie
    write_fasta(predicted_genes_fasta, gene_sequences)
    write_protein_fasta(protein_sequences_fasta, proteins)

    print(f"**Prédiction terminée avec succès")

if __name__ == "__main__":
    main()
