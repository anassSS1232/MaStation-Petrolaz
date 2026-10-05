import re
import json
import html
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Form, Request, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ui_utils import layout
from database import get_db_connection, get_prix_carburant_a_date
from utils.client_helpers import nombre_en_lettres

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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
# 1. PAGE GLOBALE : TOUTES LES FACTURES CLIENTS
# ==========================================================
@router.get("/factures", response_class=HTMLResponse)
async def page_toutes_les_factures(
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
    query = """
        SELECT f.*, c.nom as client_nom, c.code as client_code, c.ice as client_ice, 
               c.telephone as client_telephone, c.adresse as client_adresse
        FROM factures_clients f
        LEFT JOIN clients c ON f.client_id = c.id
        ORDER BY f.date_facture DESC, f.id DESC
    """
    factures_rows = conn.execute(query).fetchall()
    clients_rows = conn.execute("SELECT * FROM clients ORDER BY nom ASC").fetchall()

    last_fact = conn.execute("SELECT numero_facture FROM factures_clients ORDER BY id DESC LIMIT 1").fetchone()
    prochain_numero = "0001"
    if last_fact and last_fact['numero_facture']:
        digits = re.findall(r'\d+', str(last_fact['numero_facture']))
        if digits:
            prochain_numero = f"{int(digits[-1]) + 1:04d}"

    conn.close()

    # Préparation des clients
    clients = []
    for c in clients_rows:
        cd = dict(c)
        clients.append({
            "id": cd.get("id"),
            "code": cd.get("code") or "—",
            "nom": cd.get("nom") or "",
            "ice": cd.get("ice") or "",
            "telephone": cd.get("telephone") or cd.get("tel") or "",
            "adresse": cd.get("adresse") or "Nador",
            "mode_reglement": cd.get("mode_paiement") or "Virement"
        })

    # Préparation des factures
    factures = []
    for f in factures_rows:
        f_dict = dict(f)
        f_id = f_dict.get('id')
        cid = f_dict.get('client_id')
        is_passager = not bool(cid)
        client_nom = f_dict.get('client_nom') or f_dict.get('destinataire_nom') or 'Passager / Divers'
        client_code = f_dict.get('client_code') or ('PASSAGER' if is_passager else '—')
        raw_date = f_dict.get('date_facture') or ''

        # Extraction détaillée des infos destinataire
        dest_info = f_dict.get('destinataire_info') or ''
        ice_val = f_dict.get('client_ice') or ''
        tel_val = f_dict.get('client_telephone') or ''
        adr_val = f_dict.get('client_adresse') or ''

        if not ice_val and 'ICE:' in dest_info.upper():
            m_ice = re.search(r'ICE\s*:\s*([^\s\-\|]+)', dest_info, re.IGNORECASE)
            if m_ice: ice_val = m_ice.group(1).strip()
        if not tel_val and 'TEL:' in dest_info.upper():
            m_tel = re.search(r'TEL\s*:\s*([^\s\-\|]+)', dest_info, re.IGNORECASE)
            if m_tel: tel_val = m_tel.group(1).strip()

        parts_info = dest_info.split(' - ')
        if len(parts_info) >= 4:
            adr_val = parts_info[-1].strip()
        if not adr_val:
            adr_val = "Nador"

        try:
            lignes_obj = json.loads(f_dict.get("lignes_json") or "[]")
        except Exception:
            lignes_obj = []

        facture_payload = {
            "id": f_id,
            "numero_facture": f_dict.get("numero_facture"),
            "date_facture": raw_date,
            "date_debut": f_dict.get("date_debut") or "",
            "date_fin": f_dict.get("date_fin") or "",
            "client_id": cid or "",
            "destinataire_nom": f_dict.get("destinataire_nom") or client_nom,
            "destinataire_ice": ice_val,
            "destinataire_tel": tel_val,
            "destinataire_adresse": adr_val,
            "client_nom": client_nom,
            "client_code": client_code,
            "client_ice": ice_val or "—",
            "client_tel": tel_val or "—",
            "mode_paiement": f_dict.get("mode_paiement") or "Virement",
            "montant_ht": float(f_dict.get("montant_ht") or 0.0),
            "taux_tva": float(f_dict.get("taux_tva") or 0.0),
            "montant_tva": float(f_dict.get("montant_tva") or 0.0),
            "remise_pourcent": float(f_dict.get("remise_pourcent") or 0.0),
            "montant_remise": float(f_dict.get("montant_remise") or 0.0),
            "montant_ttc": float(f_dict.get("montant_ttc") or 0.0),
            "notes": f_dict.get("notes") or "",
            "lignes": lignes_obj
        }

        search_blob = f"{f_dict.get('numero_facture', '')} {client_nom} {client_code} {f_dict.get('destinataire_nom', '')} {f_dict.get('mode_paiement', '')}".lower()

        factures.append({
            **f_dict,
            "client_nom": client_nom,
            "client_code": client_code,
            "is_passager": is_passager,
            "date_affichee": formater_date_fr(raw_date),
            "search_blob": search_blob,
            "json_payload": json.dumps(facture_payload)
        })

    template = templates.get_template("factures/factures_liste.html")
    inner_html = template.render({
        "request": request,
        "factures": factures,
        "clients": clients,
        "prochain_numero": prochainNumeroFactureDefaut(prochain_numero),
        "val_debut": val_debut,
        "val_fin": val_fin,
        "today_iso": today_dt.strftime("%Y-%m-%d"),
        "q": q or ""
    })
    return HTMLResponse(layout(inner_html, "factures", request=request))

def prochainNumeroFactureDefaut(num: str) -> str:
    return num

# ==========================================================
# 2. ACTIONS CRUD & API
# ==========================================================
@router.get("/api/tarif-date")
async def api_tarif_date(produit: str, date_consom: str):
    p_cle = produit.strip()
    prix_fixes = {
        '10W40 (55 MAD)': 55.0,
        '10W40 (250 MAD)': 250.0,
        '15W40 CF4 (42 MAD)': 42.0,
        '15W40 CF4 (200 MAD)': 200.0,
        'SAE 50 (185 MAD)': 185.0,
        'Lavage (40 MAD)': 40.0,
        'Lavage': 40.0,
        'Autre': 0.0
    }
    if p_cle in prix_fixes:
        return JSONResponse({"produit": produit, "date": date_consom, "pu": prix_fixes[p_cle]})

    pu = get_prix_carburant_a_date(produit, date_consom)
    return JSONResponse({"produit": produit, "date": date_consom, "pu": pu})

@router.post("/factures/creer")
async def action_creer_facture(
    client_id: Optional[str] = Form(None),
    numero_facture: str = Form(...),
    date_facture: str = Form(...),
    date_debut: str = Form(""),
    date_fin: str = Form(""),
    destinataire_nom: str = Form(""),
    destinataire_ice: str = Form(""),
    destinataire_tel: str = Form(""),
    destinataire_adresse: str = Form(""),
    destinataire_info: str = Form(""),
    taux_tva: float = Form(0.0),
    remise_pourcent: float = Form(0.0),
    montant_remise: float = Form(0.0),
    montant_ht: float = Form(...),
    montant_tva: float = Form(...),
    montant_ttc: float = Form(...),
    mode_paiement: str = Form("Virement"),
    notes: str = Form(""),
    lignes_json: str = Form("[]")
):
    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cid = int(client_id) if client_id and str(client_id).isdigit() and int(client_id) > 0 else None
    
    if cid:
        c = conn.execute("SELECT nom FROM clients WHERE id = ?", (cid,)).fetchone()
        client_nom = destinataire_nom.strip() or (c['nom'] if c else "Client")
    else:
        client_nom = destinataire_nom.strip() or "Particulier"

    if not destinataire_info:
        destinataire_info = f"{client_nom} - ICE: {destinataire_ice} - TEL: {destinataire_tel} - {destinataire_adresse}"

    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("""
            INSERT INTO factures_clients 
            (client_id, numero_facture, date_facture, date_debut, date_fin, destinataire_nom, destinataire_info, 
             taux_tva, remise_pourcent, montant_remise, montant_ht, montant_tva, montant_ttc, mode_paiement, 
             notes, lignes_json, statut, date_creation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Validée', ?)
        """, (cid, numero_facture.strip(), date_facture, date_debut, date_fin, client_nom, destinataire_info, 
              taux_tva, remise_pourcent, montant_remise, montant_ht, montant_tva, montant_ttc, mode_paiement, 
              notes, lignes_json, now))

        if cid:
            conn.execute("UPDATE clients SET solde = solde + ? WHERE id = ?", (montant_ttc, cid))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if cid:
        return RedirectResponse(url=f"/clients/{cid}?tab=factures", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/factures", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/factures/modifier")
async def action_modifier_facture(
    facture_id: int = Form(...),
    client_id: Optional[str] = Form(None),
    numero_facture: str = Form(...),
    date_facture: str = Form(...),
    destinataire_nom: str = Form(""),
    destinataire_ice: str = Form(""),
    destinataire_tel: str = Form(""),
    destinataire_adresse: str = Form(""),
    destinataire_info: str = Form(""),
    taux_tva: float = Form(0.0),
    remise_pourcent: float = Form(0.0),
    montant_remise: float = Form(0.0),
    montant_ht: float = Form(...),
    montant_tva: float = Form(...),
    montant_ttc: float = Form(...),
    mode_paiement: str = Form("Virement"),
    notes: str = Form(""),
    lignes_json: str = Form("[]")
):
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE;")
        ancienne = conn.execute("SELECT montant_ttc, client_id FROM factures_clients WHERE id = ?", (facture_id,)).fetchone()
        if not ancienne:
            conn.rollback()
            return RedirectResponse(url="/factures", status_code=status.HTTP_303_SEE_OTHER)

        ancien_ttc = float(ancienne['montant_ttc'] or 0.0)
        ancien_client_id = ancienne['client_id']
        cid = int(client_id) if client_id and str(client_id).isdigit() and int(client_id) > 0 else None

        nom_final = destinataire_nom.strip() or "Particulier"
        if not destinataire_info:
            destinataire_info = f"{nom_final} - ICE: {destinataire_ice} - TEL: {destinataire_tel} - {destinataire_adresse}"

        conn.execute("""
            UPDATE factures_clients 
            SET client_id = ?, numero_facture = ?, date_facture = ?, destinataire_nom = ?, destinataire_info = ?, 
                taux_tva = ?, remise_pourcent = ?, montant_remise = ?, montant_ht = ?, montant_tva = ?, 
                montant_ttc = ?, mode_paiement = ?, notes = ?, lignes_json = ?
            WHERE id = ?
        """, (cid, numero_facture.strip(), date_facture, nom_final, destinataire_info, taux_tva, 
              remise_pourcent, montant_remise, montant_ht, montant_tva, montant_ttc, mode_paiement, 
              notes, lignes_json, facture_id))

        if ancien_client_id and cid and ancien_client_id == cid:
            delta = montant_ttc - ancien_ttc
            conn.execute("UPDATE clients SET solde = solde + ? WHERE id = ?", (delta, cid))
        else:
            if ancien_client_id:
                conn.execute("UPDATE clients SET solde = solde - ? WHERE id = ?", (ancien_ttc, ancien_client_id))
            if cid:
                conn.execute("UPDATE clients SET solde = solde + ? WHERE id = ?", (montant_ttc, cid))

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return RedirectResponse(url="/factures", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/factures/delete")
async def action_supprimer_facture(facture_id: int = Form(...)):
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE;")
        f = conn.execute("SELECT montant_ttc, client_id FROM factures_clients WHERE id = ?", (facture_id,)).fetchone()
        if f:
            montant_ttc = float(f['montant_ttc'] or 0.0)
            cid = f['client_id']
            conn.execute("DELETE FROM factures_clients WHERE id = ?", (facture_id,))
            if cid:
                conn.execute("UPDATE clients SET solde = solde - ? WHERE id = ?", (montant_ttc, cid))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return RedirectResponse(url="/factures", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/factures/{facture_id}/imprimer", response_class=HTMLResponse)
async def imprimer_facture_pdf(request: Request, facture_id: int):
    conn = get_db_connection()
    f = conn.execute("SELECT * FROM factures_clients WHERE id = ?", (facture_id,)).fetchone()
    if not f:
        conn.close()
        return HTMLResponse("Facture introuvable.", status_code=404)

    f_dict = dict(f)
    client_id = f_dict.get('client_id')
    client = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone() if client_id else None
    conn.close()

    if client:
        c_dict = dict(client)
    else:
        dest_info = f_dict.get('destinataire_info') or ''
        nom = f_dict.get('destinataire_nom') or 'Particulier'
        ice = ''
        tel = ''
        adresse = 'Nador'

        if 'ICE:' in dest_info.upper():
            m_ice = re.search(r'ICE\s*:\s*([^\s\-\|]+)', dest_info, re.IGNORECASE)
            if m_ice: ice = m_ice.group(1).strip()
        if 'TEL:' in dest_info.upper():
            m_tel = re.search(r'TEL\s*:\s*([^\s\-\|]+)', dest_info, re.IGNORECASE)
            if m_tel: tel = m_tel.group(1).strip()

        c_dict = {
            "nom": nom,
            "code": "PASSAGER",
            "telephone": tel,
            "ice": ice,
            "adresse": adresse
        }

    try:
        lignes_brutes = json.loads(f_dict.get('lignes_json') or '[]')
    except Exception:
        lignes_brutes = []

    date_raw = f_dict.get('date_facture', '')
    date_fr = formater_date_fr(date_raw)

    lignes = []
    for l in lignes_brutes:
        qte = float(l.get('qte', 0.0))
        pu_ttc = float(l.get('pu', 0.0))
        total_ttc = float(l.get('total_ttc', qte * pu_ttc))
        raw_nom = str(l.get('produit') or l.get('designation') or 'Article').strip()
        date_ligne = str(l.get('date') or '').strip()

        match_date = re.search(r'\((\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})\)', raw_nom)
        if match_date:
            if not date_ligne:
                date_ligne = match_date.group(1)
            raw_nom = re.sub(r'\s*\(' + re.escape(match_date.group(1)) + r'\)\s*', '', raw_nom).strip()

        if not date_ligne:
            date_ligne = f_dict.get('date_facture', '')

        date_ligne = formater_date_fr(date_ligne)
        nom_upper = raw_nom.upper()
        if "GASOIL" in nom_upper:
            designation = "Ravitaillement de Gasoil 10"
        elif "SSP" in nom_upper or "ESSENCE" in nom_upper:
            designation = "Ravitaillement d'essence (S.S.P)"
        else:
            designation = raw_nom

        qte_str = f"{int(qte)}" if qte.is_integer() else f"{qte:,.2f}"

        lignes.append({
            "date": date_ligne,
            "designation": designation,
            "qte_str": qte_str if qte > 0 else "-",
            "pu_ttc_str": f"{pu_ttc:,.2f} DH" if pu_ttc > 0 else "-",
            "total_ttc_str": f"{total_ttc:,.2f} DH"
        })

    montant_ttc = float(f_dict.get('montant_ttc') or 0.0)
    lettres = nombre_en_lettres(montant_ttc).strip()
    if "DIRHAM" not in lettres.upper():
        lettres = f"{lettres} DIRHAMS"

    return templates.TemplateResponse(
        request=request,
        name="factures/facture.html",
        context={
            "f": f_dict,
            "client": c_dict,
            "lignes": lignes,
            "date_fr": date_fr,
            "montant_en_lettres": lettres,
            "cache_buster": datetime.now().strftime("%Y%m%d%H%M%S")
        }
    )