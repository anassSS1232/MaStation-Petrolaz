# ==============================================================================
# FICHIER : pages/rapport_encaissements.py (CORRIGÉ & TESTÉ)
# ==============================================================================

import html
import json
import base64
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from database import get_db_connection
from ui_utils import layout

router = APIRouter()

def mad(val: float) -> str:
    try:
        return f"{float(val or 0.0):,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return "0,00"

def normaliser_date_iso(date_str: str) -> str:
    """Transforme n'importe quel format (DD/MM/YYYY ou YYYY-MM-DD) en YYYY-MM-DD pur."""
    if not date_str:
        return ""
    clean = str(date_str).strip().split(" ")[0]
    if "/" in clean:
        parts = clean.split("/")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    elif "-" in clean:
        parts = clean.split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            else:
                return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return clean

def formater_date_fr(date_str: str) -> str:
    iso = normaliser_date_iso(date_str)
    if not iso or len(iso) < 10:
        return date_str or "—"
    parts = iso.split("-")
    return f"{parts[2]}/{parts[1]}/{parts[0]}"

@router.get("/centre-rapports/encaissements", response_class=HTMLResponse)
async def page_rapport_encaissements(
    request: Request,
    client_id: Optional[str] = "ALL",
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None
):
    today = datetime.now()
    d_debut = date_debut or (today - timedelta(days=120)).strftime("%Y-%m-%d")
    d_fin = date_fin or today.strftime("%Y-%m-%d")

    conn = get_db_connection()
    
    # 1. Récupération des clients pour le select
    clients_rows = conn.execute("SELECT id, nom, code FROM clients ORDER BY nom ASC").fetchall()
    clients_options = '<option value="ALL">Tous les clients</option>'
    for c in clients_rows:
        c_nom = html.escape(c["nom"] or "")
        c_code = html.escape(c["code"] or "")
        clients_options += f'<option value="{c["id"]}">{c_nom} ({c_code})</option>'

    # 2. Récupération de tous les encaissements
    query = """
        SELECT e.*, 
               COALESCE(NULLIF(c.nom, ''), NULLIF(e.client_nom_libre, ''), 'Client Passager') as client_nom, 
               COALESCE(c.code, 'PASSAGER') as client_code
        FROM client_encaissements e
        LEFT JOIN clients c ON e.client_id = c.id
        ORDER BY e.date_paiement DESC, e.id DESC
    """
    rows = conn.execute(query).fetchall()
    conn.close()

    encaissements_list = []
    for r in rows:
        d_p = str(r["date_paiement"] or "")
        d_iso = normaliser_date_iso(d_p)
        
        m_raw = (r["mode_paiement"] or "Espèces").strip()
        m_lower = m_raw.lower()

        if "chèque" in m_lower or "cheque" in m_lower:
            m_norm = "Chèque"
        elif "vir" in m_lower:
            m_norm = "Virement"
        elif "tpe" in m_lower or "carte" in m_lower:
            m_norm = "Carte Bancaire / TPE"
        else:
            m_norm = "Espèces"

        st_val = (r["statut"] or "Validé").strip()

        encaissements_list.append({
            "id": r["id"],
            "client_id": str(r["client_id"] or 0),
            "date_iso": d_iso,
            "date_fr": formater_date_fr(d_p),
            "client_nom": r["client_nom"],
            "client_code": r["client_code"],
            "mode": m_norm,
            "reference": r["reference"] or "-",
            "montant": float(r["montant"] or 0.0),
            "statut": st_val,
            "banque": r["banque"] or "-",
            "description": r["description"] or "-"
        })

    # Encodage sécurisé en Base64 pour éliminer tout bug de parsing JS
    encaissements_b64 = base64.b64encode(json.dumps(encaissements_list).encode('utf-8')).decode('utf-8')

    content = f"""
    <div class="max-w-7xl mx-auto space-y-4 animate-in fade-in duration-150">
        
        <!-- 1. EN-TÊTE DU RAPPORT -->
        <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-[#183042]">
                <div class="flex items-center gap-2.5">
                    <div class="w-8 h-8 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center font-bold">
                        <i data-lucide="wallet" class="w-4 h-4"></i>
                    </div>
                    <h1 class="font-black text-slate-900 dark:text-white text-sm uppercase tracking-wider">
                        Rapport des Encaissements & Règlements
                    </h1>
                </div>

                <a href="/centre-rapports" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-[#132738] text-slate-700 dark:text-slate-200 text-xs font-bold transition">
                    <i data-lucide="arrow-left" class="w-3.5 h-3.5"></i>
                    <span>Retour Hub</span>
                </a>
            </div>

            <!-- FILTRES RESPONSIVES INSTANTANÉS -->
            <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
                <div class="sm:col-span-4">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Client</label>
                    <select id="filtreClient" onchange="filtrerDirect()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-2.5 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none">
                        {clients_options}
                    </select>
                </div>

                <div class="sm:col-span-2">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Mode de Paiement</label>
                    <select id="filtreMode" onchange="filtrerDirect()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-2.5 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none">
                        <option value="ALL">Tous les modes</option>
                        <option value="Espèces">Espèces</option>
                        <option value="Chèque">Chèque</option>
                        <option value="Virement">Virement</option>
                        <option value="Carte Bancaire / TPE">TPE / Carte</option>
                    </select>
                </div>

                <div class="sm:col-span-2">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Statut</label>
                    <select id="filtreStatut" onchange="filtrerDirect()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-2.5 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none">
                        <option value="ALL">Tous les statuts</option>
                        <option value="Validé">Validé</option>
                        <option value="En attente">En attente</option>
                    </select>
                </div>

                <div class="sm:col-span-2">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Date début</label>
                    <input type="date" id="filtreDateDebut" value="{d_debut}" onchange="filtrerDirect()" oninput="filtrerDirect()" 
                           class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-2.5 py-2 text-xs font-bold font-mono text-slate-900 dark:text-white outline-none cursor-pointer">
                </div>

                <div class="sm:col-span-2">
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Date fin</label>
                    <input type="date" id="filtreDateFin" value="{d_fin}" onchange="filtrerDirect()" oninput="filtrerDirect()" 
                           class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-2.5 py-2 text-xs font-bold font-mono text-slate-900 dark:text-white outline-none cursor-pointer">
                </div>
            </div>
        </div>

        <!-- 2. LES 4 CARTES KPI SYNTHÉTIQUES -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-purple-500 shadow-xs text-center">
                <div id="kpiTotalMnt" class="text-xl font-black font-mono text-slate-900 dark:text-white">0,00 DH</div>
                <span class="text-[10px] font-black uppercase text-slate-400 mt-1 block">Total Global Encaissé</span>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-blue-500 shadow-xs text-center">
                <div id="kpiNbTotal" class="text-xl font-black font-mono text-slate-900 dark:text-white">0</div>
                <span class="text-[10px] font-black uppercase text-slate-400 mt-1 block">Nombre d'Encaissements</span>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-teal-500 shadow-xs text-center">
                <div id="kpiEspMnt" class="text-xl font-black font-mono text-teal-600 dark:text-teal-400">0,00 DH</div>
                <div class="flex justify-center gap-2 text-[10.5px] font-bold text-slate-400 mt-1">
                    <span>Espèces</span>
                    <span>•</span>
                    <span id="kpiEspCount" class="font-mono">0 opérations</span>
                </div>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-amber-500 shadow-xs text-center">
                <div id="kpiChqMnt" class="text-xl font-black font-mono text-amber-600 dark:text-amber-400">0,00 DH</div>
                <div class="flex justify-center gap-2 text-[10.5px] font-bold text-slate-400 mt-1">
                    <span>Chèques & Banques</span>
                    <span>•</span>
                    <span id="kpiChqCount" class="font-mono">0 opérations</span>
                </div>
            </div>
        </div>

        <!-- 3. TABLEAU RÉCAPITULATIF PAR MODE DE PAIEMENT (EN-TÊTES BLANCS & NETS) -->
        <div class="bg-white dark:bg-[#0E1B26] rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs overflow-hidden">
            <div class="px-4 py-3 border-b border-slate-100 dark:border-[#183042] flex items-center justify-between">
                <h3 class="text-xs font-black uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
                    <i data-lucide="pie-chart" class="w-4 h-4 text-purple-400"></i>
                    Récapitulatif par Mode de Paiement
                </h3>
                <span id="labelPeriode" class="text-[11px] text-slate-400 font-mono">Période active</span>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-[#122435] sticky top-0 border-b-2 border-[#1E3A52]">
                        <tr class="text-[12px] sm:text-[13px] font-black uppercase text-white tracking-wider">
                            <th class="py-3 px-4">Mode de Paiement</th>
                            <th class="py-3 px-4 text-center">Nombre</th>
                            <th class="py-3 px-4 text-right">Montant</th>
                            <th class="py-3 px-4 text-center w-36">Détails</th>
                        </tr>
                    </thead>
                    <tbody id="recapTableBody" class="divide-y divide-slate-100 dark:divide-[#183042]/50 text-xs font-semibold">
                    </tbody>
                    <tfoot class="bg-[#0a1520] border-t-2 border-[#1E3A52] text-xs font-black">
                        <tr>
                            <td class="py-2.5 px-4 uppercase text-purple-400">TOTAL</td>
                            <td id="tfootCount" class="py-2.5 px-4 text-center text-white font-mono">0</td>
                            <td id="tfootMnt" class="py-2.5 px-4 text-right text-white font-mono">0,00 DH</td>
                            <td class="py-2.5 px-4 text-center">
                                <button type="button" onclick="ouvrirModalMode('TOUS')" 
                                        class="px-3 py-1 rounded-lg bg-[#184E68] hover:bg-sky-600 text-white font-bold text-xs uppercase tracking-wide transition shadow-xs flex items-center gap-1.5 mx-auto cursor-pointer">
                                    <i data-lucide="list" class="w-3.5 h-3.5"></i>
                                    <span>Détails</span>
                                </button>
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>

    </div>

    <!-- ============================================================================== -->
    <!-- 4. MODALE POPUP DE DÉTAILS DES ENCAISSEMENTS -->
    <!-- ============================================================================== -->
    <div id="modal-encaissements" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 hidden transition-all">
        
        <div id="modal-box" class="bg-[#0A1622] border border-[#1b3449] rounded-2xl w-full max-w-5xl h-[88vh] flex flex-col shadow-2xl overflow-hidden transition-all duration-200">
            
            <!-- EN-TÊTE MODALE -->
            <div class="px-5 py-3 border-b border-[#1b3449] bg-[#071018] flex items-center justify-between shrink-0">
                <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-lg bg-purple-500/15 text-purple-400 flex items-center justify-center font-bold">
                        <i data-lucide="wallet" class="w-4 h-4"></i>
                    </div>
                    <span class="font-black text-xs uppercase tracking-wider text-slate-200">
                        Détails des Encaissements
                    </span>
                </div>

                <div class="px-4 py-1.5 rounded-xl bg-purple-500/15 border border-purple-400/30 flex items-center gap-2 shadow-xs">
                    <i data-lucide="calendar" class="w-4 h-4 text-purple-400"></i>
                    <span id="modal-date-titre" class="text-sm font-black font-mono tracking-widest text-purple-300">
                        ----/--/--
                    </span>
                </div>

                <div class="flex items-center gap-2">
                    <button type="button" onclick="toggleAgrandirModal()" title="Agrandir / Réduire" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 flex items-center justify-center cursor-pointer transition">
                        <i id="icon-maximize" data-lucide="maximize-2" class="w-4 h-4"></i>
                    </button>
                    <button type="button" onclick="fermerModal()" title="Fermer" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-rose-500/20 hover:text-rose-400 text-slate-300 flex items-center justify-center cursor-pointer transition">
                        <i data-lucide="x" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <!-- FILTRES INTERNES MODALE -->
            <div class="px-5 py-3 bg-[#0d1d2c] border-b border-[#1b3449] flex flex-wrap items-center justify-between gap-3 shrink-0">
                <div class="flex items-center gap-1.5 bg-[#071018] p-1 rounded-xl border border-[#1e3a52]">
                    <span class="text-[10px] font-black uppercase text-slate-400 px-2">Mode:</span>
                    <button type="button" onclick="setModalMode('TOUS')" id="btn-mode-TOUS" class="btn-mode-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition bg-purple-600 text-white">Tous</button>
                    <button type="button" onclick="setModalMode('Espèces')" id="btn-mode-Espèces" class="btn-mode-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white">Espèces</button>
                    <button type="button" onclick="setModalMode('Chèque')" id="btn-mode-Chèque" class="btn-mode-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white">Chèque</button>
                    <button type="button" onclick="setModalMode('Virement')" id="btn-mode-Virement" class="btn-mode-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white">Virement</button>
                </div>

                <div class="relative w-48 sm:w-64">
                    <input type="text" id="modalRechercheLibre" oninput="appliquerFiltresModal()" placeholder="Filtrer client ou référence..." 
                           class="w-full bg-[#071018] border border-[#1e3a52] rounded-xl px-3 py-1.5 text-xs font-mono font-bold text-purple-300 placeholder-slate-500 outline-none focus:border-purple-400">
                </div>
            </div>

            <!-- COMPTEUR MODALE -->
            <div class="px-5 py-2 bg-[#091520] border-b border-[#1b3449]/70 flex items-center justify-between text-[11px] font-bold text-slate-400 shrink-0">
                <span id="modalCompteur" class="text-purple-400 font-mono">0 ligne(s)</span>
                <div class="flex items-center gap-4 font-mono">
                    <span>Total Sélection : <strong id="modalTotalMnt" class="text-white font-black">0,00 DH</strong></span>
                </div>
            </div>

            <!-- TABLEAU DÉTAILLÉ SANS COLONNE STATION (EN-TÊTE ÉCLATANT) -->
            <div class="flex-1 overflow-y-auto bg-[#071018]">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-[#122435] sticky top-0 z-20 border-b-2 border-[#1E3A52] shadow-sm">
                        <tr class="text-[12px] sm:text-[13px] font-black uppercase text-white tracking-wider">
                            <th class="py-3 px-4 text-purple-300">Date</th>
                            <th class="py-3 px-4 text-white">Client</th>
                            <th class="py-3 px-4 text-center text-white">Mode</th>
                            <th class="py-3 px-4 text-center text-white">Référence</th>
                            <th class="py-3 px-4 text-right text-white">Montant</th>
                            <th class="py-3 px-4 text-center text-teal-300">Statut</th>
                        </tr>
                    </thead>
                    <tbody id="modalTbody" class="divide-y divide-[#183042]/50 text-xs font-semibold text-slate-200">
                    </tbody>
                </table>
                <div id="modalEmpty" class="text-center py-16 text-slate-500 font-bold hidden">
                    Aucun encaissement trouvé.
                </div>
            </div>

        </div>
    </div>

    <!-- MOTEUR JS INTERACTIF SÉCURISÉ -->
    <script>
        const RAW_B64 = "{encaissements_b64}";
        const DONNEES = JSON.parse(decodeURIComponent(escape(atob(RAW_B64))));
        
        let encaissementsFiltres = [];
        let modeModalActif = 'TOUS';
        let estPleinEcran = false;

        function badgeMode(mode) {{
            const m = (mode || '').toLowerCase();
            if (m.includes('chèque') || m.includes('cheque')) {{
                return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">Chèque</span>';
            }} else if (m.includes('virement')) {{
                return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-500/15 text-blue-400 border border-blue-500/30">Virement</span>';
            }} else if (m.includes('carte') || m.includes('tpe')) {{
                return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-500/15 text-purple-400 border border-purple-500/30">TPE / Carte</span>';
            }}
            return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-teal-500/15 text-teal-400 border border-teal-500/30">Espèces</span>';
        }}

        function filtrerDirect() {{
            const fClient = document.getElementById('filtreClient').value;
            const fMode = document.getElementById('filtreMode').value;
            const fStatut = document.getElementById('filtreStatut').value;
            const dDeb = document.getElementById('filtreDateDebut').value;
            const dFin = document.getElementById('filtreDateFin').value;

            const labelDeb = dDeb ? dDeb.split('-').reverse().join('/') : '--';
            const labelFin = dFin ? dFin.split('-').reverse().join('/') : '--';
            document.getElementById('labelPeriode').innerText = `Du ${{labelDeb}} au ${{labelFin}}`;
            document.getElementById('modal-date-titre').innerText = `${{labelDeb}} ➔ ${{labelFin}}`;

            encaissementsFiltres = [];
            let totalMnt = 0;
            let totEspMnt = 0, totEspCount = 0;
            let totChqMnt = 0, totChqCount = 0;
            let parMode = {{}};

            for (let i = 0; i < DONNEES.length; i++) {{
                const e = DONNEES[i];

                // Comparaison fiable sur les dates ISO (YYYY-MM-DD)
                if (dDeb && e.date_iso && e.date_iso < dDeb) continue;
                if (dFin && e.date_iso && e.date_iso > dFin) continue;
                if (fClient !== 'ALL' && String(e.client_id) !== String(fClient)) continue;
                if (fMode !== 'ALL' && e.mode.toLowerCase() !== fMode.toLowerCase()) continue;
                if (fStatut !== 'ALL' && e.statut.toLowerCase() !== fStatut.toLowerCase()) continue;

                encaissementsFiltres.push(e);
                totalMnt += e.montant;

                const m = e.mode;
                if (!parMode[m]) parMode[m] = {{ count: 0, mnt: 0 }};
                parMode[m].count++;
                parMode[m].mnt += e.montant;

                if (m === 'Espèces') {{
                    totEspMnt += e.montant;
                    totEspCount++;
                }} else {{
                    totChqMnt += e.montant;
                    totChqCount++;
                }}
            }}

            // 1. Mise à jour des 4 cartes KPI
            document.getElementById('kpiTotalMnt').innerText = totalMnt.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
            document.getElementById('kpiNbTotal').innerText = encaissementsFiltres.length;
            document.getElementById('kpiEspMnt').innerText = totEspMnt.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
            document.getElementById('kpiEspCount').innerText = `${{totEspCount}} opérations`;
            document.getElementById('kpiChqMnt').innerText = totChqMnt.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
            document.getElementById('kpiChqCount').innerText = `${{totChqCount}} opérations`;

            // 2. Remplissage du tableau de synthèse par mode
            const tbody = document.getElementById('recapTableBody');
            tbody.innerHTML = '';

            for (const [modeNom, info] of Object.entries(parMode)) {{
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50/50 dark:hover:bg-white/[0.02]";
                tr.innerHTML = `
                    <td class="py-2.5 px-4">${{badgeMode(modeNom)}}</td>
                    <td class="py-2.5 px-4 text-center font-mono font-bold text-slate-800 dark:text-slate-200">${{info.count}}</td>
                    <td class="py-2.5 px-4 text-right font-mono font-black text-slate-900 dark:text-white">${{info.mnt.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }})}} DH</td>
                    <td class="py-2.5 px-4 text-center">
                        <button type="button" onclick="ouvrirModalMode('${{modeNom}}')" 
                                class="px-2.5 py-1 rounded-lg bg-[#184E68] hover:bg-sky-600 text-white text-[11px] font-bold transition flex items-center gap-1 mx-auto cursor-pointer shadow-xs">
                            <i data-lucide="list" class="w-3.5 h-3.5"></i>
                            <span>Détails</span>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            }}

            document.getElementById('tfootCount').innerText = encaissementsFiltres.length;
            document.getElementById('tfootMnt').innerText = totalMnt.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';

            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function ouvrirModalMode(mode) {{
            modeModalActif = mode;
            document.getElementById('modalRechercheLibre').value = '';
            majPillsMode();
            appliquerFiltresModal();
            document.getElementById('modal-encaissements').classList.remove('hidden');
        }}

        function setModalMode(mode) {{
            modeModalActif = mode;
            majPillsMode();
            appliquerFiltresModal();
        }}

        function majPillsMode() {{
            document.querySelectorAll('.btn-mode-pill').forEach(btn => {{
                btn.className = "btn-mode-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white";
            }});
            const actif = document.getElementById('btn-mode-' + modeModalActif);
            if (actif) actif.className = "btn-mode-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition bg-purple-600 text-white shadow-sm";
        }}

        function appliquerFiltresModal() {{
            const search = document.getElementById('modalRechercheLibre').value.trim().toLowerCase();
            let lignes = encaissementsFiltres;

            if (modeModalActif !== 'TOUS') {{
                lignes = lignes.filter(l => l.mode.toLowerCase() === modeModalActif.toLowerCase());
            }}

            if (search) {{
                lignes = lignes.filter(l => 
                    l.client_nom.toLowerCase().includes(search) || 
                    l.reference.toLowerCase().includes(search) || 
                    l.date_fr.includes(search)
                );
            }}

            afficherLignesModal(lignes);
        }}

        function afficherLignesModal(lignes) {{
            const tbody = document.getElementById('modalTbody');
            const empty = document.getElementById('modalEmpty');
            const compteur = document.getElementById('modalCompteur');
            const totalMntEl = document.getElementById('modalTotalMnt');

            compteur.innerText = `${{lignes.length}} ligne(s)`;

            let sum = 0;
            if (lignes.length === 0) {{
                tbody.innerHTML = '';
                empty.classList.remove('hidden');
                totalMntEl.innerText = '0,00 DH';
                return;
            }}

            empty.classList.add('hidden');
            let h = '';
            lignes.forEach(l => {{
                sum += l.montant;
                h += `
                <tr class="hover:bg-white/[0.04] transition-colors border-b border-[#183042]/40">
                    <td class="py-2.5 px-4 font-mono font-bold text-purple-400 text-xs">${{l.date_fr}}</td>
                    <td class="py-2.5 px-4 font-bold text-slate-100 uppercase">${{l.client_nom}}</td>
                    <td class="py-2.5 px-4 text-center">${{badgeMode(l.mode)}}</td>
                    <td class="py-2.5 px-4 text-center font-mono text-slate-400">${{l.reference}}</td>
                    <td class="py-2.5 px-4 text-right font-mono font-black text-white">${{l.montant.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }})}} DH</td>
                    <td class="py-2.5 px-4 text-center">
                        <span class="px-2 py-0.5 rounded-full text-[10.5px] font-extrabold bg-teal-500/15 text-teal-400 border border-teal-500/30">
                            ${{l.statut}}
                        </span>
                    </td>
                </tr>
                `;
            }});

            tbody.innerHTML = h;
            totalMntEl.innerText = sum.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
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

        function fermerModal() {{
            document.getElementById('modal-encaissements').classList.add('hidden');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') fermerModal();
        }});

        document.addEventListener('DOMContentLoaded', () => {{
            filtrerDirect();
        }});
    </script>
    """
    return HTMLResponse(layout(content, active_tab="centre_rapports", request=request))