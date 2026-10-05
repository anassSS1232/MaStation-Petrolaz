# pages/rapport_compteurs.py
import json
from datetime import datetime
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse

from ui_utils import layout
from database import get_db_connection, init_db
from fusion_reader import parse_fusion_transactions, parse_fusion_text

router = APIRouter()

@router.post("/rapport-quart/import-fusion")
async def import_fusion(file: UploadFile = File(...)):
    try:
        content = await file.read()
        res = parse_fusion_transactions(content)
        return JSONResponse({"status": "success", "indexes": res["indexes"], "transactions": res["transactions"]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

@router.post("/rapport-quart/parse-clipboard")
async def parse_clipboard(request: Request):
    try:
        data = await request.json()
        res = parse_fusion_text(data.get("text", ""))
        return JSONResponse({"status": "success", "indexes": res["indexes"], "transactions": res["transactions"]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

@router.post("/rapport-quart/save-pompes")
async def save_pompes(request: Request):
    try:
        init_db()
        data = await request.json()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_jour = datetime.now().strftime("%Y-%m-%d")

        conn = get_db_connection()
        cursor = conn.cursor()

        for item in data.get("compteurs", []):
            cursor.execute("""
                INSERT INTO compteurs (date, type, pompe_id, index_val) 
                VALUES (?, ?, ?, ?)
            """, (now, str(item.get("type")), int(item.get("pompe_id")), float(item.get("index_val", 0.0))))

        trans_rows = [
            (
                date_jour,
                str(t.get("sale_id", "")),
                str(t.get("date", t.get("end_date", date_jour))),
                str(t.get("heure", t.get("end_time", ""))),
                int(t.get("pump_id", 0)),
                str(t.get("type", "")),
                str(t.get("carburant", "")),
                float(t.get("volume", 0.0)),
                float(t.get("money", 0.0)),
                float(t.get("initial_vol", 0.0)),
                float(t.get("final_vol", 0.0))
            )
            for t in data.get("transactions", [])
        ]

        if trans_rows:
            cursor.executemany("""
                INSERT INTO transactions_jour (
                    date_releve, sale_id, date_vente, heure, pump_id, type, carburant, volume, money, initial_vol, final_vol
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, trans_rows)

        conn.commit()
        conn.close()
        return JSONResponse({"status": "success", "message": f"{len(trans_rows)} transactions enregistrées !"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@router.get("/rapport-quart/compteurs", response_class=HTMLResponse)
async def page_compteurs(request: Request):
    init_db()
    conn = get_db_connection()
    today_str = datetime.now().strftime("%d/%m/%Y")
    today_sql = datetime.now().strftime("%Y-%m-%d")

    p_ssp = conn.execute("SELECT prix FROM prix_vente WHERE produit IN ('SSP', 'Essence', 'Sans Plomb') AND statut='ACTIF' ORDER BY id DESC LIMIT 1").fetchone()
    p_go = conn.execute("SELECT prix FROM prix_vente WHERE produit IN ('GO', 'Diesel', 'Gasoil 10') AND statut='ACTIF' ORDER BY id DESC LIMIT 1").fetchone()
    prix_ssp = float(p_ssp['prix']) if p_ssp else 15.340
    prix_go = float(p_go['prix']) if p_go else 14.280

    pompes_ssp = [1, 2, 3, 4, 6, 8]
    pompes_go = [1, 2, 3, 4, 5, 7]

    def get_pump_day_stats(c_type, p_id):
        try:
            types_comp = ('ESS', 'SSP') if c_type in ('ESS', 'SSP') else ('DIE', 'GO')
            row = conn.execute("""
                SELECT SUM(volume) as total_vol, MIN(NULLIF(initial_vol, 0)) as min_init, MAX(final_vol) as max_fin
                FROM transactions_jour 
                WHERE date_releve = ? AND type IN (?, ?) AND pump_id = ?
            """, (today_sql, types_comp[0], types_comp[1], p_id)).fetchone()

            vol = float(row['total_vol']) if (row and row['total_vol'] is not None) else 0.00
            last_idx = conn.execute(
                "SELECT index_val FROM compteurs WHERE type IN (?, ?) AND pompe_id=? ORDER BY id DESC LIMIT 1",
                (types_comp[0], types_comp[1], p_id)
            ).fetchone()
            fb_idx = float(last_idx['index_val']) if last_idx and last_idx['index_val'] else 0.00
            init_v = float(row['min_init']) if (row and row['min_init']) else (fb_idx - vol if fb_idx > 0 else 0.00)
            fin_v = float(row['max_fin']) if (row and row['max_fin']) else fb_idx
            return vol, max(0.00, init_v), fin_v
        except Exception:
            return 0.00, 0.00, 0.00

    stats_ssp = {p: get_pump_day_stats('SSP', p) for p in pompes_ssp}
    stats_go = {p: get_pump_day_stats('GO', p) for p in pompes_go}
    total_ssp_l = sum(stats_ssp[p][0] for p in pompes_ssp)
    total_go_l = sum(stats_go[p][0] for p in pompes_go)
    total_fusion_theorique = (total_ssp_l * prix_ssp) + (total_go_l * prix_go)

    raw_trans = conn.execute("""
        SELECT id, date_releve, COALESCE(NULLIF(date_vente, ''), date_releve) as date_v,
               heure, sale_id, pump_id, type, carburant, volume, money, initial_vol, final_vol 
        FROM transactions_jour ORDER BY id DESC LIMIT 1500
    """).fetchall()

    transactions_list = [{
        "id": r["id"], "date": r["date_v"], "heure": r["heure"], "sale_id": r["sale_id"], "pump_id": r["pump_id"],
        "type": "SSP" if r["type"] in ["ESS", "SSP"] else "GO",
        "carburant": "SSP" if ("SSP" in str(r["carburant"]).upper() or "ESS" in str(r["carburant"]).upper()) else "GO",
        "volume": float(r["volume"] or 0.0), "money": float(r["money"] or 0.0),
        "initial_vol": float(r["initial_vol"] or 0.0), "final_vol": float(r["final_vol"] or 0.0)
    } for r in raw_trans]

    conn.close()

    content = f"""
    <script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
    <input type="file" id="fusionFileInput" accept=".xls,.xlsx,.csv,.txt,.xml" class="hidden" onchange="uploadFusionFile(event)" />

    <div class="h-full flex flex-col gap-2.5 animate-in fade-in duration-200">
        <!-- BARRE DU HAUT -->
        <div class="flex flex-col md:flex-row justify-between items-stretch md:items-center bg-white dark:bg-[#0E1B26] p-2.5 rounded-xl border border-slate-200/80 dark:border-[#183042] shadow-xs gap-2 shrink-0">
            <div class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-lg bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-[#38BDF8] flex items-center justify-center border border-sky-200 dark:border-sky-500/20 shrink-0">
                    <i data-lucide="gauge" class="w-3.5 h-3.5"></i>
                </div>
                <div>
                    <h1 class="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">Compteurs Pompes</h1>
                    <p class="text-[9.5px] text-slate-400 font-mono">{today_str}</p>
                </div>
            </div>

            <!-- FILTRE SECTEUR -->
            <div class="flex items-center justify-between sm:justify-center gap-1.5">
                <div class="flex items-center bg-slate-100 dark:bg-[#070E15] p-0.5 rounded-lg border border-slate-200 dark:border-[#183042] text-xs">
                    <button onclick="changerVueSecteur('ALL')" id="btn-vue-all" class="px-2.5 py-0.5 rounded-md font-bold text-slate-900 dark:text-white bg-white dark:bg-[#184E68] shadow-xs transition text-[11px]">
                        Tous (12)
                    </button>
                    <button onclick="changerVueSecteur('SSP')" id="btn-vue-ssp" class="px-2.5 py-0.5 rounded-md font-bold text-slate-500 dark:text-slate-400 hover:text-emerald-500 transition flex items-center gap-1 text-[11px]">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> SSP
                    </button>
                    <button onclick="changerVueSecteur('GO')" id="btn-vue-go" class="px-2.5 py-0.5 rounded-md font-bold text-slate-500 dark:text-slate-400 hover:text-amber-500 transition flex items-center gap-1 text-[11px]">
                        <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span> GO
                    </button>
                </div>

                <div class="hidden sm:flex items-center gap-1.5 bg-slate-50 dark:bg-[#070E15] px-2.5 py-0.5 rounded-lg border border-slate-200 dark:border-[#183042] font-mono text-[11px]">
                    <span class="text-slate-400 font-sans">Vendu:</span>
                    <span class="text-slate-900 dark:text-white font-black">{(total_ssp_l + total_go_l):,.2f} L</span>
                    <span class="text-slate-300 dark:text-slate-700">|</span>
                    <span class="text-emerald-600 dark:text-[#00F5A0] font-black">{total_fusion_theorique:,.2f} DH</span>
                </div>
            </div>

            <!-- BOUTONS ACTIONS -->
            <div class="flex items-center gap-1">
                <button onclick="toggleModalHistorique(true)" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-[#070E15] dark:hover:bg-[#183042] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-[#183042] text-[11px] font-bold transition">
                    <i data-lucide="history" class="w-3 h-3 text-sky-500"></i> Historique
                </button>
                <button onclick="ouvrirModalColler()" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-[#070E15] dark:hover:bg-[#183042] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-[#183042] text-[11px] font-bold transition">
                    <i data-lucide="clipboard-paste" class="w-3 h-3 text-emerald-500"></i> Coller
                </button>
                <button onclick="document.getElementById('fusionFileInput').click()" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#184E68] hover:bg-sky-700 text-white text-[11px] font-black uppercase tracking-wider transition shadow-xs">
                    <i data-lucide="file-up" class="w-3 h-3"></i> Importer
                </button>
            </div>
        </div>

        <!-- GRILLES DES POMPES -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-2.5 flex-1 pb-2 overflow-y-auto" id="container-grilles">
            <!-- SECTEUR SSP -->
            <div id="secteur-ssp" class="bg-white dark:bg-[#0E1B26] p-2.5 rounded-xl border border-slate-200 dark:border-[#183042] flex flex-col justify-between shadow-xs">
                <div class="flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-100 dark:border-[#183042]">
                    <div class="flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                        <h2 class="font-black text-slate-900 dark:text-white text-[11px] uppercase">Super Sans Plomb (SSP)</h2>
                        <span class="text-[10px] font-bold text-emerald-600 dark:text-[#00F5A0] bg-emerald-50 dark:bg-emerald-500/10 px-1.5 py-0.2 rounded font-mono">
                            {total_ssp_l:,.2f} L
                        </span>
                    </div>
                    <span class="text-[10px] font-mono text-slate-500">Tarif : <b class="text-emerald-600 dark:text-[#00F5A0]">{prix_ssp:.3f}</b> MAD/L</span>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 flex-1">
                    {"".join([f'''
                    <div class="bg-slate-50 dark:bg-[#070E15] border border-slate-200 dark:border-[#183042] p-2 rounded-lg transition flex flex-col justify-between { "opacity-50" if stats_ssp[p][0] == 0 else "" }">
                        <div class="flex justify-between items-center">
                            <span class="text-[11px] font-black text-slate-800 dark:text-slate-200 uppercase">POMPE {p}</span>
                            <span class="text-[8.5px] font-bold text-emerald-600 dark:text-[#00F5A0] px-1 py-0.2 rounded font-mono">SSP</span>
                        </div>
                        <div class="my-1.5 text-center">
                            <div class="text-base font-black text-slate-900 dark:text-white font-mono">{stats_ssp[p][0]:,.2f} <span class="text-[9px] text-slate-400 font-sans">L</span></div>
                            <div class="text-[11px] font-bold text-emerald-600 dark:text-[#00F5A0] font-mono">{(stats_ssp[p][0] * prix_ssp):,.2f} DH</div>
                        </div>
                        <div class="text-[9px] font-mono text-slate-400 text-center border-t border-slate-200 dark:border-[#183042] pt-1 flex justify-center items-center gap-1">
                            <span>{stats_ssp[p][1]:,.1f}</span> ➔ <span class="text-slate-800 dark:text-slate-200 font-bold">{stats_ssp[p][2]:,.1f}</span>
                        </div>
                    </div>
                    ''' for p in pompes_ssp])}
                </div>
            </div>

            <!-- SECTEUR DIESEL GO -->
            <div id="secteur-go" class="bg-white dark:bg-[#0E1B26] p-2.5 rounded-xl border border-slate-200 dark:border-[#183042] flex flex-col justify-between shadow-xs">
                <div class="flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-100 dark:border-[#183042]">
                    <div class="flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-amber-500"></span>
                        <h2 class="font-black text-slate-900 dark:text-white text-[11px] uppercase">Diesel (Gasoil 10)</h2>
                        <span class="text-[10px] font-bold text-amber-600 dark:text-[#E5A842] bg-amber-50 dark:bg-amber-500/10 px-1.5 py-0.2 rounded font-mono">
                            {total_go_l:,.2f} L
                        </span>
                    </div>
                    <span class="text-[10px] font-mono text-slate-500">Tarif : <b class="text-amber-600 dark:text-[#E5A842]">{prix_go:.3f}</b> MAD/L</span>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 flex-1">
                    {"".join([f'''
                    <div class="bg-slate-50 dark:bg-[#070E15] border border-slate-200 dark:border-[#183042] p-2 rounded-lg transition flex flex-col justify-between { "opacity-50" if stats_go[p][0] == 0 else "" }">
                        <div class="flex justify-between items-center">
                            <span class="text-[11px] font-black text-slate-800 dark:text-slate-200 uppercase">POMPE {p}</span>
                            <span class="text-[8.5px] font-bold text-amber-600 dark:text-[#E5A842] px-1 py-0.2 rounded font-mono">GO</span>
                        </div>
                        <div class="my-1.5 text-center">
                            <div class="text-base font-black text-slate-900 dark:text-white font-mono">{stats_go[p][0]:,.2f} <span class="text-[9px] text-slate-400 font-sans">L</span></div>
                            <div class="text-[11px] font-bold text-amber-600 dark:text-[#E5A842] font-mono">{(stats_go[p][0] * prix_go):,.2f} DH</div>
                        </div>
                        <div class="text-[9px] font-mono text-slate-400 text-center border-t border-slate-200 dark:border-[#183042] pt-1 flex justify-center items-center gap-1">
                            <span>{stats_go[p][1]:,.1f}</span> ➔ <span class="text-slate-800 dark:text-slate-200 font-bold">{stats_go[p][2]:,.1f}</span>
                        </div>
                    </div>
                    ''' for p in pompes_go])}
                </div>
            </div>
        </div>
    </div>

    <!-- MODALE HISTORIQUE TRANSACTIONS -->
    <div id="modalHistorique" class="fixed inset-0 bg-slate-900/40 dark:bg-black/80 backdrop-blur-xs hidden z-50 flex items-center justify-center p-2 sm:p-4">
        <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] w-full max-w-5xl h-[85vh] rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            <div class="p-2.5 sm:p-3 border-b border-slate-200 dark:border-[#183042] bg-slate-50 dark:bg-[#070E15] flex flex-col gap-2 shrink-0">
                <div class="flex justify-between items-center">
                    <h3 class="font-black text-slate-900 dark:text-white text-xs uppercase tracking-wider">Historique des Transactions Pompes</h3>
                    <button onclick="toggleModalHistorique(false)" class="w-7 h-7 rounded-lg bg-slate-200 dark:bg-white/10 flex items-center justify-center text-slate-600 dark:text-slate-300 font-bold text-xs">✕</button>
                </div>

                <div class="flex flex-wrap items-center gap-1.5">
                    <div class="flex items-center gap-1 bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#183042] px-2 py-1 rounded-lg">
                        <span class="text-[9px] font-bold text-slate-400 uppercase">Date:</span>
                        <input type="date" id="filtreDateModal" oninput="filtrerHistoriqueRapide()" class="bg-transparent text-slate-900 dark:text-white text-xs outline-none font-mono">
                    </div>
                    <div class="flex items-center gap-1 bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#183042] px-2 py-1 rounded-lg">
                        <span class="text-[9px] font-bold text-slate-400 uppercase">Heure:</span>
                        <input type="time" id="filtreHeureDebut" oninput="filtrerHistoriqueRapide()" class="bg-transparent text-sky-500 text-xs outline-none font-mono">
                        <span class="text-slate-400 text-xs">-</span>
                        <input type="time" id="filtreHeureFin" oninput="filtrerHistoriqueRapide()" class="bg-transparent text-sky-500 text-xs outline-none font-mono">
                    </div>
                    <div class="flex items-center gap-1 bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#183042] px-2 py-1 rounded-lg">
                        <span class="text-[9px] font-bold text-slate-400 uppercase">Pompe:</span>
                        <select id="filtrePompeModal" onchange="filtrerHistoriqueRapide()" class="bg-transparent text-slate-900 dark:text-white text-xs outline-none font-bold">
                            <option value="ALL" class="bg-white dark:bg-[#0E1B26]">Toutes</option>
                            <optgroup label="Super Sans Plomb (SSP)" class="bg-white dark:bg-[#0E1B26]">
                                {"".join([f'<option value="SSP_{p}">Pompe {p} (SSP)</option>' for p in pompes_ssp])}
                            </optgroup>
                            <optgroup label="Diesel (GO)" class="bg-white dark:bg-[#0E1B26]">
                                {"".join([f'<option value="GO_{p}">Pompe {p} (GO)</option>' for p in pompes_go])}
                            </optgroup>
                        </select>
                    </div>
                    <button onclick="reinitialiserFiltres()" title="Réinitialiser" class="p-1.5 bg-slate-100 dark:bg-[#070E15] text-slate-600 dark:text-slate-300 rounded-lg border border-slate-200 dark:border-[#183042]">
                        <i data-lucide="rotate-ccw" class="w-3 h-3"></i>
                    </button>
                </div>
            </div>

            <div class="flex-1 overflow-auto p-2">
                <table class="w-full text-left text-xs min-w-[650px]">
                    <thead class="bg-slate-50 dark:bg-[#070E15] text-[9.5px] uppercase font-bold text-slate-400 sticky top-0 border-b border-slate-200 dark:border-[#183042]">
                        <tr>
                            <th class="py-2 px-2.5">Date</th>
                            <th class="py-2 px-2.5">Heure</th>
                            <th class="py-2 px-2.5">N° Vente</th>
                            <th class="py-2 px-2.5">Pompe</th>
                            <th class="py-2 px-2.5">Carburant</th>
                            <th class="py-2 px-2.5 text-right">Vol. Initial</th>
                            <th class="py-2 px-2.5 text-right">Vol. Final</th>
                            <th class="py-2 px-2.5 text-right text-slate-900 dark:text-white font-bold">Vendu (L)</th>
                            <th class="py-2 px-2.5 text-right text-emerald-600 dark:text-[#00F5A0] font-bold">Montant (DH)</th>
                        </tr>
                    </thead>
                    <tbody id="modalHistoriqueTableBody" class="divide-y divide-slate-100 dark:divide-[#183042]/50 font-mono text-[11px]"></tbody>
                </table>
            </div>

            <div class="p-2.5 border-t border-slate-200 dark:border-[#183042] bg-slate-50 dark:bg-[#070E15] flex justify-between items-center shrink-0">
                <div class="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                    Volume : <span id="totalVolumeFiltre" class="font-black text-slate-900 dark:text-white">0.00 L</span> | 
                    Montant : <span id="totalMontantFiltre" class="font-black text-emerald-600 dark:text-[#00F5A0]">0.00 DH</span>
                </div>
                <button onclick="toggleModalHistorique(false)" class="px-3 py-1 rounded-lg bg-slate-200 dark:bg-slate-800 text-xs font-bold">Fermer</button>
            </div>
        </div>
    </div>

    <!-- MODALE COLLER EXCEL -->
    <div id="modalCollerExcel" class="fixed inset-0 bg-slate-900/40 dark:bg-black/80 backdrop-blur-xs hidden z-50 flex items-center justify-center p-3">
        <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] w-full max-w-lg rounded-xl p-3.5 shadow-2xl flex flex-col gap-2.5">
            <div class="flex justify-between items-center pb-1.5 border-b border-slate-100 dark:border-[#183042]">
                <h3 class="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">Coller Données Fusion / Excel</h3>
                <button onclick="fermerModalColler()" class="text-slate-400 hover:text-white font-bold text-xs">✕</button>
            </div>
            <textarea id="zoneColler" rows="6" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#183042] rounded-lg p-2.5 text-xs font-mono text-slate-900 dark:text-slate-200 outline-none" placeholder="Collez vos lignes de vente ici (Ctrl+V)..."></textarea>
            <div class="flex justify-end gap-1.5">
                <button onclick="fermerModalColler()" class="px-3 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 text-xs font-bold">Annuler</button>
                <button onclick="traiterZoneColler()" class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-black uppercase tracking-wider transition shadow-sm">Analyser & Sauvegarder</button>
            </div>
        </div>
    </div>

    <script>
        const TOUTES_LES_TRANSACTIONS = {json.dumps(transactions_list)};
        let transactionsFiltrees = [];
        let limiteAffichage = 100;

        function changerVueSecteur(vue) {{
            const ssp = document.getElementById('secteur-ssp');
            const go = document.getElementById('secteur-go');
            const grid = document.getElementById('container-grilles');
            const btnAll = document.getElementById('btn-vue-all');
            const btnSsp = document.getElementById('btn-vue-ssp');
            const btnGo = document.getElementById('btn-vue-go');

            btnAll.className = "px-2.5 py-0.5 rounded-md font-bold text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition text-[11px]";
            btnSsp.className = "px-2.5 py-0.5 rounded-md font-bold text-slate-500 dark:text-slate-400 hover:text-emerald-500 transition flex items-center gap-1 text-[11px]";
            btnGo.className = "px-2.5 py-0.5 rounded-md font-bold text-slate-500 dark:text-slate-400 hover:text-amber-500 transition flex items-center gap-1 text-[11px]";

            if (vue === 'ALL') {{
                ssp.classList.remove('hidden');
                go.classList.remove('hidden');
                grid.className = "grid grid-cols-1 lg:grid-cols-2 gap-2.5 flex-1 pb-2 overflow-y-auto";
                btnAll.className = "px-2.5 py-0.5 rounded-md font-bold text-slate-900 dark:text-white bg-white dark:bg-[#184E68] shadow-xs transition text-[11px]";
            }} else if (vue === 'SSP') {{
                ssp.classList.remove('hidden');
                go.classList.add('hidden');
                grid.className = "grid grid-cols-1 gap-2.5 flex-1 max-w-4xl mx-auto w-full pb-2 overflow-y-auto";
                btnSsp.className = "px-2.5 py-0.5 rounded-md font-bold text-emerald-600 dark:text-[#00F5A0] bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 shadow-xs transition flex items-center gap-1 text-[11px]";
            }} else if (vue === 'GO') {{
                ssp.classList.add('hidden');
                go.classList.remove('hidden');
                grid.className = "grid grid-cols-1 gap-2.5 flex-1 max-w-4xl mx-auto w-full pb-2 overflow-y-auto";
                btnGo.className = "px-2.5 py-0.5 rounded-md font-bold text-amber-600 dark:text-[#E5A842] bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 shadow-xs transition flex items-center gap-1 text-[11px]";
            }}
        }}

        function toggleModalHistorique(show) {{
            const m = document.getElementById('modalHistorique');
            if (show) {{
                m.classList.remove('hidden');
                document.body.style.overflow = 'hidden';
                limiteAffichage = 100;
                filtrerHistoriqueRapide();
            }} else {{
                m.classList.add('hidden');
                document.body.style.overflow = 'auto';
            }}
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function reinitialiserFiltres() {{
            document.getElementById('filtreDateModal').value = "";
            document.getElementById('filtreHeureDebut').value = "";
            document.getElementById('filtreHeureFin').value = "";
            document.getElementById('filtrePompeModal').value = "ALL";
            limiteAffichage = 100;
            filtrerHistoriqueRapide();
        }}

        function filtrerHistoriqueRapide() {{
            const fDate = document.getElementById('filtreDateModal').value;
            const fHeureDeb = document.getElementById('filtreHeureDebut').value;
            const fHeureFin = document.getElementById('filtreHeureFin').value;
            const fPompe = document.getElementById('filtrePompeModal').value;

            let sumVol = 0, sumMoney = 0;
            transactionsFiltrees = [];

            for (let i = 0; i < TOUTES_LES_TRANSACTIONS.length; i++) {{
                const t = TOUTES_LES_TRANSACTIONS[i];
                if (fDate) {{
                    const [y, m, d] = fDate.split('-');
                    const fDateFR = `${{d}}/${{m}}/${{y}}`;
                    if (t.date !== fDate && t.date !== fDateFR && !t.date.startsWith(fDate)) continue;
                }}
                if (t.heure) {{
                    const hSimple = t.heure.substring(0, 5);
                    if (fHeureDeb && hSimple < fHeureDeb) continue;
                    if (fHeureFin && hSimple > fHeureFin) continue;
                }}
                if (fPompe !== 'ALL') {{
                    const [cType, pId] = fPompe.split('_');
                    if (t.type !== cType || String(t.pump_id) !== pId) continue;
                }}
                transactionsFiltrees.push(t);
                sumVol += t.volume;
                sumMoney += t.money;
            }}

            document.getElementById('totalVolumeFiltre').innerText = sumVol.toLocaleString('fr-FR', {{minimumFractionDigits: 2}}) + ' L';
            document.getElementById('totalMontantFiltre').innerText = sumMoney.toLocaleString('fr-FR', {{minimumFractionDigits: 2}}) + ' DH';
            rendreTableauHistorique();
        }}

        function rendreTableauHistorique() {{
            const total = transactionsFiltrees.length;
            if (total === 0) {{
                document.getElementById('modalHistoriqueTableBody').innerHTML = `
                    <tr><td colspan="9" class="py-8 text-center text-slate-400 font-sans text-xs italic">Aucune transaction trouvée.</td></tr>
                `;
                return;
            }}

            let htmlRows = "";
            const limite = Math.min(limiteAffichage, total);
            for (let i = 0; i < limite; i++) {{
                const t = transactionsFiltrees[i];
                const badgeColor = t.type === 'SSP' 
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-500/10 dark:text-[#00F5A0]' 
                    : 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-500/10 dark:text-[#E5A842]';
                const moneyColor = t.type === 'SSP' ? 'text-emerald-600 dark:text-[#00F5A0]' : 'text-amber-600 dark:text-[#E5A842]';

                htmlRows += `
                <tr class="border-b border-slate-100 dark:border-[#183042]/50 hover:bg-slate-50/80 dark:hover:bg-white/[0.02]">
                    <td class="py-1.5 px-2.5 text-slate-600 dark:text-slate-400 font-medium">${{t.date}}</td>
                    <td class="py-1.5 px-2.5 text-sky-600 dark:text-[#38BDF8] font-semibold">${{t.heure}}</td>
                    <td class="py-1.5 px-2.5 font-bold text-slate-900 dark:text-slate-200">#${{t.sale_id}}</td>
                    <td class="py-1.5 px-2.5 text-slate-700 dark:text-slate-300 font-semibold">Pompe ${{t.pump_id}}</td>
                    <td class="py-1.5 px-2.5"><span class="text-[8.5px] font-black uppercase px-1.5 py-0.2 rounded-md ${{badgeColor}}">${{t.carburant}}</span></td>
                    <td class="py-1.5 px-2.5 text-right text-slate-400">${{t.initial_vol.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}}</td>
                    <td class="py-1.5 px-2.5 text-right text-slate-700 dark:text-slate-300 font-medium">${{t.final_vol.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}}</td>
                    <td class="py-1.5 px-2.5 text-right font-black text-slate-900 dark:text-white">${{t.volume.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}} L</td>
                    <td class="py-1.5 px-2.5 text-right font-black ${{moneyColor}}">${{t.money.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}} DH</td>
                </tr>
                `;
            }}
            document.getElementById('modalHistoriqueTableBody').innerHTML = htmlRows;
        }}

        function ouvrirModalColler() {{
            document.getElementById('zoneColler').value = "";
            document.getElementById('modalCollerExcel').classList.remove('hidden');
            setTimeout(() => document.getElementById('zoneColler').focus(), 100);
        }}

        function fermerModalColler() {{
            document.getElementById('modalCollerExcel').classList.add('hidden');
        }}

        async function traiterZoneColler() {{
            const rawText = document.getElementById('zoneColler').value;
            if (!rawText.trim()) return alert("Veuillez coller les données.");
            fermerModalColler();
            await envoyerTextePourTraitement(rawText);
        }}

        async function envoyerTextePourTraitement(text) {{
            try {{
                const res = await fetch('/rapport-quart/parse-clipboard', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ text: text }})
                }});
                const result = await res.json();
                if (res.ok && result.transactions && result.transactions.length > 0) {{
                    await sauvegarderDirectement(result.indexes, result.transactions);
                }} else {{
                    alert("⚠️ Aucune transaction exploitable trouvée.");
                }}
            }} catch (err) {{
                alert("❌ Erreur : " + err);
            }}
        }}

        async function uploadFusionFile(event) {{
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = async function(e) {{
                try {{
                    const data = new Uint8Array(e.target.result);
                    const workbook = XLSX.read(data, {{type: 'array'}});
                    const tsvText = XLSX.utils.sheet_to_csv(workbook.Sheets[workbook.SheetNames[0]], {{FS: "\\t"}});
                    await envoyerTextePourTraitement(tsvText);
                }} catch (err) {{
                    const tr = new FileReader();
                    tr.onload = async function(te) {{ await envoyerTextePourTraitement(te.target.result); }};
                    tr.readAsText(file, 'utf-8');
                }}
            }};
            reader.readAsArrayBuffer(file);
            event.target.value = "";
        }}

        async function sauvegarderDirectement(indexes, transactions) {{
            const compteurs = [];
            for (const [pId, val] of Object.entries(indexes.SSP || indexes.ESS || {{}})) {{
                compteurs.push({{ type: 'ESS', pompe_id: parseInt(pId), index_val: parseFloat(val) }});
            }}
            for (const [pId, val] of Object.entries(indexes.GO || indexes.DIE || {{}})) {{
                compteurs.push({{ type: 'DIE', pompe_id: parseInt(pId), index_val: parseFloat(val) }});
            }}

            try {{
                const response = await fetch('/rapport-quart/save-pompes', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ compteurs: compteurs, transactions: transactions }})
                }});
                const res = await response.json();
                alert(response.ok ? '✅ ' + res.message : '❌ ' + res.message);
                if (response.ok) window.location.reload();
            }} catch (err) {{
                alert('❌ Erreur de sauvegarde : ' + err);
            }}
        }}
    </script>
    """
    return HTMLResponse(layout(content, "compteurs", request=request))