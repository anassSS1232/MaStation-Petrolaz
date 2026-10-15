import json
import html
from datetime import datetime
from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse

from database import get_db_connection
from pages.portail_employe.views import vue_saisie_poste_employe

router = APIRouter(prefix="/employe", tags=["employe"])

@router.get("/poste", response_class=HTMLResponse)
async def page_poste_employe(request: Request, success: bool = False, msg: str = ""):
    conn = get_db_connection()
    user = getattr(request.state, "user", None)
    nom_operateur = (user.get("nom_complet", "Pompiste") if user else "Pompiste").upper()
    today_sql = datetime.now().strftime("%Y-%m-%d")

    # Heure début
    row_heure = conn.execute(
        "SELECT MIN(heure) as prem_heure FROM transactions_jour WHERE date_releve = ?", 
        (today_sql,)
    ).fetchone()
    prem_heure = row_heure["prem_heure"] if row_heure and row_heure["prem_heure"] else "08:00:00"
    if len(prem_heure.split(":")) == 2:
        prem_heure += ":00"
    heure_debut_iso = f"{today_sql}T{prem_heure}"

    # Tarifs actifs
    p_ssp = conn.execute(
        "SELECT prix FROM prix_vente WHERE produit IN ('SSP', 'Essence', 'Sans Plomb') AND statut='ACTIF' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    p_go = conn.execute(
        "SELECT prix FROM prix_vente WHERE produit IN ('GAZOIL', 'Gasoil', 'GO', 'Diesel', 'Gasoil 10') AND statut='ACTIF' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    
    prix_ssp = float(p_ssp['prix']) if p_ssp else 14.50
    prix_go = float(p_go['prix']) if p_go else 13.00

    # Volumes du jour
    row_vol = conn.execute("""
        SELECT 
            SUM(CASE WHEN type IN ('ESS', 'SSP') THEN volume ELSE 0 END) as v_ssp,
            SUM(CASE WHEN type IN ('DIE', 'GO', 'GAZOIL') THEN volume ELSE 0 END) as v_go
        FROM transactions_jour 
        WHERE date_releve = ?
    """, (today_sql,)).fetchone()

    total_ssp_l = float(row_vol['v_ssp'] or 0.0) if row_vol else 0.0
    total_go_l = float(row_vol['v_go'] or 0.0) if row_vol else 0.0
    total_theorique = (total_ssp_l * prix_ssp) + (total_go_l * prix_go)

    # Récupération clients actifs + matricule (enregistré dans adresse ou contact_nom)
    clients_rows = conn.execute("SELECT id, nom, code, adresse, contact_nom FROM clients WHERE statut='ACTIF' ORDER BY nom ASC").fetchall()
    
    clients_data = []
    for c in clients_rows:
        matricule = (c["adresse"] or c["contact_nom"] or "").strip()
        clients_data.append({
            "id": c["id"],
            "nom": c["nom"],
            "code": c["code"],
            "matricule": matricule
        })

    conn.close()

    alert_banner = ""
    if success:
        alert_banner = f"""
        <div class="bg-emerald-500/20 border-2 border-emerald-400 text-emerald-300 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-black flex items-center justify-between mb-3 animate-fadeIn">
            <span>✓ {html.escape(msg or 'Clôture validée avec succès.')}</span>
            <a href="/employe/poste" class="text-white hover:text-emerald-200 font-black text-sm">✕</a>
        </div>
        """

    return HTMLResponse(
        content=vue_saisie_poste_employe(
            nom_operateur=nom_operateur,
            heure_debut_iso=heure_debut_iso,
            total_theorique=total_theorique,
            clients_data=clients_data,
            prix_ssp=prix_ssp,
            prix_go=prix_go,
            message_alerte=alert_banner
        )
    )

@router.post("/cloturer")
async def action_cloturer_poste(
    fusion: float = Form(0.0), 
    tpe: float = Form(0.0), 
    especes_saisie_directe: float = Form(0.0),
    mode_especes: str = Form("detaille"),
    operateur: str = Form("Opérateur"),
    credits_json: str = Form("[]"),
    charges_json: str = Form("[]"),
    qte_200: int = Form(0), qte_100: int = Form(0), qte_50: int = Form(0), 
    qte_20: int = Form(0), qte_10: int = Form(0), qte_5: int = Form(0), 
    qte_2: int = Form(0), qte_1: int = Form(0), qte_0_5: int = Form(0)
):
    if mode_especes == "direct":
        especes = float(especes_saisie_directe or 0.0)
    else:
        especes = (
            (qte_200 * 200) + (qte_100 * 100) + (qte_50 * 50) +
            (qte_20 * 20) + (qte_10 * 10) + (qte_5 * 5) +
            (qte_2 * 2) + (qte_1 * 1) + (qte_0_5 * 0.5)
        )

    try:
        total_credits = sum([float(i.get('montant', 0) or 0) for i in json.loads(credits_json)])
    except Exception:
        total_credits = 0.0

    try:
        total_charges = sum([float(i.get('montant', 0) or 0) for i in json.loads(charges_json)])
    except Exception:
        total_charges = 0.0

    total_net = especes + tpe + total_credits + total_charges
    resultat = total_net - fusion if fusion > 0 else 0.0

    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO cloture_quart (date, operateur, fusion, tpe, especes, credits, total_net, resultat, details_json, credits_json, charges_json) 
           VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), operateur, fusion, tpe, especes, total_credits, total_net, resultat, "{}", credits_json, charges_json)
    )
    conn.commit()
    conn.close()

    return RedirectResponse(url="/employe/poste?success=true&msg=Clôture+validée", status_code=status.HTTP_303_SEE_OTHER)