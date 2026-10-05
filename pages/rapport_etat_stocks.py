# ==============================================================================
# FICHIER : pages/rapport_etat_stocks.py (AVEC MODALE HISTORIQUE EXACTE)
# ==============================================================================

import html
import json
import base64
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse

from database import get_db_connection, get_fournisseurs, get_prix_carburant_a_date
from ui_utils import layout

router = APIRouter()

def mad(val: float) -> str:
    try:
        return f"{float(val or 0.0):,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return "0,00"

def format_l(val: float) -> str:
    try:
        return f"{float(val or 0.0):,.0f}".replace(",", " ")
    except Exception:
        return "0"

CITERNES_CONFIG = {
    "C1": {
        "nom": "C1",
        "carburant": "Essence",
        "badge_color": "bg-sky-100 text-sky-800 dark:bg-sky-500/20 dark:text-sky-300 border-sky-300/40",
        "capacite": 31600.0,
        "seuil_alerte": 5000.0,
        "stock_initial": 15000.0
    },
    "C2": {
        "nom": "C2",
        "carburant": "Diesel",
        "badge_color": "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-[#E5A842] border-amber-300/40",
        "capacite": 60500.0,
        "seuil_alerte": 8000.0,
        "stock_initial": 35000.0
    }
}

PRODUITS_DIVERS_REF = [
    {"produit": "10W40 (5L)", "categorie": "Lubrifiant", "stock_initial": 45, "prix_unitaire": 250.0, "seuil": 10},
    {"produit": "10W40 (1L)", "categorie": "Lubrifiant", "stock_initial": 80, "prix_unitaire": 55.0, "seuil": 15},
    {"produit": "15W40 CF4 (5L)", "categorie": "Lubrifiant", "stock_initial": 30, "prix_unitaire": 200.0, "seuil": 8},
    {"produit": "15W40 CF4 (1L)", "categorie": "Lubrifiant", "stock_initial": 55, "prix_unitaire": 42.0, "seuil": 12},
    {"produit": "SAE 50 (5L)", "categorie": "Lubrifiant", "stock_initial": 25, "prix_unitaire": 185.0, "seuil": 5},
    {"produit": "Liquide Refroidissement", "categorie": "Entretien", "stock_initial": 40, "prix_unitaire": 60.0, "seuil": 10},
    {"produit": "Lave-Glace", "categorie": "Entretien", "stock_initial": 50, "prix_unitaire": 25.0, "seuil": 10}
]

@router.api_route("/centre-rapports/etat-stocks", methods=["GET", "POST"], response_class=HTMLResponse)
async def page_etat_stocks(
    request: Request,
    station: Optional[str] = Form("OKAY ENERGY"),
    type_stock: Optional[str] = Form("TOUS"),
    date_debut: Optional[str] = Form(None),
    date_fin: Optional[str] = Form(None)
):
    if request.method == "GET":
        qp = request.query_params
        station = qp.get("station", "OKAY ENERGY")
        type_stock = qp.get("type_stock", "TOUS")
        date_debut = qp.get("date_debut")
        date_fin = qp.get("date_fin")

    today = datetime.now()
    d_debut = date_debut or (today - timedelta(days=30)).strftime("%Y-%m-%d")
    d_fin = date_fin or today.strftime("%Y-%m-%d")

    conn = get_db_connection()

    # 1. Total des tirages pompes sur la période
    pompes_sorties = conn.execute("""
        SELECT 
            SUM(CASE WHEN type IN ('ESS', 'SSP') THEN volume ELSE 0 END) as sorties_essence,
            SUM(CASE WHEN type IN ('DIE', 'GO', 'GAZOIL') THEN volume ELSE 0 END) as sorties_diesel
        FROM transactions_jour
        WHERE COALESCE(NULLIF(substr(date_vente, 1, 10), ''), date_releve) BETWEEN ? AND ?
    """, (d_debut, d_fin)).fetchone()

    sorties_ess = float(pompes_sorties["sorties_essence"] or 0.0) if pompes_sorties else 0.0
    sorties_die = float(pompes_sorties["sorties_diesel"] or 0.0) if pompes_sorties else 0.0

    # 2. Entrées d'achats BL
    achats_lignes = conn.execute("""
        SELECT a.date, a.produit, a.volume_litres, a.lignes_json
        FROM achats_fournisseurs a
        WHERE a.date BETWEEN ? AND ?
    """, (d_debut, d_fin)).fetchall()

    entrees_ess = 0.0
    entrees_die = 0.0

    for a in achats_lignes:
        p_main = (a["produit"] or "").upper()
        v_main = float(a["volume_litres"] or 0.0)
        lignes_json = a["lignes_json"] or "[]"
        try:
            items = json.loads(lignes_json)
        except Exception:
            items = []

        if items:
            for it in items:
                p_it = str(it.get("produit", "")).upper()
                q_it = float(it.get("qte", 0.0))
                if any(k in p_it for k in ["ESS", "SSP", "SUPER"]):
                    entrees_ess += q_it
                elif any(k in p_it for k in ["DIE", "GASOIL", "GAZOIL", "GO"]):
                    entrees_die += q_it
        else:
            if any(k in p_main for k in ["ESS", "SSP", "SUPER"]):
                entrees_ess += v_main
            elif any(k in p_main for k in ["DIE", "GASOIL", "GAZOIL", "GO"]):
                entrees_die += v_main

    # 3. Stock Actuel Citernes
    c1_cap = CITERNES_CONFIG["C1"]["capacite"]
    c1_init = CITERNES_CONFIG["C1"]["stock_initial"]
    c1_actuel = max(0.0, min(c1_cap, c1_init + entrees_ess - sorties_ess))
    c1_pct = (c1_actuel / c1_cap * 100.0) if c1_cap > 0 else 0.0

    c2_cap = CITERNES_CONFIG["C2"]["capacite"]
    c2_init = CITERNES_CONFIG["C2"]["stock_initial"]
    c2_actuel = max(0.0, min(c2_cap, c2_init + entrees_die - sorties_die))
    c2_pct = (c2_actuel / c2_cap * 100.0) if c2_cap > 0 else 0.0

    total_capacite_carb = c1_cap + c2_cap
    total_stock_carb = c1_actuel + c2_actuel
    taux_remplissage_global = (total_stock_carb / total_capacite_carb * 100.0) if total_capacite_carb > 0 else 0.0

    # 4. Génération de l'historique par date pour la modale
    # Reconstitution journalière chronologique
    ventes_par_jour_raw = conn.execute("""
        SELECT 
            COALESCE(NULLIF(substr(date_vente, 1, 10), ''), date_releve) as jour,
            SUM(CASE WHEN type IN ('ESS', 'SSP') THEN volume ELSE 0 END) as v_ess,
            SUM(CASE WHEN type IN ('DIE', 'GO', 'GAZOIL') THEN volume ELSE 0 END) as v_die
        FROM transactions_jour
        WHERE COALESCE(NULLIF(substr(date_vente, 1, 10), ''), date_releve) BETWEEN ? AND ?
        GROUP BY jour
        ORDER BY jour DESC
    """, (d_debut, d_fin)).fetchall()

    dict_ventes = {r["jour"]: (float(r["v_ess"] or 0), float(r["v_die"] or 0)) for r in ventes_par_jour_raw}

    historique_modal = []
    # Dates entre date_fin et date_debut (ordre décroissant)
    try:
        dt_start = datetime.strptime(d_debut, "%Y-%m-%d")
        dt_end = datetime.strptime(d_fin, "%Y-%m-%d")
    except Exception:
        dt_start = today - timedelta(days=30)
        dt_end = today

    curr_dt = dt_end
    run_c1 = c1_actuel
    run_c2 = c2_actuel

    while curr_dt >= dt_start:
        j_iso = curr_dt.strftime("%Y-%m-%d")
        j_fr = curr_dt.strftime("%d/%m/%Y")
        v_ess_j, v_die_j = dict_ventes.get(j_iso, (0.0, 0.0))

        prix_die = get_prix_carburant_a_date("GAZOIL", j_iso)
        prix_ess = get_prix_carburant_a_date("SSP", j_iso)

        pct_die = (run_c2 / c2_cap * 100.0) if c2_cap > 0 else 0.0
        val_die = run_c2 * prix_die

        pct_ess = (run_c1 / c1_cap * 100.0) if c1_cap > 0 else 0.0
        val_ess = run_c1 * prix_ess

        # Ligne Diesel
        historique_modal.append({
            "date": j_fr,
            "date_iso": j_iso,
            "carburant": "Diesel",
            "type_carb": "DIE",
            "capacite": c2_cap,
            "stock": run_c2,
            "taux": pct_die,
            "valeur": val_die
        })

        # Ligne Essence
        historique_modal.append({
            "date": j_fr,
            "date_iso": j_iso,
            "carburant": "Essence",
            "type_carb": "ESS",
            "capacite": c1_cap,
            "stock": run_c1,
            "taux": pct_ess,
            "valeur": val_ess
        })

        # Recul théorique
        run_c1 = max(0.0, min(c1_cap, run_c1 + v_ess_j))
        run_c2 = max(0.0, min(c2_cap, run_c2 + v_die_j))

        curr_dt -= timedelta(days=1)

    # 5. Produits boutique
    produits_calcules = []
    valeur_stock_produits = 0.0
    alertes_count = 0

    if c1_actuel <= CITERNES_CONFIG["C1"]["seuil_alerte"]:
        alertes_count += 1
    if c2_actuel <= CITERNES_CONFIG["C2"]["seuil_alerte"]:
        alertes_count += 1

    for prod in PRODUITS_DIVERS_REF:
        qte_restante = prod["stock_initial"]
        val_produit = qte_restante * prod["prix_unitaire"]
        valeur_stock_produits += val_produit
        is_bas = qte_restante <= prod["seuil"]
        if is_bas:
            alertes_count += 1

        produits_calcules.append({
            "produit": prod["produit"],
            "categorie": prod["categorie"],
            "stock_actuel": qte_restante,
            "prix_unitaire": prod["prix_unitaire"],
            "valeur_stock": val_produit,
            "is_bas": is_bas
        })

    conn.close()

    def get_bar_color(pct: float) -> str:
        if pct < 20.0:
            return "bg-rose-500"
        elif pct < 45.0:
            return "bg-amber-500"
        return "bg-emerald-500"

    c1_bar_color = get_bar_color(c1_pct)
    c2_bar_color = get_bar_color(c2_pct)
    global_bar_color = get_bar_color(taux_remplissage_global)

    c1_badge_statut = '<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10.5px] font-bold bg-rose-500/15 text-rose-500 border border-rose-500/30">⚠ Bas</span>' if c1_actuel <= CITERNES_CONFIG["C1"]["seuil_alerte"] else '<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10.5px] font-bold bg-emerald-500/15 text-emerald-500">Normal</span>'
    c2_badge_statut = '<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10.5px] font-bold bg-rose-500/15 text-rose-500 border border-rose-500/30">⚠ Bas</span>' if c2_actuel <= CITERNES_CONFIG["C2"]["seuil_alerte"] else '<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10.5px] font-bold bg-emerald-500/15 text-emerald-500">Normal</span>'

    lignes_produits_html = ""
    for p in produits_calcules:
        badge_p = '<span class="px-1.5 py-0.5 rounded text-[10.5px] font-bold bg-rose-500/15 text-rose-500 border border-rose-500/30">Stock Faible</span>' if p["is_bas"] else '<span class="px-1.5 py-0.5 rounded text-[10.5px] font-bold bg-emerald-500/15 text-emerald-500">Optimal</span>'
        lignes_produits_html += f"""
        <tr class="border-b border-slate-100 dark:border-[#183042]/50 hover:bg-slate-50/50 dark:hover:bg-white/[0.02] text-xs font-semibold">
            <td class="py-2.5 px-4 font-bold text-slate-900 dark:text-white">{html.escape(p['produit'])}</td>
            <td class="py-2.5 px-4 text-slate-500 dark:text-slate-400">{html.escape(p['categorie'])}</td>
            <td class="py-2.5 px-4 text-center font-mono font-bold text-slate-800 dark:text-slate-200">{p['stock_actuel']} unités</td>
            <td class="py-2.5 px-4 text-right font-mono text-slate-700 dark:text-slate-300">{mad(p['prix_unitaire'])} DH</td>
            <td class="py-2.5 px-4 text-right font-mono font-black text-slate-900 dark:text-white">{mad(p['valeur_stock'])} DH</td>
            <td class="py-2.5 px-4 text-center">{badge_p}</td>
        </tr>
        """

    historique_json_b64 = base64.b64encode(json.dumps(historique_modal).encode("utf-8")).decode("utf-8")

    content = f"""
    <div class="max-w-7xl mx-auto space-y-4 animate-in fade-in duration-150">
        
        <!-- 1. EN-TÊTE ET FILTRES (CAPTURE 1 & 2) -->
        <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-[#183042]">
                <div class="flex items-center gap-2.5">
                    <div class="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center font-bold">
                        <i data-lucide="warehouse" class="w-4 h-4"></i>
                    </div>
                    <div>
                        <h1 class="font-black text-slate-900 dark:text-white text-sm uppercase tracking-wider">
                            État des Stocks
                        </h1>
                        <p class="text-[11px] text-slate-500 dark:text-slate-400">Inventaire physique des citernes et mouvements de cuves</p>
                    </div>
                </div>

                <a href="/centre-rapports" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-[#132738] text-slate-700 dark:text-slate-200 text-xs font-bold transition">
                    <i data-lucide="arrow-left" class="w-3.5 h-3.5"></i>
                    <span>Retour Hub</span>
                </a>
            </div>

            <!-- FORMULAIRE DE FILTRE -->
            <form method="POST" action="/centre-rapports/etat-stocks" class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
                <div class="sm:col-span-3">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Station</label>
                    <select name="station" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none cursor-pointer">
                        <option value="OKAY ENERGY" selected>OKAY ENERGY</option>
                    </select>
                </div>

                <div class="sm:col-span-3">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Type de Stock</label>
                    <select name="type_stock" id="filtreTypeStock" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none cursor-pointer">
                        <option value="TOUS" {"selected" if type_stock == "TOUS" else ""}>Tous (Carburant + Produits)</option>
                        <option value="CARBURANT" {"selected" if type_stock == "CARBURANT" else ""}>Carburant uniquement</option>
                        <option value="PRODUITS" {"selected" if type_stock == "PRODUITS" else ""}>Produits dérivés & Huiles</option>
                    </select>
                </div>

                <div class="sm:col-span-2">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Date début</label>
                    <input type="date" name="date_debut" value="{d_debut}" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold font-mono text-slate-900 dark:text-white outline-none cursor-pointer">
                </div>

                <div class="sm:col-span-2">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Date fin</label>
                    <input type="date" name="date_fin" value="{d_fin}" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold font-mono text-slate-900 dark:text-white outline-none cursor-pointer">
                </div>

                <div class="sm:col-span-2">
                    <button type="submit" class="w-full h-[38px] rounded-xl flex items-center justify-center gap-1.5 font-bold uppercase text-xs text-white bg-[#0284C7] hover:bg-sky-600 shadow-md transition cursor-pointer active:scale-95">
                        <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
                        <span>Actualiser</span>
                    </button>
                </div>
            </form>
        </div>

        <!-- 2. LES 6 CARTES KPIS (CAPTURE 3) -->
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div class="bg-white dark:bg-[#0E1B26] p-3.5 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-amber-500 shadow-xs text-center">
                <div class="text-xl font-black font-mono text-slate-900 dark:text-white">2</div>
                <span class="text-[9.5px] font-black uppercase text-slate-400 mt-1 block">CITERNES</span>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-3.5 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-sky-500 shadow-xs text-center">
                <div class="text-xl font-black font-mono text-slate-900 dark:text-white">{format_l(total_stock_carb)} L</div>
                <span class="text-[9.5px] font-black uppercase text-slate-400 mt-1 block">STOCK CARBURANT</span>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-3.5 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-teal-500 shadow-xs text-center">
                <div class="text-xl font-black font-mono text-teal-600 dark:text-teal-400">{taux_remplissage_global:.1f}%</div>
                <span class="text-[9.5px] font-black uppercase text-slate-400 mt-1 block">TAUX REMPLISSAGE</span>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-3.5 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-purple-500 shadow-xs text-center">
                <div class="text-xl font-black font-mono text-slate-900 dark:text-white">{len(PRODUITS_DIVERS_REF)}</div>
                <span class="text-[9.5px] font-black uppercase text-slate-400 mt-1 block">PRODUITS</span>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-3.5 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-emerald-500 shadow-xs text-center">
                <div class="text-xl font-black font-mono text-emerald-600 dark:text-emerald-400">{mad(valeur_stock_produits)}</div>
                <span class="text-[9.5px] font-black uppercase text-slate-400 mt-1 block">VALEUR STOCK</span>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-3.5 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-rose-500 shadow-xs text-center">
                <div class="text-xl font-black font-mono text-rose-600 dark:text-rose-400">{alertes_count}</div>
                <span class="text-[9.5px] font-black uppercase text-slate-400 mt-1 block">ALERTES STOCK BAS</span>
            </div>
        </div>

        <!-- 3. TABLEAU DES CITERNES CLIQUABLES (OUVRE LA MODALE EXACTE) -->
        <div id="section-citernes" class="bg-white dark:bg-[#0E1B26] rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs overflow-hidden">
            <div class="px-4 py-3 border-b border-slate-100 dark:border-[#183042] flex items-center justify-between">
                <h3 class="text-xs font-black uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
                    <i data-lucide="fuel" class="w-4 h-4 text-amber-500"></i>
                    Stock Carburant (Citernes)
                </h3>
                <span class="text-[11px] text-sky-600 dark:text-sky-400 font-bold flex items-center gap-1">
                    <i data-lucide="mouse-pointer-click" class="w-3.5 h-3.5"></i>
                    Cliquez sur une citerne pour voir les détails par date
                </span>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-slate-50 dark:bg-[#070E15] text-[10px] font-black uppercase text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-[#183042]">
                        <tr>
                            <th class="py-2.5 px-4">Station</th>
                            <th class="py-2.5 px-4">Citerne</th>
                            <th class="py-2.5 px-4">Type Carburant</th>
                            <th class="py-2.5 px-4 text-right">Capacité (L)</th>
                            <th class="py-2.5 px-4 text-right">Stock Actuel (L)</th>
                            <th class="py-2.5 px-4 text-left w-56">Taux Remplissage</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 dark:divide-[#183042]/50 text-xs font-semibold">
                        
                        <!-- LIGNE C1 ESSENCE (CLIQUABLE) -->
                        <tr onclick="ouvrirModalHistoriqueStock('Essence')" 
                            class="hover:bg-sky-500/10 dark:hover:bg-white/[0.05] cursor-pointer transition group" title="Cliquer pour afficher les détails Essence">
                            <td class="py-3 px-4 font-bold text-slate-800 dark:text-slate-200 group-hover:text-sky-500">OKAY ENERGY</td>
                            <td class="py-3 px-4 font-mono font-bold text-slate-700 dark:text-slate-300">C1</td>
                            <td class="py-3 px-4">
                                <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold {CITERNES_CONFIG['C1']['badge_color']} inline-flex items-center gap-1 shadow-2xs">
                                    Essence
                                    <i data-lucide="chevron-right" class="w-3 h-3"></i>
                                </span>
                            </td>
                            <td class="py-3 px-4 text-right font-mono font-bold text-slate-900 dark:text-white">
                                {format_l(c1_cap)}
                            </td>
                            <td class="py-3 px-4 text-right font-mono font-black text-slate-900 dark:text-white">
                                {format_l(c1_actuel)} {c1_badge_statut}
                            </td>
                            <td class="py-3 px-4">
                                <div class="flex items-center gap-3">
                                    <div class="flex-1 bg-slate-100 dark:bg-[#070E15] h-2.5 rounded-full overflow-hidden border border-slate-200 dark:border-[#183042]">
                                        <div class="{c1_bar_color} h-full rounded-full transition-all duration-500" style="width: {min(100.0, max(0.0, c1_pct)):.1f}%"></div>
                                    </div>
                                    <span class="font-mono text-xs font-black text-slate-800 dark:text-slate-200 w-14 text-right">{c1_pct:.1f}%</span>
                                </div>
                            </td>
                        </tr>

                        <!-- LIGNE C2 DIESEL (CLIQUABLE) -->
                        <tr onclick="ouvrirModalHistoriqueStock('Diesel')" 
                            class="hover:bg-amber-500/10 dark:hover:bg-white/[0.05] cursor-pointer transition group" title="Cliquer pour afficher les détails Diesel">
                            <td class="py-3 px-4 font-bold text-slate-800 dark:text-slate-200 group-hover:text-amber-500">OKAY ENERGY</td>
                            <td class="py-3 px-4 font-mono font-bold text-slate-700 dark:text-slate-300">C2</td>
                            <td class="py-3 px-4">
                                <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold {CITERNES_CONFIG['C2']['badge_color']} inline-flex items-center gap-1 shadow-2xs">
                                    Diesel
                                    <i data-lucide="chevron-right" class="w-3 h-3"></i>
                                </span>
                            </td>
                            <td class="py-3 px-4 text-right font-mono font-bold text-slate-900 dark:text-white">
                                {format_l(c2_cap)}
                            </td>
                            <td class="py-3 px-4 text-right font-mono font-black text-slate-900 dark:text-white">
                                {format_l(c2_actuel)} {c2_badge_statut}
                            </td>
                            <td class="py-3 px-4">
                                <div class="flex items-center gap-3">
                                    <div class="flex-1 bg-slate-100 dark:bg-[#070E15] h-2.5 rounded-full overflow-hidden border border-slate-200 dark:border-[#183042]">
                                        <div class="{c2_bar_color} h-full rounded-full transition-all duration-500" style="width: {min(100.0, max(0.0, c2_pct)):.1f}%"></div>
                                    </div>
                                    <span class="font-mono text-xs font-black text-slate-800 dark:text-slate-200 w-14 text-right">{c2_pct:.1f}%</span>
                                </div>
                            </td>
                        </tr>
                    </tbody>

                    <!-- PIED DU TABLEAU TOTAL -->
                    <tfoot class="bg-amber-100/60 dark:bg-amber-950/30 border-t-2 border-amber-300 dark:border-amber-900/40 text-xs font-black">
                        <tr>
                            <td colspan="3" class="py-3 px-4 uppercase text-slate-900 dark:text-white tracking-wider">TOTAL</td>
                            <td class="py-3 px-4 text-right font-mono text-slate-900 dark:text-white">{format_l(total_capacite_carb)}</td>
                            <td class="py-3 px-4 text-right font-mono text-slate-900 dark:text-white">{format_l(total_stock_carb)}</td>
                            <td class="py-3 px-4">
                                <div class="flex items-center gap-3">
                                    <div class="flex-1 bg-slate-200 dark:bg-[#070E15] h-2.5 rounded-full overflow-hidden">
                                        <div class="{global_bar_color} h-full rounded-full transition-all duration-500" style="width: {min(100.0, max(0.0, taux_remplissage_global)):.1f}%"></div>
                                    </div>
                                    <span class="font-mono text-xs font-black text-slate-900 dark:text-white w-14 text-right">{taux_remplissage_global:.1f}%</span>
                                </div>
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>

        <!-- 4. INVENTAIRE PRODUITS & LUBRIFIANTS -->
        <div id="section-produits" class="bg-white dark:bg-[#0E1B26] rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs overflow-hidden">
            <div class="px-4 py-3 border-b border-slate-100 dark:border-[#183042] flex items-center justify-between">
                <h3 class="text-xs font-black uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
                    <i data-lucide="package" class="w-4 h-4 text-sky-500"></i>
                    Inventaire Produits & Lubrifiants
                </h3>
                <span class="text-[11px] text-slate-400 font-mono">Boutique & Baie de graissage</span>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-slate-50 dark:bg-[#070E15] text-[10px] font-black uppercase text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-[#183042]">
                        <tr>
                            <th class="py-2.5 px-4">Produit / Désignation</th>
                            <th class="py-2.5 px-4">Catégorie</th>
                            <th class="py-2.5 px-4 text-center">Quantité Restante</th>
                            <th class="py-2.5 px-4 text-right">Prix Unitaire</th>
                            <th class="py-2.5 px-4 text-right">Valeur Totale</th>
                            <th class="py-2.5 px-4 text-center">Statut Stock</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 dark:divide-[#183042]/50">
                        {lignes_produits_html}
                    </tbody>
                    <tfoot class="bg-slate-50/80 dark:bg-[#070E15] border-t-2 border-slate-200 dark:border-[#183042] text-xs font-black">
                        <tr>
                            <td colspan="4" class="py-3 px-4 uppercase text-slate-900 dark:text-white">VALEUR GLOBALE PRODUITS</td>
                            <td class="py-3 px-4 text-right font-mono text-emerald-600 dark:text-emerald-400">{mad(valeur_stock_produits)} DH</td>
                            <td></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>

    </div>

    <!-- ============================================================================== -->
    <!-- 5. MODALE POP-UP EXACTEMENT IDENTIQUE À VOTRE DEUXIÈME IMAGE -->
    <!-- ============================================================================== -->
    <div id="modal-historique-stock" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 hidden transition-all">
        
        <div id="modal-box-stock" class="bg-[#0A1622] border border-[#1b3449] rounded-2xl w-full max-w-5xl h-[88vh] flex flex-col shadow-2xl overflow-hidden transition-all duration-200">
            
            <!-- EN-TÊTE MODALE -->
            <div class="px-5 py-3 border-b border-[#1b3449] bg-[#071018] flex items-center justify-between shrink-0">
                <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-lg bg-sky-500/15 text-sky-400 flex items-center justify-center font-bold">
                        <i data-lucide="calendar" class="w-4 h-4"></i>
                    </div>
                    <span class="font-black text-xs uppercase tracking-wider text-slate-200">
                        Stock Carburant par Carburant et Date
                    </span>
                </div>

                <!-- Badge Date Centrale -->
                <div class="px-4 py-1.5 rounded-xl bg-purple-500/15 border border-purple-400/30 flex items-center gap-2 shadow-xs">
                    <i data-lucide="calendar-range" class="w-4 h-4 text-purple-400"></i>
                    <span id="modal-stock-periode-titre" class="text-sm font-black font-mono tracking-widest text-purple-300">
                        {d_debut} ➔ {d_fin}
                    </span>
                </div>

                <div class="flex items-center gap-2">
                    <button type="button" onclick="toggleAgrandirModalStock()" title="Agrandir / Réduire" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 flex items-center justify-center cursor-pointer transition">
                        <i id="icon-maximize-stock" data-lucide="maximize-2" class="w-4 h-4"></i>
                    </button>
                    <button type="button" onclick="fermerModalHistoriqueStock()" title="Fermer" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-rose-500/20 hover:text-rose-400 text-slate-300 flex items-center justify-center cursor-pointer transition">
                        <i data-lucide="x" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <!-- FILTRES INTERNES DE LA MODALE -->
            <div class="px-5 py-3 bg-[#0d1d2c] border-b border-[#1b3449] flex flex-wrap items-center justify-between gap-3 shrink-0">
                <div class="flex items-center gap-1.5 bg-[#071018] p-1 rounded-xl border border-[#1e3a52]">
                    <span class="text-[10px] font-black uppercase text-slate-400 px-2">Carburant:</span>
                    <button type="button" onclick="setFiltreCarbModal('ALL')" id="btn-modal-carb-ALL" class="btn-carb-pill-modal px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition bg-purple-600 text-white">Tous</button>
                    <button type="button" onclick="setFiltreCarbModal('Essence')" id="btn-modal-carb-Essence" class="btn-carb-pill-modal px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white">Essence</button>
                    <button type="button" onclick="setFiltreCarbModal('Diesel')" id="btn-modal-carb-Diesel" class="btn-carb-pill-modal px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white">Diesel</button>
                </div>

                <div class="relative w-48 sm:w-64">
                    <input type="text" id="modalRechercheDateStock" oninput="appliquerFiltresModalStock()" placeholder="Rechercher une date (ex: 31/10)..." 
                           class="w-full bg-[#071018] border border-[#1e3a52] rounded-xl px-3 py-1.5 text-xs font-mono font-bold text-purple-300 placeholder-slate-500 outline-none focus:border-purple-400">
                </div>
            </div>

            <!-- STATISTIQUES RAPIDES DU FILTRE MODALE -->
            <div class="px-5 py-2 bg-[#091520] border-b border-[#1b3449]/70 flex items-center justify-between text-[11px] font-bold text-slate-400 shrink-0">
                <span id="modalStockCompteur" class="text-purple-400 font-mono">0 ligne(s)</span>
                <div class="flex items-center gap-4 font-mono">
                    <span>Valeur Sélectionnée : <strong id="modalStockTotalVal" class="text-white font-black">0,00 DH</strong></span>
                </div>
            </div>

            <!-- TABLEAU EXACT DE L'IMAGE 1 AVEC LES EN-TÊTES IDENTIQUES -->
            <div class="flex-1 overflow-y-auto bg-[#071018]">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-[#122435] sticky top-0 z-20 border-b-2 border-[#1E3A52] shadow-sm">
                        <tr class="text-[12px] sm:text-[13px] font-black uppercase text-white tracking-wider">
                            <th class="py-3 px-4 text-purple-300">Date</th>
                            <th class="py-3 px-4 text-white">Type Carburant</th>
                            <th class="py-3 px-4 text-right text-white">Capacité (L)</th>
                            <th class="py-3 px-4 text-right text-white">Stock Actuel (L)</th>
                            <th class="py-3 px-4 text-left w-56 text-teal-300">Taux Remplissage</th>
                            <th class="py-3 px-4 text-right text-white">Valeur Stock</th>
                        </tr>
                    </thead>
                    <tbody id="modalStockTbody" class="divide-y divide-[#183042]/50 text-xs font-semibold text-slate-200 font-mono">
                    </tbody>
                </table>
                <div id="modalStockEmpty" class="text-center py-16 text-slate-500 font-bold hidden font-sans">
                    Aucun historique de stock trouvé pour les critères sélectionnés.
                </div>
            </div>

        </div>
    </div>

    <!-- MOTEUR JAVASCRIPT COMPLET ET SYNCHRONE -->
    <script>
        const RAW_HISTO_B64 = "{historique_json_b64}";
        const DONNEES_HISTORIQUE = JSON.parse(decodeURIComponent(escape(atob(RAW_HISTO_B64))));

        let filtreCarbModalActif = 'ALL';
        let estPleinEcranStock = false;

        function badgeCarbModal(carb) {{
            if (carb.toLowerCase() === 'essence') {{
                return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-100 text-sky-800 dark:bg-sky-500/20 dark:text-sky-300 border border-sky-300/40">Essence</span>';
            }}
            return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-[#E5A842] border border-amber-300/40">Diesel</span>';
        }}

        function ouvrirModalHistoriqueStock(carburantParDefaut) {{
            filtreCarbModalActif = carburantParDefaut || 'ALL';
            document.getElementById('modalRechercheDateStock').value = '';
            majPillsCarbModal();
            appliquerFiltresModalStock();
            document.getElementById('modal-historique-stock').classList.remove('hidden');
            if (window.lucide) lucide.createIcons();
        }}

        function fermerModalHistoriqueStock() {{
            document.getElementById('modal-historique-stock').classList.add('hidden');
        }}

        function setFiltreCarbModal(carb) {{
            filtreCarbModalActif = carb;
            majPillsCarbModal();
            appliquerFiltresModalStock();
        }}

        function majPillsCarbModal() {{
            document.querySelectorAll('.btn-carb-pill-modal').forEach(btn => {{
                btn.className = "btn-carb-pill-modal px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white";
            }});
            const actif = document.getElementById('btn-modal-carb-' + filtreCarbModalActif);
            if (actif) actif.className = "btn-carb-pill-modal px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition bg-purple-600 text-white shadow-sm";
        }}

        function appliquerFiltresModalStock() {{
            const search = document.getElementById('modalRechercheDateStock').value.trim().toLowerCase();
            let lignes = DONNEES_HISTORIQUE;

            if (filtreCarbModalActif !== 'ALL') {{
                lignes = lignes.filter(l => l.carburant.toLowerCase() === filtreCarbModalActif.toLowerCase());
            }}

            if (search) {{
                lignes = lignes.filter(l => l.date.includes(search) || l.date_iso.includes(search));
            }}

            afficherLignesModalStock(lignes);
        }}

        function afficherLignesModalStock(lignes) {{
            const tbody = document.getElementById('modalStockTbody');
            const empty = document.getElementById('modalStockEmpty');
            const compteur = document.getElementById('modalStockCompteur');
            const totalValEl = document.getElementById('modalStockTotalVal');

            compteur.innerText = `${{lignes.length}} ligne(s)`;

            let sumValeur = 0;
            if (lignes.length === 0) {{
                tbody.innerHTML = '';
                empty.classList.remove('hidden');
                totalValEl.innerText = '0,00 DH';
                return;
            }}

            empty.classList.add('hidden');
            let h = '';
            lignes.forEach(l => {{
                sumValeur += l.valeur;
                const barColor = l.taux < 20 ? 'bg-rose-500' : (l.taux < 45 ? 'bg-amber-500' : 'bg-emerald-500');
                const textColor = l.taux < 20 ? 'text-rose-400' : (l.taux < 45 ? 'text-amber-400' : 'text-emerald-400');

                h += `
                <tr class="hover:bg-white/[0.04] transition-colors border-b border-[#183042]/40">
                    <td class="py-2.5 px-4 font-bold text-slate-200">${{l.date}}</td>
                    <td class="py-2.5 px-4 font-sans">${{badgeCarbModal(l.carburant)}}</td>
                    <td class="py-2.5 px-4 text-right text-slate-300 font-bold">${{l.capacite.toLocaleString('fr-FR')}}</td>
                    <td class="py-2.5 px-4 text-right font-black text-white">${{l.stock.toLocaleString('fr-FR', {{ minimumFractionDigits: 0, maximumFractionDigits: 0 }})}}</td>
                    <td class="py-2.5 px-4">
                        <div class="flex items-center gap-3">
                            <div class="flex-1 bg-[#071018] h-2.5 rounded-full overflow-hidden border border-[#1e3a52]">
                                <div class="${{barColor}} h-full rounded-full transition-all duration-300" style="width: ${{Math.min(100, Math.max(0, l.taux))}}%"></div>
                            </div>
                            <span class="${{textColor}} font-black text-xs w-14 text-right">${{l.taux.toFixed(1)}}%</span>
                        </div>
                    </td>
                    <td class="py-2.5 px-4 text-right font-black text-slate-100">${{l.valeur.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}} DH</td>
                </tr>
                `;
            }});

            tbody.innerHTML = h;
            totalValEl.innerText = sumValeur.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
        }}

        function toggleAgrandirModalStock() {{
            const box = document.getElementById('modal-box-stock');
            const icon = document.getElementById('icon-maximize-stock');
            estPleinEcranStock = !estPleinEcranStock;

            if (estPleinEcranStock) {{
                box.classList.remove('max-w-5xl', 'h-[88vh]', 'rounded-2xl');
                box.classList.add('max-w-none', 'h-full', 'rounded-none');
                icon.setAttribute('data-lucide', 'minimize-2');
            }} else {{
                box.classList.add('max-w-5xl', 'h-[88vh]', 'rounded-2xl');
                box.classList.remove('max-w-none', 'h-full', 'rounded-none');
                icon.setAttribute('data-lucide', 'maximize-2');
            }}
            if (window.lucide) lucide.createIcons();
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') fermerModalHistoriqueStock();
        }});
    </script>
    """
    return HTMLResponse(layout(content, active_tab="centre_rapports", request=request))