# ==================================================
# FICHIER : .\database.py (COMPLET + OPTIMISÉ)
# ==================================================

import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = "station.db"

def hash_mdp(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}${key.hex()}"

def verifier_mdp(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    if "$" not in stored_hash:
        return hashlib.sha256(password.encode("utf-8")).hexdigest() == stored_hash
    try:
        salt_hex, key_hex = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return new_key == expected_key
    except Exception:
        return False

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=25.0)
    # PRAGMAS D'ACCÉLÉRATION EN CACHE RAM
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")        # 64 Mo de cache RAM
    conn.execute("PRAGMA temp_store = MEMORY;")        # Tris et calculs en RAM
    conn.execute("PRAGMA mmap_size = 268435456;")      # Lecture fichier mémoire projetée
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nom_complet TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            cin TEXT DEFAULT '',
            cnss TEXT DEFAULT '',
            telephone TEXT DEFAULT '',
            date_embauche TEXT DEFAULT '',
            salaire_base REAL DEFAULT 0.0,
            adresse TEXT DEFAULT '',
            statut TEXT DEFAULT 'ACTIF'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prix_vente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT DEFAULT '',
            date_effet TEXT NOT NULL,
            produit TEXT NOT NULL,
            prix REAL NOT NULL,
            statut TEXT DEFAULT 'ACTIF'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cloture_quart (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            date TEXT, 
            operateur TEXT,
            fusion REAL DEFAULT 0, 
            tpe REAL DEFAULT 0, 
            especes REAL DEFAULT 0, 
            credits REAL DEFAULT 0,
            total_net REAL DEFAULT 0, 
            resultat REAL DEFAULT 0,
            details_json TEXT,
            credits_json TEXT DEFAULT '[]'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compteurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            date TEXT, 
            type TEXT,
            pompe_id INTEGER, 
            index_val REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions_jour (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_releve TEXT,
            sale_id TEXT,
            date_vente TEXT,
            heure TEXT,
            pump_id INTEGER,
            type TEXT,
            carburant TEXT,
            volume REAL DEFAULT 0.0,
            money REAL DEFAULT 0.0,
            initial_vol REAL DEFAULT 0.0,
            final_vol REAL DEFAULT 0.0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            contenu TEXT NOT NULL,
            categorie TEXT DEFAULT 'Général',
            couleur TEXT DEFAULT 'yellow',
            est_epingle INTEGER DEFAULT 0,
            date_creation TEXT NOT NULL,
            auteur TEXT DEFAULT 'Admin'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            type_fournisseur TEXT DEFAULT 'Carburant',
            contact_nom TEXT DEFAULT '',
            telephone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            adresse TEXT DEFAULT '',
            conditions_paiement TEXT DEFAULT '',
            solde_initial REAL DEFAULT 0.0,
            montant_fidelite REAL DEFAULT 0.0,
            document TEXT DEFAULT '',
            doc_categorie TEXT DEFAULT 'Autre',
            doc_description TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            statut TEXT DEFAULT 'Actif',
            date_creation TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achats_fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur_id INTEGER NOT NULL,
            numero_facture TEXT NOT NULL,
            date TEXT NOT NULL,
            reference_bl TEXT DEFAULT '',
            produit TEXT NOT NULL,
            volume_litres REAL DEFAULT 0.0,
            prix_unitaire REAL DEFAULT 0.0,
            montant_ht REAL DEFAULT 0.0,
            taux_tva REAL DEFAULT 10.0,
            montant_tva REAL DEFAULT 0.0,
            montant_total REAL NOT NULL,
            observations TEXT DEFAULT '',
            fichier_facture TEXT DEFAULT '',
            lignes_json TEXT DEFAULT '[]',
            FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reglements_fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            reference_paiement TEXT NOT NULL,
            mode_paiement TEXT NOT NULL,
            montant REAL NOT NULL,
            banque TEXT DEFAULT '',
            observations TEXT DEFAULT '',
            FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            nom TEXT NOT NULL,
            type_client TEXT DEFAULT 'Entreprise',
            contact_nom TEXT DEFAULT '',
            telephone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            adresse TEXT DEFAULT '',
            ice TEXT DEFAULT '',
            plafond REAL DEFAULT 0.0,
            solde REAL DEFAULT 0.0,
            delai_paiement INTEGER DEFAULT 0,
            mode_paiement TEXT DEFAULT 'Espèces',
            statut TEXT DEFAULT 'ACTIF',
            date_creation TEXT DEFAULT '',
            document TEXT DEFAULT '',
            doc_rc TEXT DEFAULT '',
            doc_statuts TEXT DEFAULT '',
            doc_cin TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS factures_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            numero_facture TEXT UNIQUE NOT NULL,
            date_facture TEXT NOT NULL,
            date_debut TEXT DEFAULT '',
            date_fin TEXT DEFAULT '',
            destinataire_nom TEXT DEFAULT '',
            destinataire_info TEXT DEFAULT '',
            taux_tva REAL DEFAULT 10.0,
            remise_pourcent REAL DEFAULT 0.0,
            montant_remise REAL DEFAULT 0.0,
            montant_ht REAL DEFAULT 0.0,
            montant_tva REAL DEFAULT 0.0,
            montant_ttc REAL NOT NULL,
            mode_paiement TEXT DEFAULT 'Espèces',
            notes TEXT DEFAULT '',
            lignes_json TEXT DEFAULT '[]',
            statut TEXT DEFAULT 'Validée',
            date_creation TEXT DEFAULT '',
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS client_encaissements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            client_nom_libre TEXT DEFAULT '',
            date_paiement TEXT NOT NULL,
            mode_paiement TEXT DEFAULT 'Espèces',
            banque TEXT DEFAULT '',
            reference TEXT DEFAULT '',
            description TEXT DEFAULT '',
            montant REAL NOT NULL,
            notes TEXT DEFAULT '',
            fichier TEXT DEFAULT '',
            statut TEXT DEFAULT 'Validé',
            operateur TEXT DEFAULT 'Safouane'
        )
    ''')

    # Migration douce pour toutes les colonnes additionnelles
    migrations = [
        ("achats_fournisseurs", "lignes_json", "TEXT DEFAULT '[]'"),
        ("client_encaissements", "client_nom_libre", "TEXT DEFAULT ''"),
        ("prix_vente", "date_effet", "TEXT DEFAULT ''")
    ]
    for table, col, col_type in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # ========================================================
    # INDEX DE PERFORMANCE CRITIQUES & INDEX D'EXPRESSION
    # ========================================================
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_jour ON transactions_jour(date_releve, type, pump_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_date_vente ON transactions_jour(date_vente);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fact_client ON factures_clients(client_id, date_facture);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_enc_client ON client_encaissements(client_id, date_paiement);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_achats_fourn ON achats_fournisseurs(fournisseur_id, date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prix_statut ON prix_vente(produit, statut);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_dates ON transactions_jour(date_releve, date_vente, type);")

    # Index calculé pour supprimer le freeze sur les rapports de ventes
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_calc_date ON transactions_jour(COALESCE(NULLIF(substr(date_vente, 1, 10), ''), date_releve), type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cloture_sub_date ON cloture_quart(substr(date, 1, 10));")
    except Exception:
        pass

    # Données par défaut
    cursor.execute("SELECT COUNT(*) FROM utilisateurs")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """INSERT INTO utilisateurs 
            (username, nom_complet, password, role, cin, cnss, telephone, date_embauche, salaire_base, adresse, statut) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("safouane_adm", "SAFOUANE", hash_mdp("admin123"), "admin", "U123456", "102938475", "+212 600 000 000", "2024-01-01", 8500.0, "Oujda", "ACTIF"),
                ("comptable_cpt", "M. COMPTABLE", hash_mdp("compte123"), "comptable", "U654321", "203948576", "+212 611 111 111", "2024-03-01", 6000.0, "Oujda", "ACTIF"),
                ("agent_emp", "AGENT POMPISTE", hash_mdp("emp123"), "employe", "S998877", "304958671", "+212 622 222 222", "2024-06-15", 3500.0, "Oujda", "ACTIF")
            ]
        )

    cursor.execute("SELECT COUNT(*) FROM prix_vente")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO prix_vente (date, date_effet, produit, prix, statut) VALUES ('2026-01-01', '2026-01-01', 'GAZOIL', 14.00, 'ACTIF')")
        cursor.execute("INSERT INTO prix_vente (date, date_effet, produit, prix, statut) VALUES ('2026-01-01', '2026-01-01', 'SSP', 15.00, 'ACTIF')")

    conn.commit()
    conn.close()

def parse_to_iso_datetime(dt_str: str) -> str:
    if not dt_str:
        return ""
    dt_str = str(dt_str).strip()
    if "/" in dt_str:
        parts = dt_str.split(" ")
        d_parts = parts[0].split("/")
        if len(d_parts) == 3:
            heure = parts[1] if len(parts) > 1 else "00:00:00"
            if len(heure.split(":")) == 2:
                heure += ":00"
            return f"{d_parts[2]}-{d_parts[1].zfill(2)}-{d_parts[0].zfill(2)} {heure}"
    if len(dt_str) == 10 and "-" in dt_str:
        return f"{dt_str} 00:00:00"
    return dt_str

def get_prix_carburant_a_date(produit: str, date_str: str) -> float:
    prod_upper = str(produit).upper().strip()
    is_diesel = any(k in prod_upper for k in ["DIESEL", "GAZOIL", "G10", "GO", "G50"])
    
    iso_date_norm = parse_to_iso_datetime(date_str) if date_str else ""
    clean_date = iso_date_norm[:10] if iso_date_norm else datetime.now().strftime("%Y-%m-%d")
    target_dt = f"{clean_date} 23:59:59"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, produit, prix, date_effet, date, statut FROM prix_vente")
    rows = cursor.fetchall()
    conn.close()

    candidats = []
    for r in rows:
        r_prod = str(r["produit"]).upper()
        r_is_diesel = any(k in r_prod for k in ["DIESEL", "GAZOIL", "G10", "GO", "G50"])
        
        if is_diesel == r_is_diesel:
            raw_date = r["date_effet"] or r["date"]
            iso_d = parse_to_iso_datetime(raw_date)
            if iso_d and iso_d <= target_dt:
                prio_actif = 1 if str(r["statut"]).upper() == "ACTIF" else 0
                candidats.append((iso_d, prio_actif, r["id"], float(r["prix"])))

    if candidats:
        candidats.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        return float(candidats[0][3])

    for r in rows:
        r_prod = str(r["produit"]).upper()
        if is_diesel == any(k in r_prod for k in ["DIESEL", "GAZOIL", "G10", "GO", "G50"]):
            if str(r["statut"]).upper() == "ACTIF":
                return float(r["prix"])

    return 14.00 if is_diesel else 15.00

def generer_prochain_code_fournisseur() -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT code FROM fournisseurs")
    rows = cursor.fetchall()
    conn.close()

    max_num = 0
    for r in rows:
        code_str = str(r["code"] or "").strip().upper()
        if code_str.startswith("FOUR-"):
            part = code_str.replace("FOUR-", "").strip()
            if part.isdigit():
                max_num = max(max_num, int(part))
        elif code_str.startswith("F") and code_str[1:].isdigit():
            max_num = max(max_num, int(code_str[1:]))

    return f"FOUR-{max_num + 1:03d}"

def generer_prochain_numero_facture() -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    today_code = datetime.now().strftime("%Y%m%d")
    cursor.execute("SELECT COUNT(*) FROM achats_fournisseurs WHERE numero_facture LIKE ?", (f"FAC-{today_code}%",))
    count = cursor.fetchone()[0] + 1
    conn.close()
    return f"FAC-{today_code}-{count:03d}"

def get_achats_filtres(date_debut: str = None, date_fin: str = None, fournisseur_id: int = None, min_montant: float = None, max_montant: float = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT a.*, f.nom as fournisseur_nom, f.code as fournisseur_code
        FROM achats_fournisseurs a
        LEFT JOIN fournisseurs f ON a.fournisseur_id = f.id
        WHERE 1=1
    """
    params = []
    if date_debut:
        query += " AND a.date >= ?"
        params.append(date_debut)
    if date_fin:
        query += " AND a.date <= ?"
        params.append(date_fin)
    if fournisseur_id and fournisseur_id > 0:
        query += " AND a.fournisseur_id = ?"
        params.append(fournisseur_id)
    if min_montant is not None and min_montant > 0:
        query += " AND a.montant_total >= ?"
        params.append(min_montant)
    if max_montant is not None and max_montant > 0:
        query += " AND a.montant_total <= ?"
        params.append(max_montant)
        
    query += " ORDER BY a.date DESC, a.id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def ajouter_achat(fournisseur_id: int, date: str, montant_total: float, numero_facture: str = "", reference_bl: str = "", produit: str = "Diesel", volume_litres: float = 0.0, prix_unitaire: float = 0.0, montant_ht: float = 0.0, taux_tva: float = 10.0, montant_tva: float = 0.0, observations: str = "", fichier_facture: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    if not numero_facture or numero_facture.strip() == "":
        numero_facture = generer_prochain_numero_facture()
    if montant_ht <= 0 and montant_total > 0:
        montant_ht = montant_total / (1 + (taux_tva / 100.0))
        montant_tva = montant_total - montant_ht

    cursor.execute("""
        INSERT INTO achats_fournisseurs 
        (fournisseur_id, numero_facture, date, reference_bl, produit, volume_litres, prix_unitaire, montant_ht, taux_tva, montant_tva, montant_total, observations, fichier_facture)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (fournisseur_id, numero_facture, date, reference_bl, produit, volume_litres, prix_unitaire, montant_ht, taux_tva, montant_tva, montant_total, observations, fichier_facture))
    conn.commit()
    conn.close()

def supprimer_achat(achat_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM achats_fournisseurs WHERE id = ?", (achat_id,))
    conn.commit()
    conn.close()

def get_fournisseurs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fournisseurs ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_fournisseur_complet(fournisseur_id: int = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if fournisseur_id:
        cursor.execute("SELECT * FROM fournisseurs WHERE id = ?", (fournisseur_id,))
    else:
        cursor.execute("SELECT * FROM fournisseurs ORDER BY id ASC LIMIT 1")
    fournisseur = cursor.fetchone()
    if not fournisseur:
        conn.close()
        return None
    f_id = fournisseur["id"]
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(montant_total), 0.0) FROM achats_fournisseurs WHERE fournisseur_id = ?", (f_id,))
    nb_achats, total_achats = cursor.fetchone()
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(montant), 0.0) FROM reglements_fournisseurs WHERE fournisseur_id = ?", (f_id,))
    nb_paiements, total_paye = cursor.fetchone()
    dette = (fournisseur["solde_initial"] + total_achats) - total_paye

    cursor.execute("""
        SELECT 'ACHAT' as type_op, id, date, COALESCE(numero_facture, reference_bl) as ref, 
               produit as details, 
               montant_total as montant_achat, 0.0 as montant_paye, observations, '' as mode, '' as banque
        FROM achats_fournisseurs WHERE fournisseur_id = ?
        UNION ALL
        SELECT 'PAIEMENT' as type_op, id, date, reference_paiement as ref, 
               mode_paiement || (CASE WHEN banque != '' THEN ' (' || banque || ')' ELSE '' END) as details, 
               0.0 as montant_achat, montant as montant_paye, observations, mode_paiement as mode, banque
        FROM reglements_fournisseurs WHERE fournisseur_id = ?
        ORDER BY date DESC, id DESC
    """, (f_id, f_id))
    operations = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {
        "fournisseur": dict(fournisseur),
        "nb_achats": nb_achats,
        "nb_paiements": nb_paiements,
        "total_achats": total_achats,
        "total_paye": total_paye,
        "dette": dette,
        "operations": operations
    }

def ajouter_fournisseur(code: str, nom: str, type_f: str = "Carburant", contact: str = "", tel: str = "", email: str = "", adresse: str = "", cond: str = "", solde_init: float = 0.0, statut: str = "Actif", montant_fidelite: float = 0.0, document: str = "", doc_categorie: str = "Autre", doc_description: str = "", notes: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO fournisseurs (
            code, nom, type_fournisseur, contact_nom, telephone, 
            email, adresse, conditions_paiement, solde_initial, 
            montant_fidelite, document, doc_categorie, doc_description, 
            notes, statut, date_creation
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date('now'))
    """, (code, nom, type_f, contact, tel, email, adresse, cond, solde_init, montant_fidelite, document, doc_categorie, doc_description, notes, statut))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def modifier_fournisseur(f_id: int, code: str, nom: str, type_f: str, contact: str, tel: str, email: str, adresse: str, cond: str, solde_init: float, statut: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE fournisseurs 
        SET code = ?, nom = ?, type_fournisseur = ?, contact_nom = ?, telephone = ?, email = ?, adresse = ?, conditions_paiement = ?, solde_initial = ?, statut = ?
        WHERE id = ?
    """, (code, nom, type_f, contact, tel, email, adresse, cond, solde_init, statut, f_id))
    conn.commit()
    conn.close()

def supprimer_fournisseur(f_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM achats_fournisseurs WHERE fournisseur_id = ?", (f_id,))
    cursor.execute("DELETE FROM reglements_fournisseurs WHERE fournisseur_id = ?", (f_id,))
    cursor.execute("DELETE FROM fournisseurs WHERE id = ?", (f_id,))
    conn.commit()
    conn.close()

def ajouter_reglement_fournisseur(fournisseur_id: int, date: str, reference: str, mode: str, montant: float, banque: str = "", obs: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reglements_fournisseurs (fournisseur_id, date, reference_paiement, mode_paiement, montant, banque, observations)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (fournisseur_id, date, reference, mode, montant, banque, obs))
    conn.commit()
    conn.close()

# ========================================================
# GESTION DES UTILISATEURS (CONNEXION & PROFIL)
# ========================================================

def verifier_utilisateur(username: str, password_clair: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nom_complet, password, role FROM utilisateurs WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user and verifier_mdp(password_clair, user["password"]):
        user_dict = dict(user)
        user_dict.pop("password", None)
        return user_dict
    return None

def lister_utilisateurs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM utilisateurs ORDER BY id DESC")
    users = [dict(u) for u in cursor.fetchall()]
    conn.close()
    return users

def get_utilisateur_by_id(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM utilisateurs WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def ajouter_utilisateur(username: str, nom_complet: str, password: str, role: str, cin: str = "", cnss: str = "", telephone: str = "", date_embauche: str = "", salaire_base: float = 0.0, adresse: str = "", statut: str = "ACTIF"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO utilisateurs 
        (username, nom_complet, password, role, cin, cnss, telephone, date_embauche, salaire_base, adresse, statut) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (username, nom_complet, hash_mdp(password), role, cin, cnss, telephone, date_embauche, salaire_base, adresse, statut)
    )
    conn.commit()
    conn.close()
    return True

def modifier_utilisateur(user_id: int, nom_complet: str, username: str, role: str, password: str = None, cin: str = "", cnss: str = "", telephone: str = "", date_embauche: str = "", salaire_base: float = 0.0, adresse: str = "", statut: str = "ACTIF"):
    conn = get_db_connection()
    cursor = conn.cursor()
    if password and password.strip():
        cursor.execute(
            """UPDATE utilisateurs 
            SET nom_complet = ?, username = ?, role = ?, password = ?, 
                cin = ?, cnss = ?, telephone = ?, date_embauche = ?, 
                salaire_base = ?, adresse = ?, statut = ? 
            WHERE id = ?""",
            (nom_complet, username, role, hash_mdp(password), cin, cnss, telephone, date_embauche, salaire_base, adresse, statut, user_id)
        )
    else:
        cursor.execute(
            """UPDATE utilisateurs 
            SET nom_complet = ?, username = ?, role = ?, 
                cin = ?, cnss = ?, telephone = ?, date_embauche = ?, 
                salaire_base = ?, adresse = ?, statut = ? 
            WHERE id = ?""",
            (nom_complet, username, role, cin, cnss, telephone, date_embauche, salaire_base, adresse, statut, user_id)
        )
    conn.commit()
    conn.close()

def supprimer_utilisateur(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

init_db()