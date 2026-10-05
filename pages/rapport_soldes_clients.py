# ==============================================================================
# FICHIER : pages/rapport_soldes_clients.py
# ==============================================================================

import html
import json
import base64
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

@router.get("/centre-rapports/soldes-clients", response_class=HTMLResponse)
async def page_rapport_soldes_clients(request: Request):
    conn = get_db_connection()

    # Récupération de tous les clients avec solde calculé
    query = """
        SELECT c.*,
               COALESCE((SELECT SUM(montant) FROM client_encaissements WHERE client_id = c.id), 0.0) AS total_encaisse,
               COALESCE((SELECT SUM(montant_ttc) FROM factures_clients WHERE client_id = c.id), 0.0) AS total_factures
        FROM clients c
        ORDER BY c.nom ASC
    """
    rows = conn.execute(query).fetchall()
    conn.close()

    clients_list = []
    options_clients_html = '<option value="ALL">Tous les clients</option>'

    for r in rows:
        cid = r["id"]
        c_nom = (r["nom"] or "Client Sans Nom").strip()
        c_code = (r["code"] or "CL-000").strip()
        c_type = (r["type_client"] or "Entreprise").strip()
        solde_raw = float(r["solde"] or 0.0)
        plafond_val = float(r["plafond"] or 0.0)
        tel_val = (r["telephone"] or "—").strip()
        ice_val = (r["ice"] or "—").strip()
        statut_val = (r["statut"] or "ACTIF").strip()

        # Règle comptable : solde > 0 => Dette (créance station) | solde < 0 => Crédit (avance client)
        dette = solde_raw if solde_raw > 0 else 0.0
        credit = abs(solde_raw) if solde_raw < 0 else 0.0

        clients_list.append({
            "id": cid,
            "nom": c_nom,
            "code": c_code,
            "type_client": c_type,
            "telephone": tel_val,
            "ice": ice_val,
            "plafond": plafond_val,
            "solde_net": solde_raw,
            "dette": dette,
            "credit": credit,
            "statut": statut_val
        })

        options_clients_html += f'<option value="{cid}">{html.escape(c_nom)} ({html.escape(c_code)})</option>'

    # Encodage sécurisé en Base64 pour traitement JS sans bug de quotes
    clients_b64 = base64.b64encode(json.dumps(clients_list).encode('utf-8')).decode('utf-8')

    content = f"""
    <div class="max-w-7xl mx-auto space-y-4 animate-in fade-in duration-150">
        
        <!-- 1. EN-TÊTE + FILTRES (RESPONSIVE & CONNECTÉ) -->
        <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-[#183042]">
                <div class="flex items-center gap-2.5">
                    <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-pink-500 to-rose-500 text-white flex items-center justify-center font-bold shadow-md shadow-pink-500/20">
                        <i data-lucide="users" class="w-4 h-4"></i>
                    </div>
                    <div>
                        <h1 class="font-black text-slate-900 dark:text-white text-sm uppercase tracking-wider">
                            État des Soldes Clients
                        </h1>
                        <p class="text-[11px] text-slate-500 dark:text-slate-400">Suivi des créances clients, dettes en cours et soldes créditeurs</p>
                    </div>
                </div>

                <a href="/centre-rapports" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-[#132738] text-slate-700 dark:text-slate-200 text-xs font-bold transition">
                    <i data-lucide="arrow-left" class="w-3.5 h-3.5"></i>
                    <span>Retour Hub</span>
                </a>
            </div>

            <!-- LES 3 FILTRES DEMANDÉS (TYPE DE CLIENT - CLIENT - FILTRE SOLDE) -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                <div>
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Type de Client</label>
                    <select id="filtreTypeClient" onchange="filtrerDirectSoldes()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none cursor-pointer">
                        <option value="ALL">Tous les types</option>
                        <option value="Entreprise">Entreprise</option>
                        <option value="Particulier">Particulier</option>
                    </select>
                </div>

                <div>
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Client</label>
                    <select id="filtreClient" onchange="filtrerDirectSoldes()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none cursor-pointer">
                        {options_clients_html}
                    </select>
                </div>

                <div>
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Filtre Solde</label>
                    <select id="filtreSolde" onchange="filtrerDirectSoldes()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none cursor-pointer">
                        <option value="ALL">Tous</option>
                        <option value="DETTE">Débiteurs (Dettes > 0)</option>
                        <option value="CREDIT">Créditeurs (Crédits > 0)</option>
                        <option value="SOLDE">Soldés (Solde = 0)</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- 2. LES 4 CARTES KPIS CONFORMES À L'IMAGE 4 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <!-- Carte 1 : CLIENTS (Bordure bleue) -->
            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-sky-500 shadow-xs text-center">
                <div id="kpiNbClients" class="text-2xl font-black font-mono text-slate-900 dark:text-white">0</div>
                <span class="text-[10px] font-black uppercase tracking-wider text-slate-400 mt-1 block">CLIENTS</span>
            </div>

            <!-- Carte 2 : TOTAL DETTES (Bordure rouge) -->
            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-rose-500 shadow-xs text-center">
                <div id="kpiTotalDettes" class="text-2xl font-black font-mono text-rose-600 dark:text-rose-400">0,00</div>
                <span class="text-[10px] font-black uppercase tracking-wider text-slate-400 mt-1 block">TOTAL DETTES</span>
            </div>

            <!-- Carte 3 : TOTAL CRÉDITS (Bordure verte) -->
            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-emerald-500 shadow-xs text-center">
                <div id="kpiTotalCredits" class="text-2xl font-black font-mono text-emerald-600 dark:text-[#00F5A0]">0,00</div>
                <span class="text-[10px] font-black uppercase tracking-wider text-slate-400 mt-1 block">TOTAL CRÉDITS</span>
            </div>

            <!-- Carte 4 : SOLDE NET (Bordure violette) -->
            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-purple-500 shadow-xs text-center">
                <div id="kpiSoldeNet" class="text-2xl font-black font-mono text-slate-900 dark:text-white">0,00</div>
                <span class="text-[10px] font-black uppercase tracking-wider text-slate-400 mt-1 block">SOLDE NET</span>
            </div>
        </div>

        <!-- 3. TABLEAU RÉCAPITULATIF PAR TYPE DE CLIENT (IMAGE 4) -->
        <div class="bg-white dark:bg-[#0E1B26] rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs overflow-hidden">
            <div class="px-4 py-3 border-b border-slate-100 dark:border-[#183042] flex items-center justify-between">
                <h3 class="text-xs font-black uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
                    <i data-lucide="pie-chart" class="w-4 h-4 text-purple-400"></i>
                    Récapitulatif par Type de Client
                </h3>
                <span class="text-[11px] text-slate-400 font-mono">Vue analytique</span>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-[#122435] sticky top-0 border-b-2 border-[#1E3A52]">
                        <tr class="text-[12px] sm:text-[13px] font-black uppercase text-white tracking-wider">
                            <th class="py-3 px-4">Type Client</th>
                            <th class="py-3 px-4 text-center">Nombre</th>
                            <th class="py-3 px-4 text-right text-rose-300">Dettes</th>
                            <th class="py-3 px-4 text-right text-emerald-300">Crédits</th>
                            <th class="py-3 px-4 text-center w-36">Détails</th>
                        </tr>
                    </thead>
                    <tbody id="recapSoldesTbody" class="divide-y divide-slate-100 dark:divide-[#183042]/50 text-xs font-semibold">
                    </tbody>
                    <tfoot class="bg-rose-50/70 dark:bg-rose-950/20 border-t-2 border-rose-200 dark:border-rose-900/40 text-xs font-black">
                        <tr>
                            <td class="py-3 px-4 uppercase text-slate-900 dark:text-white">TOTAL</td>
                            <td id="tfootNb" class="py-3 px-4 text-center text-slate-900 dark:text-white font-mono">0</td>
                            <td id="tfootDettes" class="py-3 px-4 text-right text-rose-600 dark:text-rose-400 font-mono">0,00</td>
                            <td id="tfootCredits" class="py-3 px-4 text-right text-emerald-600 dark:text-[#00F5A0] font-mono">0,00</td>
                            <td class="py-3 px-4 text-center">
                                <button type="button" onclick="ouvrirModalSoldes('ALL')" 
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
    <!-- 4. MODALE POPUP DE DÉTAILS DES CLIENTS (MÊME STRUCTURE QUE ENCAISSEMENTS) -->
    <!-- ============================================================================== -->
    <div id="modal-soldes" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 hidden transition-all">
        
        <div id="modal-box" class="bg-[#0A1622] border border-[#1b3449] rounded-2xl w-full max-w-5xl h-[88vh] flex flex-col shadow-2xl overflow-hidden transition-all duration-200">
            
            <!-- EN-TÊTE MODALE -->
            <div class="px-5 py-3 border-b border-[#1b3449] bg-[#071018] flex items-center justify-between shrink-0">
                <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-lg bg-pink-500/15 text-pink-400 flex items-center justify-center font-bold">
                        <i data-lucide="users" class="w-4 h-4"></i>
                    </div>
                    <span class="font-black text-xs uppercase tracking-wider text-slate-200">
                        Détails des Soldes Clients
                    </span>
                </div>

                <div class="px-4 py-1.5 rounded-xl bg-pink-500/15 border border-pink-400/30 flex items-center gap-2 shadow-xs">
                    <i data-lucide="shield-check" class="w-4 h-4 text-pink-400"></i>
                    <span id="modal-type-titre" class="text-sm font-black font-mono tracking-widest text-pink-300">
                        TOUS LES TYPES
                    </span>
                </div>

                <div class="flex items-center gap-2">
                    <button type="button" onclick="toggleAgrandirModal()" title="Agrandir / Réduire" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 flex items-center justify-center cursor-pointer transition">
                        <i id="icon-maximize" data-lucide="maximize-2" class="w-4 h-4"></i>
                    </button>
                    <button type="button" onclick="fermerModalSoldes()" title="Fermer" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-rose-500/20 hover:text-rose-400 text-slate-300 flex items-center justify-center cursor-pointer transition">
                        <i data-lucide="x" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <!-- FILTRES INTERNES MODALE -->
            <div class="px-5 py-3 bg-[#0d1d2c] border-b border-[#1b3449] flex flex-wrap items-center justify-between gap-3 shrink-0">
                <div class="flex items-center gap-1.5 bg-[#071018] p-1 rounded-xl border border-[#1e3a52]">
                    <span class="text-[10px] font-black uppercase text-slate-400 px-2">Type:</span>
                    <button type="button" onclick="setModalType('ALL')" id="btn-type-ALL" class="btn-type-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition bg-pink-600 text-white">Tous</button>
                    <button type="button" onclick="setModalType('Entreprise')" id="btn-type-Entreprise" class="btn-type-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white">Entreprise</button>
                    <button type="button" onclick="setModalType('Particulier')" id="btn-type-Particulier" class="btn-type-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white">Particulier</button>
                </div>

                <div class="relative w-48 sm:w-64">
                    <input type="text" id="modalRechercheLibre" oninput="appliquerFiltresModal()" placeholder="Rechercher client, code, ICE..." 
                           class="w-full bg-[#071018] border border-[#1e3a52] rounded-xl px-3 py-1.5 text-xs font-mono font-bold text-pink-300 placeholder-slate-500 outline-none focus:border-pink-400">
                </div>
            </div>

            <!-- COMPTEUR MODALE -->
            <div class="px-5 py-2 bg-[#091520] border-b border-[#1b3449]/70 flex items-center justify-between text-[11px] font-bold text-slate-400 shrink-0">
                <span id="modalCompteur" class="text-pink-400 font-mono">0 client(s)</span>
                <div class="flex items-center gap-4 font-mono">
                    <span>Dettes : <strong id="modalTotalDettes" class="text-rose-400 font-black">0,00 DH</strong></span>
                    <span>Crédits : <strong id="modalTotalCredits" class="text-emerald-400 font-black">0,00 DH</strong></span>
                    <span>Net : <strong id="modalTotalNet" class="text-white font-black">0,00 DH</strong></span>
                </div>
            </div>

            <!-- TABLEAU DÉTAILLÉ DES CLIENTS -->
            <div class="flex-1 overflow-y-auto bg-[#071018]">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-[#122435] sticky top-0 z-20 border-b-2 border-[#1E3A52] shadow-sm">
                        <tr class="text-[12px] sm:text-[13px] font-black uppercase text-white tracking-wider">
                            <th class="py-3 px-4 text-sky-300">Code</th>
                            <th class="py-3 px-4 text-white">Client</th>
                            <th class="py-3 px-4 text-center text-white">Type</th>
                            <th class="py-3 px-4 text-right text-rose-300">Dettes</th>
                            <th class="py-3 px-4 text-right text-emerald-300">Crédits</th>
                            <th class="py-3 px-4 text-right text-white">Solde Net</th>
                            <th class="py-3 px-4 text-center text-teal-300">Statut</th>
                            <th class="py-3 px-4 text-center">Fiche</th>
                        </tr>
                    </thead>
                    <tbody id="modalTbody" class="divide-y divide-[#183042]/50 text-xs font-semibold text-slate-200">
                    </tbody>
                </table>
                <div id="modalEmpty" class="text-center py-16 text-slate-500 font-bold hidden">
                    Aucun client ne correspond aux critères.
                </div>
            </div>

        </div>
    </div>

    <!-- MOTEUR JS INTERACTIF ET SYNCHRONE -->
    <script>
        const RAW_B64 = "{clients_b64}";
        const TOUS_LES_CLIENTS = JSON.parse(decodeURIComponent(escape(atob(RAW_B64))));
        
        let clientsFiltresActifs = [];
        let typeModalActif = 'ALL';
        let estPleinEcran = false;

        function badgeTypeClient(type) {{
            if ((type || '').toLowerCase() === 'entreprise') {{
                return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-[#00F5A0] border border-emerald-300/40">Entreprise</span>';
            }}
            return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300 border border-blue-300/40">Particulier</span>';
        }}

        function filtrerDirectSoldes() {{
            const fType = document.getElementById('filtreTypeClient').value;
            const fClientId = document.getElementById('filtreClient').value;
            const fSolde = document.getElementById('filtreSolde').value;

            clientsFiltresActifs = [];
            let sumDettes = 0;
            let sumCredits = 0;
            let sumNet = 0;

            let parType = {{}};

            for (let i = 0; i < TOUS_LES_CLIENTS.length; i++) {{
                const c = TOUS_LES_CLIENTS[i];

                if (fType !== 'ALL' && c.type_client.toLowerCase() !== fType.toLowerCase()) continue;
                if (fClientId !== 'ALL' && String(c.id) !== String(fClientId)) continue;

                if (fSolde === 'DETTE' && c.dette <= 0.001) continue;
                if (fSolde === 'CREDIT' && c.credit <= 0.001) continue;
                if (fSolde === 'SOLDE' && (c.dette > 0.001 || c.credit > 0.001)) continue;

                clientsFiltresActifs.push(c);

                sumDettes += c.dette;
                sumCredits += c.credit;
                sumNet += c.solde_net;

                const t = c.type_client || 'Entreprise';
                if (!parType[t]) parType[t] = {{ count: 0, dettes: 0, credits: 0 }};
                parType[t].count++;
                parType[t].dettes += c.dette;
                parType[t].credits += c.credit;
            }}

            // 1. Mise à jour des 4 KPIs
            document.getElementById('kpiNbClients').innerText = clientsFiltresActifs.length;
            document.getElementById('kpiTotalDettes').innerText = sumDettes.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
            document.getElementById('kpiTotalCredits').innerText = sumCredits.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
            document.getElementById('kpiSoldeNet').innerText = sumNet.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});

            // 2. Remplissage du tableau Récapitulatif par Type de Client (Image 4)
            const tbody = document.getElementById('recapSoldesTbody');
            tbody.innerHTML = '';

            for (const [nomType, info] of Object.entries(parType)) {{
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50/50 dark:hover:bg-white/[0.02] cursor-pointer";
                tr.onclick = function() {{ ouvrirModalSoldes(nomType); }};

                tr.innerHTML = `
                    <td class="py-3 px-4">${{badgeTypeClient(nomType)}}</td>
                    <td class="py-3 px-4 text-center font-mono font-bold text-slate-800 dark:text-slate-200">${{info.count}}</td>
                    <td class="py-3 px-4 text-right font-mono font-black text-rose-600 dark:text-rose-400">${{info.dettes.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                    <td class="py-3 px-4 text-right font-mono font-black text-emerald-600 dark:text-[#00F5A0]">${{info.credits.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                    <td class="py-3 px-4 text-center" onclick="event.stopPropagation()">
                        <button type="button" onclick="ouvrirModalSoldes('${{nomType}}')" 
                                class="px-2.5 py-1 rounded-lg bg-[#184E68] hover:bg-sky-600 text-white text-[11px] font-bold transition flex items-center gap-1 mx-auto cursor-pointer shadow-xs">
                            <i data-lucide="list" class="w-3.5 h-3.5"></i>
                            <span>Détails</span>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            }}

            document.getElementById('tfootNb').innerText = clientsFiltresActifs.length;
            document.getElementById('tfootDettes').innerText = sumDettes.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
            document.getElementById('tfootCredits').innerText = sumCredits.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});

            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function ouvrirModalSoldes(type) {{
            typeModalActif = type;
            document.getElementById('modalRechercheLibre').value = '';
            majPillsType();
            appliquerFiltresModal();
            document.getElementById('modal-soldes').classList.remove('hidden');
        }}

        function setModalType(type) {{
            typeModalActif = type;
            majPillsType();
            appliquerFiltresModal();
        }}

        function majPillsType() {{
            document.querySelectorAll('.btn-type-pill').forEach(btn => {{
                btn.className = "btn-type-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white";
            }});
            const actif = document.getElementById('btn-type-' + typeModalActif);
            if (actif) actif.className = "btn-type-pill px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition bg-pink-600 text-white shadow-sm";
            document.getElementById('modal-type-titre').innerText = (typeModalActif === 'ALL') ? 'TOUS LES TYPES' : typeModalActif.toUpperCase();
        }}

        function appliquerFiltresModal() {{
            const search = document.getElementById('modalRechercheLibre').value.trim().toLowerCase();
            let lignes = clientsFiltresActifs;

            if (typeModalActif !== 'ALL') {{
                lignes = lignes.filter(c => c.type_client.toLowerCase() === typeModalActif.toLowerCase());
            }}

            if (search) {{
                lignes = lignes.filter(c => 
                    c.nom.toLowerCase().includes(search) || 
                    c.code.toLowerCase().includes(search) || 
                    c.ice.toLowerCase().includes(search) ||
                    c.telephone.toLowerCase().includes(search)
                );
            }}

            afficherLignesModal(lignes);
        }}

        function afficherLignesModal(lignes) {{
            const tbody = document.getElementById('modalTbody');
            const empty = document.getElementById('modalEmpty');
            const compteur = document.getElementById('modalCompteur');
            const totDettesEl = document.getElementById('modalTotalDettes');
            const totCreditsEl = document.getElementById('modalTotalCredits');
            const totNetEl = document.getElementById('modalTotalNet');

            compteur.innerText = `${{lignes.length}} client(s)`;

            let sumDettes = 0;
            let sumCredits = 0;
            let sumNet = 0;

            if (lignes.length === 0) {{
                tbody.innerHTML = '';
                empty.classList.remove('hidden');
                totDettesEl.innerText = '0,00 DH';
                totCreditsEl.innerText = '0,00 DH';
                totNetEl.innerText = '0,00 DH';
                return;
            }}

            empty.classList.add('hidden');
            let h = '';
            lignes.forEach(c => {{
                sumDettes += c.dette;
                sumCredits += c.credit;
                sumNet += c.solde_net;

                h += `
                <tr class="hover:bg-white/[0.04] transition-colors border-b border-[#183042]/40">
                    <td class="py-2.5 px-4 font-mono font-bold text-sky-400 text-xs">${{c.code}}</td>
                    <td class="py-2.5 px-4 font-bold text-slate-100 uppercase">${{c.nom}}</td>
                    <td class="py-2.5 px-4 text-center">${{badgeTypeClient(c.type_client)}}</td>
                    <td class="py-2.5 px-4 text-right font-mono font-black text-rose-500">${{c.dette.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }})}} DH</td>
                    <td class="py-2.5 px-4 text-right font-mono font-black text-emerald-400">${{c.credit.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }})}} DH</td>
                    <td class="py-2.5 px-4 text-right font-mono font-black text-white">${{c.solde_net.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }})}} DH</td>
                    <td class="py-2.5 px-4 text-center">
                        <span class="px-2 py-0.5 rounded-full text-[10.5px] font-extrabold ${{c.statut === 'ACTIF' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-slate-500/15 text-slate-400 border border-slate-500/30'}}">
                            ${{c.statut}}
                        </span>
                    </td>
                    <td class="py-2.5 px-4 text-center">
                        <a href="/clients/${{c.id}}" class="p-1.5 rounded-lg bg-white/5 hover:bg-sky-500/20 text-sky-400 inline-flex items-center justify-center transition" title="Voir fiche client">
                            <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                        </a>
                    </td>
                </tr>
                `;
            }});

            tbody.innerHTML = h;
            totDettesEl.innerText = sumDettes.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
            totCreditsEl.innerText = sumCredits.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
            totNetEl.innerText = sumNet.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
            if (typeof lucide !== 'undefined') lucide.createIcons();
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

        function fermerModalSoldes() {{
            document.getElementById('modal-soldes').classList.add('hidden');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') fermerModalSoldes();
        }});

        document.addEventListener('DOMContentLoaded', () => {{
            filtrerDirectSoldes();
        }});
    </script>
    """
    return HTMLResponse(layout(content, active_tab="centre_rapports", request=request))