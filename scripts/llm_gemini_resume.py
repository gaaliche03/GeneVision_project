# llm_resume.py - Script Windows pour appeler le résumé de description via WSL
import subprocess
import os
import re


#exécuter script du LLM pour avoir la simplification de la description
def run_llm_resume(description):
    # chemins de l'environnement Python virtuel et le script dans WSL
    wsl_python_path = "/home/gaaliche/venv-gemini/bin/python3"
    wsl_script_path = "/home/gaaliche/llm_resume_core.py"
    
    # échapper les caractères spéciaux pour éviter les problèmes dans la commande shell
    escaped_description = description.replace('"', '\\"').replace("'", "\\'")
    
    # Commande à exécuter via WSL
    cmd = [
        "wsl",
        wsl_python_path,
        wsl_script_path,
        f'"{escaped_description}"'
    ]
    
    try:
        print("**Exécution du résumé LLM via WSL en cours")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        print("**Résumé LLM exécuté avec succès")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"**Erreur lors de l'exécution du résumé LLM : {e.stderr}")
        return None

#traiter fichier qui contient descriptions et generer simplification
def process_go_terms(input_file, output_file):
    with open(input_file, 'r') as f:
        descriptions = f.readlines()
    
    results = []
    for i, description in enumerate(descriptions):
        if description.strip():  # Ignorer les lignes vides
            print(f"Traitement de la description {i+1}/{len(descriptions)}")
            summary = run_llm_resume(description.strip())
            if summary:
                results.append(f"Description originale: {description.strip()}\nRésumé: {summary}\n\n")
    
    with open(output_file, 'w') as f:
        f.writelines(results)
    
    print(f"**Traitement terminé, résultats enregistrés dans {output_file}")

def main():
    # Pour une seule description
    description = (
        "A biological process is the execution of a genetically-encoded biological module or program. "
        "It consists of all the steps required to achieve the specific biological objective of the module. "
        "A biological process is accomplished by a particular set of molecular functions carried out by "
        "specific gene products (or macromolecular complexes), often in a highly regulated manner and in "
        "a particular temporal sequence."
    )
    
    result = run_llm_resume(description)
    print("\nRésultat du résumé:\n", result)
    
    # Pour traiter un fichier entier de descriptions (option commentée)
    # input_file = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\go_descriptions.txt"
    # output_file = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\go_summaries.txt"
    # process_go_terms(input_file, output_file)

if __name__ == "__main__":
    main()