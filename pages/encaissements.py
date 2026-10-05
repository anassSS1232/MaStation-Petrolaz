import time
import shutil
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Form, Request, UploadFile, File, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ui_utils import layout
from database import get_db_connection
from utils.client_helpers import nombre_en_lettres

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "encaissements"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

def ensure_schema(conn):
    try:
        conn.execute("ALTER TABLE client_encaissements ADD COLUMN client_nom_libre TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass

def formater_date_fr(date_str: str) -> str:
    if not date_str:
        return "—"
    try:
        if "-" in date_str:
            p = date_str.split("-")
            if len(p) == 3:
                return f"{p[2]}/{p[1]}/{p[0]}"
    except Exception:
        pass
    return date_str

# ==========================================================
# 1. PAGE GLOBALE : TOUS LES ENCAISSEMENTS
# ==========================================================
@router.get("/encaissements", response_class=HTMLResponse)
async def page_tous_les_encaissements(
    request: Request,
    q: str = Query(None),
    date_debut: str = Query(None),
    date_fin: str = Query(None)
):
    today_dt = datetime.now()
    default_debut = (today_dt - timedelta(days=7)).strftime("%Y-%m-%d")
    default_fin = today_dt.strftime("%Y-%m-%d")

    val_debut = date_debut if date_debut is not None else default_debut
    val_fin = date_fin if date_fin is not None else default_fin

    conn = get_db_connection()
    ensure_schema(conn)

    query = """
        SELECT e.*, 
               COALESCE(NULLIF(c.nom, ''), NULLIF(e.client_nom_libre, ''), 'Client Passager') as client_nom, 
               COALESCE(c.code, 'PASSAGER') as client_code, 
               c.ice as client_ice, 
               c.telephone as client_telephone, 
               c.adresse as client_adresse
        FROM client_encaissements e
        LEFT JOIN clients c ON e.client_id = c.id
        ORDER BY e.date_paiement DESC, e.id DESC
    """
    encaissements_rows = conn.execute(query).fetchall()
    clients_rows = conn.execute("SELECT id, code, nom, solde, ice, telephone FROM clients WHERE statut = 'ACTIF' ORDER BY nom ASC").fetchall()
    conn.close()

    # Préparation des clients
    clients = []
    for c in clients_rows:
        cd = dict(c)
        clients.append({
            "id": cd["id"],
            "code": cd.get("code") or "—",
            "nom": cd.get("nom") or "",
            "solde": float(cd.get("solde") or 0.0),
            "telephone": cd.get("telephone") or "",
            "ice": cd.get("ice") or ""
        })

    # Préparation des encaissements
    encaissements = []
    for e in encaissements_rows:
        e_dict = dict(e)
        cid = int(e_dict.get('client_id') or 0)
        is_passager = (cid == 0)
        raw_date = e_dict.get('date_paiement') or ''
        client_nom_val = e_dict.get('client_nom') or 'Client Passager'
        mode_val = e_dict.get('mode_paiement') or 'Espèces'
        fichier_url = f"/{e_dict['fichier']}" if e_dict.get('fichier') else ""

        encaissement_payload = {
            "id": e_dict.get("id"),
            "client_id": cid,
            "client_nom": client_nom_val,
            "client_code": e_dict.get("client_code") or ("PASSAGER" if is_passager else "—"),
            "client_ice": e_dict.get("client_ice") or "—",
            "client_tel": e_dict.get("client_telephone") or "—",
            "date_paiement": raw_date,
            "montant": float(e_dict.get("montant") or 0.0),
            "mode_paiement": mode_val,
            "banque": e_dict.get("banque") or "—",
            "reference": e_dict.get("reference") or "—",
            "description": e_dict.get("description") or "—",
            "operateur": e_dict.get("operateur") or "Safouane",
            "fichier": fichier_url
        }

        search_blob = f"{client_nom_val} {e_dict.get('client_code', '')} {mode_val} {e_dict.get('reference', '')} {e_dict.get('description', '')}".lower()

        encaissements.append({
            **e_dict,
            "client_nom": client_nom_val,
            "is_passager": is_passager,
            "date_affichee": formater_date_fr(raw_date),
            "fichier_url": fichier_url,
            "search_blob": search_blob,
            "json_payload": json.dumps(encaissement_payload)
        })

    template = templates.get_template("factures/encaissements_liste.html")
    inner_html = template.render({
        "request": request,
        "encaissements": encaissements,
        "clients": clients,
        "val_debut": val_debut,
        "val_fin": val_fin,
        "today_iso": today_dt.strftime("%Y-%m-%d"),
        "q": q or ""
    })
    return HTMLResponse(layout(inner_html, "encaissements", request=request))

# ==========================================================
# 2. ACTIONS CRUD & IMPRESSION
# ==========================================================
@router.post("/encaissements/ajouter")
@router.post("/clients/encaissement/add")
async def add_encaissement(
    request: Request,
    client_id: Optional[str] = Form("0"),
    client_nom_libre: str = Form(""),
    date_paiement: str = Form(...),
    montant: float = Form(...),
    mode_paiement: str = Form("Espèces"),
    reference: str = Form(""),
    description: str = Form(""),
    redirect_url: str = Form(""),
    fichier: UploadFile = File(None)
):
    user = getattr(request.state, "user", None)
    nom_op = user.get("nom_complet", "Safouane") if user else "Safouane"

    file_path = ""
    if fichier and fichier.filename:
        ext = os.path.splitext(fichier.filename)[1].lower()
        if ext in ALLOWED_EXT:
            filename = f"{int(time.time())}_{fichier.filename.replace(' ', '_')}"
            dest = UPLOAD_DIR / filename
            with dest.open("wb") as buffer:
                shutil.copyfileobj(fichier.file, buffer)
            file_path = f"static/uploads/encaissements/{filename}"

    cid = int(client_id) if client_id and str(client_id).isdigit() else 0

    conn = get_db_connection()
    ensure_schema(conn)
    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("""
            INSERT INTO client_encaissements 
            (client_id, client_nom_libre, date_paiement, mode_paiement, reference, description, montant, fichier, operateur, statut)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Validé')
        """, (cid, client_nom_libre.strip(), date_paiement, mode_paiement, reference.strip(), description.strip(), montant, file_path, nom_op))

        if cid > 0:
            conn.execute("UPDATE clients SET solde = solde - ? WHERE id = ?", (montant, cid))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if redirect_url:
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    if cid > 0:
        return RedirectResponse(url=f"/clients/{cid}?tab=encaissements", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/encaissements", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/clients/encaissement/delete")
async def delete_encaissement(encaissement_id: int = Form(...), client_id: int = Form(0)):
    conn = get_db_connection()
    ensure_schema(conn)
    try:
        conn.execute("BEGIN IMMEDIATE;")
        e = conn.execute("SELECT montant, client_id FROM client_encaissements WHERE id = ?", (encaissement_id,)).fetchone()
        if e:
            montant = float(e['montant'] or 0.0)
            cid = int(e['client_id'] or 0)
            conn.execute("DELETE FROM client_encaissements WHERE id = ?", (encaissement_id,))
            if cid > 0:
                conn.execute("UPDATE clients SET solde = solde + ? WHERE id = ?", (montant, cid))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if client_id > 0:
        return RedirectResponse(url=f"/clients/{client_id}?tab=encaissements", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/encaissements", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/encaissements/{encaissement_id}/imprimer", response_class=HTMLResponse)
async def imprimer_recu_encaissement(request: Request, encaissement_id: int):
    conn = get_db_connection()
    ensure_schema(conn)
    encaissement = conn.execute("SELECT * FROM client_encaissements WHERE id = ?", (encaissement_id,)).fetchone()
    if not encaissement:
        conn.close()
        return HTMLResponse("Encaissement introuvable.", status_code=404)

    e_dict = dict(encaissement)
    client_id = int(e_dict.get("client_id") or 0)
    client = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone() if client_id > 0 else None
    conn.close()

    nom_passager = e_dict.get("client_nom_libre") or "Client Passager / Particulier"
    c_dict = dict(client) if client else {
        "nom": nom_passager,
        "code": "PASSAGER",
        "telephone": "—",
        "ice": "—",
        "adresse": "Nador"
    }

    date_raw = str(e_dict.get("date_paiement") or "")
    date_fr = formater_date_fr(date_raw)

    montant = float(e_dict.get("montant") or 0.0)
    lettres = nombre_en_lettres(montant).strip()
    if "DIRHAM" not in lettres.upper():
        lettres = f"{lettres} DIRHAMS"

    return templates.TemplateResponse(
        request=request,
        name="factures/recu_encaissement.html",
        context={
            "e": e_dict,
            "client": c_dict,
            "date_fr": date_fr,
            "montant_en_lettres": lettres,
            "cache_buster": datetime.now().strftime("%Y%m%d%H%M%S")
        }
    )