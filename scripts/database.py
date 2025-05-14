from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('genevision_db')

# Connexion à MongoDB avec gestion d'erreur
def get_db():
    uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    try:
        client = MongoClient(uri)
        db = client['genevision_db']
        # Test de connexion
        client.admin.command('ping')
        logger.info("MongoDB connection successful")
        return db, client
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise

# Initialisation de la base de données
try:
    db, client = get_db()
    users_col = db["users"]
    history_col = db["history"]
    sequences_col = db["sequences"]
    results_col = db["results"]
    reports_col = db["reports"]
    
    # Création des index pour optimiser les performances
    users_col.create_index("email", unique=True)
    history_col.create_index("user_id")
    sequences_col.create_index("user_id")
    results_col.create_index("sequence_id")
    reports_col.create_index("sequence_id")
    
    logger.info("Database collections and indexes initialized")

except Exception as e:
    logger.critical(f"Database initialization failed: {e}")
    raise

# partie de gestion des utilisateurs

#reset password
def reset_user_password(email, new_password):
    try:
        hashed = generate_password_hash(new_password)
        result = users_col.update_one({"email": email}, {"$set": {"password_hash": hashed}})
        if result.modified_count:
            user = get_user_by_email(email)
            log_activity(user["_id"], "password_reset", "Reset your password")
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return False

#sign in 
def register_user(name, email, password):

    try:
        if users_col.find_one({"email": email}):
            return False, "Email déjà utilisé.", None
        
        user = {
            "username": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "created_at": datetime.utcnow(),
            "active": True
        }
        
        result = users_col.insert_one(user)
        user_id = str(result.inserted_id)
        log_activity(user_id, "user_create", f"Account created for {name}")
        
        return True, "User registered successfully !", user_id
    except Exception as e:
        logger.error(f"User registration error: {e}")
        return False, f"Error during registration: {str(e)}", None

#vérification de id de user
def verify_user(email, password):
    try:
        user = users_col.find_one({"email": email})
        if user and check_password_hash(user["password_hash"], password):
            user["_id"] = str(user["_id"])
            return user
        return None
    except Exception as e:
        logger.error(f"Login verification error: {e}")
        return None

#récuprer user par id
def get_user_by_id(user_id):
    try:
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
        return user
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None

#récuprer user par email
def get_user_by_email(email):
    try:
        user = users_col.find_one({"email": email})
        if user:
            user["_id"] = str(user["_id"])
        return user
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return None

#update du profil de user
def update_user_profile(user_id, updated_fields):
    try:
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        
        # Empêcher la modification de champs sensibles
        safe_fields = {k: v for k, v in updated_fields.items() 
                      if k not in ["_id", "password_hash", "created_at"]}
        
        safe_fields["updated_at"] = datetime.utcnow()
        
        result = users_col.update_one(
            {"_id": user_id}, 
            {"$set": safe_fields}
        )
        
        if result.modified_count:
            log_activity(str(user_id), "profile_update", "Updating profile")
        
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        return False

#delate account
def deactivate_user(user_id):
    try:
        result = users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"active": False, "deactivated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"User deactivation error: {e}")
        return False

#Gestion des séquences
def get_download_links(seq_id):
    return {
        "Gene FASTA": f"/data/genes/{seq_id}.fasta",
        "Protein FASTA": f"/data/proteins/{seq_id}.fasta",
        "3D Model (PDB)": f"/data/pdb_models/{seq_id}.pdb"
    }


#create new sequence per user
def create_sequence(user_id, sequence, metadata=None):
    try:
        seq = {
            "user_id": user_id,
            "content": sequence,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "status": "created"
        }
        
        result = sequences_col.insert_one(seq)
        log_activity(user_id, "sequence_create", "Creating sequence")
        
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Sequence creation error: {e}")
        return None

#get sequence par id
def get_sequence(seq_id):
    try:
        seq = sequences_col.find_one({"_id": ObjectId(seq_id)})
        if seq:
            seq["_id"] = str(seq["_id"])
        return seq
    except Exception as e:
        logger.error(f"Error getting sequence: {e}")
        return None

#get les séquences d'un utilisateur avec filtrage : status: Filtre sur le statut
def get_user_sequences(user_id, limit=10, status=None):
    try:
        query = {"user_id": user_id}
        if status:
            query["status"] = status
            
        cursor = sequences_col.find(query).sort("created_at", -1).limit(limit)
        return [{**seq, "_id": str(seq["_id"])} for seq in cursor]
    except Exception as e:
        logger.error(f"Error getting user sequences: {e}")
        return []

#update de sequence
def update_sequence(seq_id, user_id, updates):
    try:
        updates["updated_at"] = datetime.utcnow()
        result = sequences_col.update_one(
            {"_id": ObjectId(seq_id), "user_id": user_id},
            {"$set": updates}
        )
        
        if result.modified_count:
            log_activity(user_id, "sequence_update", f"Mise à jour de la séquence {seq_id}")
            
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Sequence update error: {e}")
        return False

#delete sequence et tous les résultats/rapports associés
def delete_sequence(seq_id, user_id):
    try:
        # Vérification que la séquence appartient à l'utilisateur
        seq = sequences_col.find_one({"_id": ObjectId(seq_id), "user_id": user_id})
        if not seq:
            return False
            
        # Suppression des données associées
        results_col.delete_many({"sequence_id": seq_id})
        reports_col.delete_many({"sequence_id": seq_id})
        
        # Suppression de la séquence
        result = sequences_col.delete_one({"_id": ObjectId(seq_id)})
        
        if result.deleted_count:
            log_activity(user_id, "sequence_delete", f"Deletion of the sequence {seq_id}")
            
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Sequence deletion error: {e}")
        return False

# gestion des résultats d'analyse

#save le résultat d'une analyse
def create_analysis_result(seq_id, data):
    try:
        seq = get_sequence(seq_id)
        if not seq:
            return None
            
        user_id = seq["user_id"]
        
        res = {
            "sequence_id": seq_id,
            "user_id": user_id,
            "data": data,
            "created_at": datetime.utcnow()
        }
        
        result = results_col.insert_one(res)
        
        # Mise à jour du statut de la séquence
        update_sequence(seq_id, user_id, {"status": "completed"})
        
        log_activity(user_id, "analysis_complete", f"Analysis completed for sequence {seq_id}")
        
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Analysis result creation error: {e}")
        return None

#récupèrer tous les résultats de sequence
def get_sequence_results(seq_id):
    try:
        cursor = results_col.find({"sequence_id": seq_id})
        return [{**r, "_id": str(r["_id"])} for r in cursor]
    except Exception as e:
        logger.error(f"Error getting sequence results: {e}")
        return []

# gestion des rapports

#création du rapport per sequence
def create_report(seq_id, content, report_type="standard"):
    try:
        seq = get_sequence(seq_id)
        if not seq:
            return None
            
        rep = {
            "sequence_id": seq_id,
            "user_id": seq["user_id"],
            "content": content,
            "type": report_type,
            "created_at": datetime.utcnow()
        }
        
        result = reports_col.insert_one(rep)
        log_activity(seq["user_id"], "report_generate", f"Generate a report for sequence {seq_id}")
        
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Report creation error: {e}")
        return None

#récupèrer rapport par son id
def get_report(rep_id):
    try:
        rep = reports_col.find_one({"_id": ObjectId(rep_id)})
        if rep:
            rep["_id"] = str(rep["_id"])
        return rep
    except Exception as e:
        logger.error(f"Error getting report: {e}")
        return None

#récupèrer tous les rapports d'une séquence
def get_sequence_reports(seq_id):
    try:
        cursor = reports_col.find({"sequence_id": seq_id})
        return [{**r, "_id": str(r["_id"])} for r in cursor]
    except Exception as e:
        logger.error(f"Error getting sequence reports: {e}")
        return []

# historique et activités

#save activity de chaque user
def log_activity(user_id, action_type, description=None):
    try:
        log = {
            "user_id": user_id,
            "action_type": action_type,
            "timestamp": datetime.utcnow()
        }
        
        history_col.insert_one(log)
    except Exception as e:
        logger.error(f"Activity logging error: {e}")

#récuperer history d'activities per user avec options de filtrage avancées
#{user_id: ID de l'utilisateur, 
# limit: Nombre maximum d'entrées à retourner, 
# action_types: Liste des types d'actions à inclure (None = tous), 
# search_text: Texte à rechercher dans les descriptions, 
# start_date: Date de début pour le filtrage (datetime), 
# end_date: Date de fin pour le filtrage (datetime)}
def get_user_history(user_id, limit=20, action_types=None, search_text=None, start_date=None, end_date=None):
    try:
        # Construction du filtre
        query = {"user_id": user_id}
        
        # Filtrage par type d'action
        if action_types:
            if isinstance(action_types, list):
                query["action_type"] = {"$in": action_types}
            else:
                query["action_type"] = action_types
        
        # Recherche textuelle dans les descriptions
        if search_text:
            query["description"] = {"$regex": search_text, "$options": "i"}
        
        # Filtrage par date
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            if date_query:
                query["timestamp"] = date_query
        
        # Exécution de la requête
        cursor = history_col.find(query).sort("timestamp", -1).limit(limit)
        return [{**log, "_id": str(log["_id"])} for log in cursor]
    except Exception as e:
        logger.error(f"Error getting user history: {e}")
        return []

#delate une entrée d'historique spécifique
def delete_history_entry(entry_id, user_id):
    try:
        result = history_col.delete_one({
            "_id": ObjectId(entry_id),
            "user_id": user_id
        })
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"History entry deletion error: {e}")
        return False

#get des statistiques sur les activités d'un utilisateur
def get_activity_statistics(user_id):
    try:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$action_type", "count": {"$sum": 1}}}
        ]
        return list(history_col.aggregate(pipeline))
    except Exception as e:
        logger.error(f"Activity statistics error: {e}")
        return []

#delate les entrées d'historique plus anciennes que le nombre de jours spécifié (pour le momoent 90j)
def cleanup_old_history(days=90):
    try:
        cutoff_date = datetime.utcnow() - datetime.timedelta(days=days)
        result = history_col.delete_many({"timestamp": {"$lt": cutoff_date}})
        logger.info(f"Cleaned up {result.deleted_count} old history entries")
        return result.deleted_count
    except Exception as e:
        logger.error(f"History cleanup error: {e}")
        return 0

# fermeture de la connexion
def close_db():
    try:
        client.close()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")