# pages/clients.py
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Form, Request, Query, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ui_utils import layout
from database import get_db_connection
from utils.client_helpers import generate_next_client_code

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_CLIENTS_DIR = BASE_DIR / "static" / "uploads" / "clients"
UPLOAD_CLIENTS_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def sauvegarder_fichier_client(fichier: UploadFile, prefixe: str) -> str:
    if not fichier or not fichier.filename:
        return ""
    nom_fichier = os.path.basename(fichier.filename).replace(' ', '_')
    nom_securise = f"{prefixe}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{nom_fichier}"
    destination = UPLOAD_CLIENTS_DIR / nom_securise
    with open(destination, "wb") as f_out:
        shutil.copyfileobj(fichier.file, f_out)
    return f"/static/uploads/clients/{nom_securise}"

def formater_nom_client(type_client: str, nom_raw: str, prenom_raw: str = "") -> str:
    if type_client == "Particulier":
        nom_clean = nom_raw.strip().upper()
        prenom_clean = prenom_raw.strip().title()
        if prenom_clean:
            return f"{nom_clean} {prenom_clean}"
        parts = nom_clean.split()
        if len(parts) > 1:
            return f"{parts[0].upper()} {' '.join(parts[1:]).title()}"
        return nom_clean
    return nom_raw.strip().upper()

# ==========================================================
# 1. LISTE DES CLIENTS
# ==========================================================
@router.get("/clients", response_class=HTMLResponse)
async def clients_page(
    request: Request, 
    q: str = Query(None), 
    filtre: str = Query("tous")
):
    conn = get_db_connection()
    query = """
        SELECT c.*, 
               COALESCE((SELECT SUM(montant) FROM client_encaissements WHERE client_id = c.id), 0.0) AS total_paye
        FROM clients c
        WHERE 1=1
    """
    params = []
    
    if q:
        query += " AND (c.code LIKE ? OR c.nom LIKE ? OR c.telephone LIKE ? OR c.ice LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        
    if filtre == "actif":
        query += " AND c.statut = 'ACTIF'"
    elif filtre == "inactif":
        query += " AND c.statut = 'INACTIF'"
    elif filtre == "debiteur":
        query += " AND c.solde > 0"
        
    query += " ORDER BY c.nom ASC"

    clients_raw = conn.execute(query, params).fetchall()
    conn.close()

    clients = []
    for c in clients_raw:
        c_dict = dict(c)
        nom_raw = c_dict.get("nom") or "Sans Nom"
        solde = float(c_dict.get("solde") or 0.0)
        total_paye = float(c_dict.get("total_paye") or 0.0)

        clients.append({
            **c_dict,
            "solde": solde,
            "total_paye": total_paye,
            "search_blob": f"{nom_raw} {c_dict.get('code','')} {c_dict.get('type_client','')} {c_dict.get('telephone','')} {c_dict.get('ice','')}".lower()
        })

    template = templates.get_template("clients/clients_liste.html")
    inner_html = template.render({
        "request": request,
        "clients": clients,
        "q": q or "",
        "filtre": filtre,
        "auto_code": generate_next_client_code(),
        "total_clients": len(clients)
    })
    return HTMLResponse(layout(inner_html, "clients", request=request))

# ==========================================================
# 2. ACTIONS POST
# ==========================================================
@router.post("/clients/add")
async def add_client(
    code: str = Form(...), 
    type_client: str = Form("Entreprise"),
    nom_entreprise: str = Form(""),
    nom_particulier: str = Form(""),
    prenom_particulier: str = Form(""),
    telephone: str = Form(""), 
    ice: str = Form(""), 
    plafond: float = Form(0.0), 
    solde: float = Form(0.0),
    doc_rc_file: UploadFile = File(None),
    doc_statuts_file: UploadFile = File(None),
    doc_cin_file: UploadFile = File(None)
):
    nom_final = formater_nom_client("Particulier", nom_particulier, prenom_particulier) if type_client == "Particulier" else formater_nom_client("Entreprise", nom_entreprise)
    if not nom_final:
        nom_final = "SANS NOM"

    doc_rc = sauvegarder_fichier_client(doc_rc_file, "rc")
    doc_statuts = sauvegarder_fichier_client(doc_statuts_file, "statuts")
    doc_cin = sauvegarder_fichier_client(doc_cin_file, "cin")

    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        conn.execute("""
            INSERT INTO clients 
            (code, nom, type_client, telephone, ice, plafond, solde, statut, date_creation, doc_rc, doc_statuts, doc_cin)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIF', ?, ?, ?, ?)
        """, (code.strip().upper(), nom_final, type_client, telephone.strip(), ice.strip(), plafond, solde, now, doc_rc, doc_statuts, doc_cin))
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse(url="/clients", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/clients/edit-info")
async def edit_client_info(
    client_id: int = Form(...),
    code: str = Form(...),
    type_client: str = Form("Entreprise"),
    nom_entreprise: str = Form(""),
    nom_particulier: str = Form(""),
    prenom_particulier: str = Form(""),
    statut: str = Form("ACTIF"),
    telephone: str = Form(""),
    ice: str = Form(""),
    plafond: float = Form(0.0),
    solde: float = Form(0.0),
    doc_rc_file: UploadFile = File(None),
    doc_statuts_file: UploadFile = File(None),
    doc_cin_file: UploadFile = File(None)
):
    nom_final = formater_nom_client("Particulier", nom_particulier, prenom_particulier) if type_client == "Particulier" else formater_nom_client("Entreprise", nom_entreprise)
    if not nom_final:
        nom_final = "SANS NOM"

    conn = get_db_connection()
    try:
        cur_client = conn.execute("SELECT doc_rc, doc_statuts, doc_cin FROM clients WHERE id = ?", (client_id,)).fetchone()
        doc_rc = cur_client["doc_rc"] if cur_client else ""
        doc_statuts = cur_client["doc_statuts"] if cur_client else ""
        doc_cin = cur_client["doc_cin"] if cur_client else ""

        if doc_rc_file and doc_rc_file.filename:
            doc_rc = sauvegarder_fichier_client(doc_rc_file, "rc")
        if doc_statuts_file and doc_statuts_file.filename:
            doc_statuts = sauvegarder_fichier_client(doc_statuts_file, "statuts")
        if doc_cin_file and doc_cin_file.filename:
            doc_cin = sauvegarder_fichier_client(doc_cin_file, "cin")

        conn.execute("""
            UPDATE clients 
            SET code = ?, nom = ?, type_client = ?, statut = ?, telephone = ?, ice = ?, plafond = ?, solde = ?,
                doc_rc = ?, doc_statuts = ?, doc_cin = ?
            WHERE id = ?
        """, (code.strip().upper(), nom_final, type_client, statut, telephone.strip(), ice.strip(), plafond, solde, doc_rc, doc_statuts, doc_cin, client_id))
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse(url=f"/clients/{client_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/clients/delete")
async def action_supprimer_client(client_id: int = Form(...)):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM client_encaissements WHERE client_id = ?", (client_id,))
        conn.execute("DELETE FROM factures_clients WHERE client_id = ?", (client_id,))
        conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse(url="/clients", status_code=status.HTTP_303_SEE_OTHER)

# ==========================================================
# 3. DOSSIER CLIENT (HISTORIQUE DES FACTURES & RÈGLEMENTS)
# ==========================================================
@router.get("/clients/{client_id}", response_class=HTMLResponse)
async def client_detail_page(request: Request, client_id: int, tab: str = Query("factures")):
    conn = get_db_connection()
    client = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    if not client:
        conn.close()
        return RedirectResponse(url="/clients", status_code=status.HTTP_303_SEE_OTHER)

    c_dict = dict(client)
    factures_raw = conn.execute("SELECT * FROM factures_clients WHERE client_id = ? ORDER BY date_facture DESC, id DESC", (client_id,)).fetchall()
    encaissements_raw = conn.execute("SELECT * FROM client_encaissements WHERE client_id = ? ORDER BY date_paiement DESC, id DESC", (client_id,)).fetchall()
    conn.close()

    factures = []
    for f in factures_raw:
        f_dict = dict(f)
        lignes_brutes = f_dict.get('lignes_json') or '[]'
        try:
            lignes_obj = json.loads(lignes_brutes) if isinstance(lignes_brutes, str) else lignes_brutes
        except Exception:
            lignes_obj = []

        f_payload = {
            "id": f_dict["id"],
            "numero_facture": f_dict.get("numero_facture", ""),
            "date_facture": f_dict.get("date_facture", ""),
            "montant_ht": float(f_dict.get("montant_ht") or 0.0),
            "montant_tva": float(f_dict.get("montant_tva") or 0.0),
            "montant_ttc": float(f_dict.get("montant_ttc") or 0.0),
            "lignes": lignes_obj
        }
        factures.append({
            **f_dict,
            "montant_ht": float(f_dict.get('montant_ht') or 0.0),
            "montant_tva": float(f_dict.get('montant_tva') or 0.0),
            "montant_ttc": float(f_dict.get('montant_ttc') or 0.0),
            "periode_str": f"{f_dict.get('date_debut')} au {f_dict.get('date_fin')}" if f_dict.get('date_debut') else "Direct",
            "json_payload": json.dumps(f_payload)
        })

    encaissements = []
    for e in encaissements_raw:
        e_dict = dict(e)
        fichier_url = f"/{e_dict['fichier']}" if e_dict.get('fichier') else ""
        e_payload = {
            "id": e_dict["id"],
            "date_paiement": e_dict.get("date_paiement", ""),
            "montant": float(e_dict.get("montant", 0.0)),
            "mode_paiement": e_dict.get("mode_paiement", "Espèces"),
            "reference": e_dict.get("reference", ""),
            "description": e_dict.get("description", ""),
            "fichier": fichier_url
        }
        encaissements.append({
            **e_dict,
            "montant": float(e_dict.get("montant") or 0.0),
            "fichier_url": fichier_url,
            "json_payload": json.dumps(e_payload)
        })

    total_factures = sum(f['montant_ttc'] for f in factures)
    total_encaisse = sum(e['montant'] for e in encaissements)

    template = templates.get_template("clients/client_detail.html")
    inner_html = template.render({
        "request": request,
        "client": c_dict,
        "tab": tab,
        "factures": factures,
        "encaissements": encaissements,
        "total_factures": total_factures,
        "total_encaisse": total_encaisse,
        "solde_actuel": float(c_dict.get('solde') or 0.0)
    })
    return HTMLResponse(layout(inner_html, "clients", request=request))