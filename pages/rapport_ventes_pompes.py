# ==============================================================================
# FICHIER : pages/rapport_ventes_pompes.py (FILTRES PAR QUARTS/CARB + HEADERS CLAIRS)
# ==============================================================================

import html
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse

from database import get_db_connection, get_fournisseurs
from ui_utils import layout

router = APIRouter()

def mad(val: float) -> str:
    try:
        return f"{float(val or 0.0):,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return "0,00"

# ==============================================================================
# 1. API AJAX : DÉTAIL DES TIRAGES D'UN JOUR
# ==============================================================================
@router.get("/api/rapport/jour-details")
async def api_jour_details(date_jour: str):
    conn = get_db_connection()
    
    c_quart = conn.execute("""
        SELECT SUM(especes) as tot_esp, SUM(tpe) as tot_tpe, SUM(total_net) as tot_net
        FROM cloture_quart WHERE date LIKE ? || '%'
    """, (date_jour,)).fetchone()
    
    tot_net = float(c_quart['tot_net'] or 0.0) if c_quart else 0.0
    r_tpe = (float(c_quart['tot_tpe'] or 0.0) / tot_net) if tot_net > 0 else 0.125
    r_esp = 1.0 - r_tpe

    rows = conn.execute("""
        SELECT heure, date_vente, sale_id, pump_id, type, volume, money
        FROM transactions_jour
        WHERE (date_releve = ? OR date_vente LIKE ? || '%')
        ORDER BY id DESC LIMIT 500
    """, (date_jour, date_jour)).fetchall()
    conn.close()

    lignes = []
    for r in rows:
        h = str(r["heure"] or (r["date_vente"].split()[-1] if r["date_vente"] and " " in r["date_vente"] else "--:--"))[:8]
        mnt = float(r["money"] or 0.0)
        c_nom = "SSP" if r["type"] in ["ESS", "SSP"] else "DIESEL"

        lignes.append({
            "heure": h,
            "sale_id": r["sale_id"] or "--",
            "pump": f"Pompe {r['pump_id']}",
            "carb": c_nom,
            "vol_raw": float(r["volume"] or 0.0),
            "mnt_raw": mnt,
            "vol": mad(r["volume"]),
            "mnt": mad(mnt),
            "tpe": mad(mnt * r_tpe),
            "esp": mad(mnt * r_esp)
        })

    return JSONResponse({"status": "success", "date": date_jour, "lignes": lignes})

# ==============================================================================
# 2. PAGE PRINCIPALE
# ==============================================================================
@router.api_route("/centre-rapports/ventes-carburants", methods=["GET", "POST"], response_class=HTMLResponse)
async def page_ventes_carburants(
    request: Request,
    fournisseur_id: Optional[int] = Form(None),
    date_debut: Optional[str] = Form(None),
    date_fin: Optional[str] = Form(None)
):
    if request.method == "GET":
        qp = request.query_params
        fournisseur_id = int(qp.get("fournisseur_id", 0)) if qp.get("fournisseur_id") else 0
        date_debut = qp.get("date_debut")
        date_fin = qp.get("date_fin")

    today = datetime.now()
    d_debut = date_debut or (today - timedelta(days=30)).strftime("%Y-%m-%d")
    d_fin = date_fin or today.strftime("%Y-%m-%d")

    fournisseurs = get_fournisseurs()
    okay_energy_id = next((f["id"] for f in fournisseurs if "OKAY" in f.get("nom", "").upper()), 0)
    if not fournisseur_id and okay_energy_id:
        fournisseur_id = okay_energy_id

    conn = get_db_connection()

    ratios = conn.execute("""
        SELECT SUM(especes) as tot_esp, SUM(tpe) as tot_tpe, SUM(total_net) as tot_net
        FROM cloture_quart WHERE substr(date, 1, 10) BETWEEN ? AND ?
    """, (d_debut, d_fin)).fetchone()

    tot_net = float(ratios['tot_net'] or 0.0) if ratios else 0.0
    r_tpe = (float(ratios['tot_tpe'] or 0.0) / tot_net) if tot_net > 0 else 0.125
    r_esp = 1.0 - r_tpe

    query_synth = """
        SELECT 
            COALESCE(NULLIF(substr(date_vente, 1, 10), ''), date_releve) as jour,
            COUNT(id) as nb_tirages,
            SUM(CASE WHEN type IN ('DIE', 'GO', 'GAZOIL') THEN volume ELSE 0 END) as vol_die,
            SUM(CASE WHEN type IN ('ESS', 'SSP') THEN volume ELSE 0 END) as vol_ssp,
            SUM(volume) as vol_tot,
            SUM(money) as mnt_tot
        FROM transactions_jour
        WHERE COALESCE(NULLIF(substr(date_vente, 1, 10), ''), date_releve) BETWEEN ? AND ?
        GROUP BY jour
        ORDER BY jour DESC
        LIMIT 60
    """
    lignes_jours = conn.execute(query_synth, (d_debut, d_fin)).fetchall()
    conn.close()

    tot_vol_die = sum(float(j["vol_die"] or 0) for j in lignes_jours)
    tot_vol_ssp = sum(float(j["vol_ssp"] or 0) for j in lignes_jours)
    tot_volume = sum(float(j["vol_tot"] or 0) for j in lignes_jours)
    tot_montant = sum(float(j["mnt_tot"] or 0) for j in lignes_jours)
    tot_tpe = tot_montant * r_tpe
    tot_especes = tot_montant * r_esp

    tableau_jours_html = ""
    for j in lignes_jours:
        j_date = j["jour"]
        mnt = float(j["mnt_tot"] or 0)
        tpe_val = mnt * r_tpe
        esp_val = mnt * r_esp

        tableau_jours_html += f"""
        <tr class="border-b border-slate-100 dark:border-[#183042]/50 hover:bg-sky-50/50 dark:hover:bg-white/[0.02] text-xs font-semibold">
            <td class="py-3 px-4 font-mono font-bold text-sky-600 dark:text-sky-400">{j_date}</td>
            <td class="py-3 px-4 text-center font-bold text-slate-500">{j['nb_tirages']}</td>
            <td class="py-3 px-4 text-right font-mono font-bold text-slate-800 dark:text-slate-200">{mad(j['vol_die'])} L</td>
            <td class="py-3 px-4 text-right font-mono font-bold text-slate-800 dark:text-slate-200">{mad(j['vol_ssp'])} L</td>
            <td class="py-3 px-4 text-right font-mono font-black text-slate-900 dark:text-white">{mad(mnt)} DH</td>
            <td class="py-3 px-4 text-right font-mono font-bold text-purple-600 dark:text-purple-400">{mad(tpe_val)} DH</td>
            <td class="py-3 px-4 text-right font-mono font-bold text-teal-600 dark:text-teal-400">{mad(esp_val)} DH</td>
            <td class="py-3 px-4 text-center">
                <button type="button" onclick="ouvrirModalTirages('{j_date}')" class="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-sky-600 hover:text-white dark:bg-[#132738] dark:hover:bg-sky-600 text-slate-700 dark:text-slate-200 text-[11px] font-bold transition flex items-center gap-1 mx-auto cursor-pointer">
                    <i data-lucide="list" class="w-3.5 h-3.5"></i>
                    <span>Tirages</span>
                </button>
            </td>
        </tr>
        """

    if not tableau_jours_html:
        tableau_jours_html = '<tr><td colspan="8" class="text-center py-8 text-slate-400 italic">Aucune donnée trouvée sur cette période.</td></tr>'

    options_fournisseurs = "".join(
        f'<option value="{f["id"]}" {"selected" if f["id"] == fournisseur_id else ""}>{html.escape(f["nom"])}</option>'
        for f in fournisseurs
    )

    content = f"""
    <div class="max-w-7xl mx-auto space-y-4 animate-in fade-in duration-150">
        
        <!-- EN-TÊTE + FILTRES -->
        <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-[#183042]">
                <div class="flex items-center gap-2.5">
                    <div class="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center font-bold">
                        <i data-lucide="fuel" class="w-4 h-4"></i>
                    </div>
                    <h1 class="font-black text-slate-900 dark:text-white text-sm uppercase tracking-wider">
                        Rapport Carburants & Synthèse Journalière
                    </h1>
                </div>

                <a href="/centre-rapports" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-[#132738] text-slate-700 dark:text-slate-200 text-xs font-bold transition">
                    <i data-lucide="arrow-left" class="w-3.5 h-3.5"></i>
                    <span>Retour Hub</span>
                </a>
            </div>

            <form method="POST" action="/centre-rapports/ventes-carburants" class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
                <div class="sm:col-span-4">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Station</label>
                    <select name="fournisseur_id" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none">
                        {options_fournisseurs}
                    </select>
                </div>

                <div class="sm:col-span-3">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Date début</label>
                    <input type="date" name="date_debut" value="{d_debut}" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold font-mono text-slate-900 dark:text-white outline-none">
                </div>

                <div class="sm:col-span-3">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Date fin</label>
                    <input type="date" name="date_fin" value="{d_fin}" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold font-mono text-slate-900 dark:text-white outline-none">
                </div>

                <div class="sm:col-span-2">
                    <button type="submit" class="w-full h-[38px] rounded-xl flex items-center justify-center gap-1.5 font-bold uppercase text-xs text-white bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 shadow-md transition cursor-pointer active:scale-95">
                        <i data-lucide="filter" class="w-3.5 h-3.5"></i>
                        <span>Actualiser</span>
                    </button>
                </div>
            </form>
        </div>

        <!-- 4 CARTES KPI -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-blue-500 shadow-xs text-center">
                <div class="text-xl font-black font-mono text-slate-900 dark:text-white">{mad(tot_volume)} L</div>
                <div class="flex justify-center gap-3 text-[10.5px] font-bold text-slate-400 mt-1">
                    <span>DIE: {mad(tot_vol_die)} L</span>
                    <span>•</span>
                    <span>SSP: {mad(tot_vol_ssp)} L</span>
                </div>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-emerald-500 shadow-xs text-center">
                <div class="text-xl font-black font-mono text-slate-900 dark:text-white">{mad(tot_montant)} DH</div>
                <span class="text-[10px] font-black uppercase text-slate-400 mt-1 block">Chiffre d'Affaires Brut</span>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-purple-500 shadow-xs text-center">
                <div class="text-xl font-black font-mono text-purple-600 dark:text-purple-400">{mad(tot_tpe)} DH</div>
                <span class="text-[10px] font-black uppercase text-slate-400 mt-1 block">Total TPE / Cartes</span>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-teal-500 shadow-xs text-center">
                <div class="text-xl font-black font-mono text-teal-600 dark:text-teal-400">{mad(tot_especes)} DH</div>
                <span class="text-[10px] font-black uppercase text-slate-400 mt-1 block">Total Espèces</span>
            </div>
        </div>

        <!-- SYNTHÈSE PAR JOUR -->
        <div class="bg-white dark:bg-[#0E1B26] rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs overflow-hidden">
            <div class="px-4 py-3 border-b border-slate-100 dark:border-[#183042] flex items-center justify-between">
                <h3 class="text-xs font-black uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
                    <i data-lucide="calendar" class="w-4 h-4 text-sky-500"></i>
                    Évolution Quotidienne des Ventes
                </h3>
                <span class="text-[11px] text-slate-400 font-semibold">{len(lignes_jours)} jours répertoriés</span>
            </div>

            <div class="overflow-x-auto max-h-[550px]">
                <table class="w-full text-left">
                    <thead class="bg-slate-50 dark:bg-[#070E15] text-[10px] font-black uppercase text-slate-400 sticky top-0 border-b border-slate-200 dark:border-[#183042]">
                        <tr>
                            <th class="py-2.5 px-4">Date</th>
                            <th class="py-2.5 px-4 text-center">Ventes</th>
                            <th class="py-2.5 px-4 text-right">Diesel (L)</th>
                            <th class="py-2.5 px-4 text-right">SSP (L)</th>
                            <th class="py-2.5 px-4 text-right">Total (DH)</th>
                            <th class="py-2.5 px-4 text-right">TPE</th>
                            <th class="py-2.5 px-4 text-right">Espèces</th>
                            <th class="py-2.5 px-4 text-center">Détails</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 dark:divide-[#183042]/50">
                        {tableau_jours_html}
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <!-- ============================================================================== -->
    <!-- MODALE PROFESSIONNELLE AVEC FILTRES MODERNES PAR HEURE & CARBURANT -->
    <!-- ============================================================================== -->
    <div id="modal-tirages" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 hidden transition-all">
        
        <!-- CONTENEUR MODALE -->
        <div id="modal-box" class="bg-[#0A1622] border border-[#1b3449] rounded-2xl w-full max-w-5xl h-[88vh] flex flex-col shadow-2xl overflow-hidden transition-all duration-200">
            
            <!-- 1. EN-TÊTE : TITRE | DATE CENTRÉE BIEN VISIBLE | ACTIONS -->
            <div class="px-5 py-3 border-b border-[#1b3449] bg-[#071018] flex items-center justify-between shrink-0">
                
                <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-lg bg-amber-500/15 text-amber-400 flex items-center justify-center font-bold">
                        <i data-lucide="fuel" class="w-4 h-4"></i>
                    </div>
                    <span class="font-black text-xs uppercase tracking-wider text-slate-200">
                        Détails Tirages
                    </span>
                </div>

                <!-- Date au centre très visible -->
                <div class="px-4 py-1.5 rounded-xl bg-sky-500/15 border border-sky-400/30 flex items-center gap-2 shadow-xs">
                    <i data-lucide="calendar" class="w-4 h-4 text-sky-400"></i>
                    <span id="modal-date-titre" class="text-sm font-black font-mono tracking-widest text-sky-300">
                        ----/--/--
                    </span>
                </div>

                <div class="flex items-center gap-2">
                    <button type="button" onclick="toggleAgrandirModal()" title="Agrandir / Réduire" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 flex items-center justify-center cursor-pointer transition">
                        <i id="icon-maximize" data-lucide="maximize-2" class="w-4 h-4"></i>
                    </button>
                    <button type="button" onclick="fermerModalTirages()" title="Fermer" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-rose-500/20 hover:text-rose-400 text-slate-300 flex items-center justify-center cursor-pointer transition">
                        <i data-lucide="x" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <!-- 2. NOUVELLE BARRE DE FILTRES DESIGN : CARBURANT + CRÉNEAUX HEURES -->
            <div class="px-5 py-3 bg-[#0d1d2c] border-b border-[#1b3449] flex flex-wrap items-center justify-between gap-3 shrink-0">
                
                <!-- Filtre Carburant (Pills Segmentées) -->
                <div class="flex items-center gap-1.5 bg-[#071018] p-1 rounded-xl border border-[#1e3a52]">
                    <span class="text-[10px] font-black uppercase text-slate-400 px-2">Carb:</span>
                    <button type="button" onclick="setFiltreCarb('TOUS')" id="btn-carb-TOUS" class="btn-carb-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition bg-amber-500 text-slate-950">Tous</button>
                    <button type="button" onclick="setFiltreCarb('DIESEL')" id="btn-carb-DIESEL" class="btn-carb-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white">Diesel</button>
                    <button type="button" onclick="setFiltreCarb('SSP')" id="btn-carb-SSP" class="btn-carb-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white">SSP</button>
                </div>

                <!-- Filtre par Heure (Créneaux de Station / Quarts) -->
                <div class="flex items-center gap-1.5 bg-[#071018] p-1 rounded-xl border border-[#1e3a52]">
                    <span class="text-[10px] font-black uppercase text-slate-400 px-2 flex items-center gap-1">
                        <i data-lucide="clock" class="w-3 h-3 text-sky-400"></i> Quarts:
                    </span>
                    <button type="button" onclick="setFiltreQuart('TOUS')" id="btn-quart-TOUS" class="btn-quart-pill px-2.5 py-1 rounded-lg text-xs font-bold transition bg-sky-500 text-slate-950">24h</button>
                    <button type="button" onclick="setFiltreQuart('MATIN')" id="btn-quart-MATIN" class="btn-quart-pill px-2.5 py-1 rounded-lg text-xs font-bold transition text-slate-300 hover:text-white" title="06:00 à 14:00">06h-14h</button>
                    <button type="button" onclick="setFiltreQuart('SOIR')" id="btn-quart-SOIR" class="btn-quart-pill px-2.5 py-1 rounded-lg text-xs font-bold transition text-slate-300 hover:text-white" title="14:00 à 22:00">14h-22h</button>
                    <button type="button" onclick="setFiltreQuart('NUIT')" id="btn-quart-NUIT" class="btn-quart-pill px-2.5 py-1 rounded-lg text-xs font-bold transition text-slate-300 hover:text-white" title="22:00 à 06:00">22h-06h</button>
                </div>

                <!-- Recherche d'heure spécifique (ex: 14:25 ou 15) -->
                <div class="relative w-36 sm:w-44">
                    <input type="text" id="filtre-heure-libre" oninput="appliquerTousLesFiltres()" placeholder="Heure précise..." 
                           class="w-full bg-[#071018] border border-[#1e3a52] rounded-xl px-3 py-1.5 text-xs font-mono font-bold text-sky-300 placeholder-slate-500 outline-none focus:border-sky-400">
                </div>

            </div>

            <!-- 3. PETIT BANDEAU DE STATS DYNAMIQUES DU FILTRE EN COURS -->
            <div class="px-5 py-2 bg-[#091520] border-b border-[#1b3449]/70 flex items-center justify-between text-[11px] font-bold text-slate-400 shrink-0">
                <span id="modal-compteur" class="text-sky-400 font-mono">0 tirage(s)</span>
                <div class="flex items-center gap-4 font-mono">
                    <span>Volume: <strong id="modal-tot-vol" class="text-slate-100 font-black">0,00 L</strong></span>
                    <span>Total: <strong id="modal-tot-mnt" class="text-white font-black">0,00 DH</strong></span>
                </div>
            </div>

            <!-- 4. TABLEAU DES TIRAGES (EN-TÊTES AGRANDIS, BLANCS & VISIBLES) -->
            <div class="flex-1 overflow-y-auto bg-[#071018]">
                <div id="modal-loading" class="text-center py-20 text-xs text-slate-400 animate-pulse">
                    Chargement des tirages en cours...
                </div>

                <table id="modal-table" class="w-full text-left border-collapse hidden">
                    
                    <!-- EN-TÊTE DU TABLEAU : TAILLE AGRANDIE, COULEUR BLANCHE ÉCLATANTE -->
                    <thead class="bg-[#122435] sticky top-0 z-20 border-b-2 border-[#1E3A52] shadow-sm">
                        <tr class="text-[12px] sm:text-[13px] font-black uppercase text-white tracking-wider">
                            <th class="py-3 px-4 text-sky-300">Heure</th>
                            <th class="py-3 px-4 text-white">N° Vente</th>
                            <th class="py-3 px-4 text-white">Pompe</th>
                            <th class="py-3 px-4 text-white">Carburant</th>
                            <th class="py-3 px-4 text-right text-white">Volume</th>
                            <th class="py-3 px-4 text-right text-white">Montant</th>
                            <th class="py-3 px-4 text-right text-purple-300">TPE</th>
                            <th class="py-3 px-4 text-right text-teal-300">Espèces</th>
                        </tr>
                    </thead>
                    
                    <tbody id="modal-tbody" class="divide-y divide-[#183042]/50 text-xs font-semibold text-slate-200">
                    </tbody>
                </table>
            </div>

        </div>
    </div>

    <!-- SCRIPTS DES FILTRES INTERACTIFS ET DU PLEIN ÉCRAN -->
    <script>
        let toutesLesLignesJour = [];
        let filtreActifCarb = 'TOUS';
        let filtreActifQuart = 'TOUS';
        let estPleinEcran = false;

        async function ouvrirModalTirages(dateJour) {{
            const modal = document.getElementById('modal-tirages');
            const titre = document.getElementById('modal-date-titre');
            const loading = document.getElementById('modal-loading');
            const table = document.getElementById('modal-table');
            const inputHeure = document.getElementById('filtre-heure-libre');

            titre.innerText = dateJour;
            inputHeure.value = '';
            
            // Réinitialiser les boutons de filtres
            resetFiltresUI();

            loading.classList.remove('hidden');
            table.classList.add('hidden');
            modal.classList.remove('hidden');

            try {{
                const res = await fetch(`/api/rapport/jour-details?date_jour=${{dateJour}}`);
                const data = await res.json();
                
                if (data.status === 'success' && data.lignes) {{
                    toutesLesLignesJour = data.lignes;
                    appliquerTousLesFiltres();
                    loading.classList.add('hidden');
                    table.classList.remove('hidden');
                }}
            }} catch(e) {{
                loading.innerText = "Erreur de chargement des tirages.";
            }}
        }}

        function resetFiltresUI() {{
            filtreActifCarb = 'TOUS';
            filtreActifQuart = 'TOUS';
            majBoutonsCarb();
            majBoutonsQuart();
        }}

        function setFiltreCarb(carb) {{
            filtreActifCarb = carb;
            majBoutonsCarb();
            appliquerTousLesFiltres();
        }}

        function majBoutonsCarb() {{
            document.querySelectorAll('.btn-carb-pill').forEach(btn => {{
                btn.className = "btn-carb-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white";
            }});
            const actif = document.getElementById('btn-carb-' + filtreActifCarb);
            if (actif) actif.className = "btn-carb-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition bg-amber-500 text-slate-950 shadow-sm";
        }}

        function setFiltreQuart(quart) {{
            filtreActifQuart = quart;
            majBoutonsQuart();
            appliquerTousLesFiltres();
        }}

        function majBoutonsQuart() {{
            document.querySelectorAll('.btn-quart-pill').forEach(btn => {{
                btn.className = "btn-quart-pill px-2.5 py-1 rounded-lg text-xs font-bold transition text-slate-300 hover:text-white";
            }});
            const actif = document.getElementById('btn-quart-' + filtreActifQuart);
            if (actif) actif.className = "btn-quart-pill px-2.5 py-1 rounded-lg text-xs font-bold transition bg-sky-500 text-slate-950 shadow-sm";
        }}

        function appliquerTousLesFiltres() {{
            let res = toutesLesLignesJour;

            // 1. Filtre par Carburant
            if (filtreActifCarb !== 'TOUS') {{
                res = res.filter(l => l.carb.toUpperCase() === filtreActifCarb);
            }}

            // 2. Filtre par Créneaux / Quarts
            if (filtreActifQuart === 'MATIN') {{
                res = res.filter(l => {{
                    const h = parseInt(l.heure.split(':')[0], 10);
                    return h >= 6 && h < 14;
                }});
            }} else if (filtreActifQuart === 'SOIR') {{
                res = res.filter(l => {{
                    const h = parseInt(l.heure.split(':')[0], 10);
                    return h >= 14 && h < 22;
                }});
            }} else if (filtreActifQuart === 'NUIT') {{
                res = res.filter(l => {{
                    const h = parseInt(l.heure.split(':')[0], 10);
                    return h >= 22 || h < 6;
                }});
            }}

            // 3. Filtre par heure libre
            const heureLibre = document.getElementById('filtre-heure-libre').value.trim().toLowerCase();
            if (heureLibre) {{
                res = res.filter(l => l.heure.toLowerCase().includes(heureLibre));
            }}

            afficherLignes(res);
        }}

        function afficherLignes(lignes) {{
            const tbody = document.getElementById('modal-tbody');
            const compteur = document.getElementById('modal-compteur');
            const totVol = document.getElementById('modal-tot-vol');
            const totMnt = document.getElementById('modal-tot-mnt');

            compteur.innerText = `${{lignes.length}} tirage(s)`;

            let sommeVol = 0;
            let sommeMnt = 0;

            if (lignes.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="8" class="text-center py-12 text-slate-500 italic font-bold">Aucun tirage correspondant aux filtres.</td></tr>';
                totVol.innerText = '0,00 L';
                totMnt.innerText = '0,00 DH';
                return;
            }}

            let html = '';
            lignes.forEach(l => {{
                sommeVol += l.vol_raw;
                sommeMnt += l.mnt_raw;

                html += `
                <tr class="hover:bg-white/[0.04] transition-colors border-b border-[#183042]/40">
                    <td class="py-2.5 px-4 font-mono font-bold text-sky-400 text-xs">${{l.heure}}</td>
                    <td class="py-2.5 px-4 font-mono text-slate-300">#${{l.sale_id}}</td>
                    <td class="py-2.5 px-4 font-bold text-slate-200">${{l.pump}}</td>
                    <td class="py-2.5 px-4 font-black ${{l.carb === 'SSP' ? 'text-amber-400' : 'text-emerald-400'}}">${{l.carb}}</td>
                    <td class="py-2.5 px-4 text-right font-mono font-bold text-slate-100">${{l.vol}} L</td>
                    <td class="py-2.5 px-4 text-right font-mono font-black text-white">${{l.mnt}} DH</td>
                    <td class="py-2.5 px-4 text-right font-mono font-bold text-purple-400">${{l.tpe}} DH</td>
                    <td class="py-2.5 px-4 text-right font-mono font-bold text-teal-400">${{l.esp}} DH</td>
                </tr>
                `;
            }});

            tbody.innerHTML = html;
            totVol.innerText = sommeVol.toLocaleString('fr-FR', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) + ' L';
            totMnt.innerText = sommeMnt.toLocaleString('fr-FR', {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) + ' DH';
        }}

        function toggleAgrandirModal() {{
            const box = document.getElementById('modal-box');
            const icon = document.getElementById('icon-maximize');
            estPleinEcran = !estPleinEcran;

            if (estPleinEcran) {{
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

        function fermerModalTirages() {{
            document.getElementById('modal-tirages').classList.add('hidden');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') fermerModalTirages();
        }});
    </script>
    """
    return HTMLResponse(layout(content, active_tab="centre_rapports", request=request))