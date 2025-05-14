#dans cette partie du projet, on va utiliser QuickGO à l'aide de son API REST pour avoir les fonctions et desceiptions de chaque GO Term
#identifié par model deepGOPlus 
#utiliser Gemini pour simplifier ces descriptions
#entrée: fichier (final_annotations.csv) qui contient tous les informations nécessaires des termes GO définis
# sortie: fichier (final_annotations.csv) juste on le modifie et on ajoute la fonction :  le nom et la descprition de chaque term GO défini

import requests
import pandas as pd

from llm_gemini_resume import run_llm_resume

def search_go_info(go_id):
    #récupèrer le nom et la description du chaque GO Term défini à l'aide de l'API QuickGO
    url = f"https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/{go_id}"
    headers = {"Accept": "application/json"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:  # Si la requête réussit
        data = response.json()  # Convertir la réponse JSON en dictionnaire Python
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            go_name = result.get("name", "Name not found")
            go_description = result.get("definition", {}).get("text", "Description not found")
            return go_name, go_description
    
    return "Name not found", "Description not found"

# charger le fichier final_annotations.csv
final_annotations_csv = "C:\\Users\\MSI\\Documents\\PFE\\DNA_project\\data\\final_annotations.csv"
df = pd.read_csv(final_annotations_csv)

# vérifier si les colonnes nécessaires existent déjà, sinon les ajouter
if "Top GO Term Name" not in df.columns:
    df["Top GO Term Name"] = ""
if "Top GO Term Description" not in df.columns:
    df["Top GO Term Description"] = ""
if "All GO Terms" not in df.columns:
    df["All GO Terms"] = ""

# parcourir chaque ligne pour ajouter les noms et descriptions des termes GO
for index, row in df.iterrows():
    top_go_term = row["Top GO Term"].strip()
    go_name, go_description = search_go_info(top_go_term)
    
    df.at[index, "Top GO Term Name"] = go_name
    df.at[index, "Top GO Term Description"] = run_llm_resume(go_description)

    # traiter les termes GO filtrés
    filtered_go_terms = eval(row["All GO Terms"]) if isinstance(row["All GO Terms"], str) else []
    filtered_info = []
    
    for go_entry in filtered_go_terms:
        go_id = go_entry[0]  # Le premier élément est l'ID GO
        go_name, go_description = search_go_info(go_id)
        filtered_info.append((go_id, go_entry[1], go_name, go_description))

    df.at[index, "All GO Terms"] = str(filtered_info)

# sauvegarder les modifications dans le même fichier CSV
df.to_csv(final_annotations_csv, index=False)

print("**Attirbution des fonctions terminée avec succès")
