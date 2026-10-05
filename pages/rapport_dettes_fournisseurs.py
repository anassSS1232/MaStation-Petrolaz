# ==============================================================================
# FICHIER : pages/rapport_dettes_fournisseurs.py
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

@router.get("/centre-rapports/dettes-fournisseurs", response_class=HTMLResponse)
async def page_rapport_dettes_fournisseurs(request: Request):
    conn = get_db_connection()

    # Récupération de tous les fournisseurs avec achats et règlements calculés
    query = """
        SELECT f.*,
               COALESCE((SELECT SUM(montant_total) FROM achats_fournisseurs WHERE fournisseur_id = f.id), 0.0) AS total_achats,
               COALESCE((SELECT SUM(montant) FROM reglements_fournisseurs WHERE fournisseur_id = f.id), 0.0) AS total_reglements
        FROM fournisseurs f
        ORDER BY f.nom ASC
    """
    rows = conn.execute(query).fetchall()
    conn.close()

    fournisseurs_list = []
    options_fournisseurs_html = '<option value="ALL">Tous les fournisseurs</option>'

    for r in rows:
        fid = r["id"]
        f_nom = (r["nom"] or "Fournisseur Sans Nom").strip()
        f_code = (r["code"] or f"FOUR-{fid:03d}").strip()
        f_type = (r["type_fournisseur"] or "Carburant").strip()
        solde_init = float(r["solde_initial"] or 0.0)
        tot_achats = float(r["total_achats"] or 0.0)
        tot_paye = float(r["total_reglements"] or 0.0)
        tel_val = (r["telephone"] or "—").strip()
        email_val = (r["email"] or "—").strip()
        statut_val = (r["statut"] or "Actif").strip()

        # Calcul comptable : Solde net dû au fournisseur
        solde_net = (solde_init + tot_achats) - tot_paye
        dette = solde_net if solde_net > 0 else 0.0
        avoir = abs(solde_net) if solde_net < 0 else 0.0

        fournisseurs_list.append({
            "id": fid,
            "nom": f_nom,
            "code": f_code,
            "type_fournisseur": f_type,
            "telephone": tel_val,
            "email": email_val,
            "total_achats": tot_achats,
            "total_paye": tot_paye,
            "dette": dette,
            "avoir": avoir,
            "solde_net": solde_net,
            "statut": statut_val
        })

        options_fournisseurs_html += f'<option value="{fid}">{html.escape(f_nom)} ({html.escape(f_code)})</option>'

    # Encodage sécurisé en Base64 pour le JS (aucun risque de bug de guillemets)
    fournisseurs_b64 = base64.b64encode(json.dumps(fournisseurs_list).encode('utf-8')).decode('utf-8')

    content = f"""
    <div class="max-w-7xl mx-auto space-y-4 animate-in fade-in duration-150">
        
        <!-- 1. EN-TÊTE + LES 3 FILTRES CONNECTÉS -->
        <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs space-y-3">
            <div class="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-[#183042]">
                <div class="flex items-center gap-2.5">
                    <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-400 to-cyan-500 text-white flex items-center justify-center font-bold shadow-md shadow-sky-500/20">
                        <i data-lucide="truck" class="w-4 h-4"></i>
                    </div>
                    <div>
                        <h1 class="font-black text-slate-900 dark:text-white text-sm uppercase tracking-wider">
                            État des Dettes Fournisseurs
                        </h1>
                        <p class="text-[11px] text-slate-500 dark:text-slate-400">Suivi des dettes, BL d'achats et soldes d'avoirs fournisseurs</p>
                    </div>
                </div>

                <a href="/centre-rapports" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-[#132738] dark:hover:bg-[#1b354d] text-slate-700 dark:text-slate-200 text-xs font-bold transition">
                    <i data-lucide="arrow-left" class="w-3.5 h-3.5"></i>
                    <span>Retour Hub</span>
                </a>
            </div>

            <!-- FILTRES : TYPE DE FOURNISSEUR | FOURNISSEUR | FILTRE SOLDE -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                <div>
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Type de Fournisseur</label>
                    <select id="filtreTypeFournisseur" onchange="filtrerDirectFournisseurs()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none cursor-pointer transition">
                        <option value="ALL">Tous les types</option>
                        <option value="Carburant">Carburant</option>
                        <option value="Lubrifiant">Lubrifiant</option>
                        <option value="Services">Services</option>
                        <option value="Équipements">Équipements</option>
                        <option value="Grossiste">Grossiste</option>
                        <option value="Autre">Autre</option>
                    </select>
                </div>

                <div>
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Fournisseur</label>
                    <select id="filtreFournisseur" onchange="filtrerDirectFournisseurs()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none cursor-pointer transition">
                        {options_fournisseurs_html}
                    </select>
                </div>

                <div>
                    <label class="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Filtre Solde</label>
                    <select id="filtreSoldeFourn" onchange="filtrerDirectFournisseurs()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none cursor-pointer transition">
                        <option value="ALL">Tous</option>
                        <option value="DETTE">Dettes en cours (Dettes > 0)</option>
                        <option value="AVOIR">Avoirs / Trop-perçus (Avoirs > 0)</option>
                        <option value="SOLDE">Soldés (Solde = 0)</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- 2. LES 4 CARTES KPIS CONFORMES À L'IMAGE 4 (ADAPTÉES CLAIR & SOMBRE) -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <!-- Carte 1 : FOURNISSEURS (Bordure bleue) -->
            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-sky-500 shadow-xs text-center transition">
                <div id="kpiNbFourn" class="text-2xl font-black font-mono text-slate-900 dark:text-white">0</div>
                <span class="text-[10px] font-black uppercase tracking-wider text-slate-400 mt-1 block">FOURNISSEURS</span>
            </div>

            <!-- Carte 2 : TOTAL DETTES (Bordure rouge) -->
            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-rose-500 shadow-xs text-center transition">
                <div id="kpiTotalDettesFourn" class="text-2xl font-black font-mono text-rose-600 dark:text-rose-400">0,00</div>
                <span class="text-[10px] font-black uppercase tracking-wider text-slate-400 mt-1 block">TOTAL DETTES</span>
            </div>

            <!-- Carte 3 : TOTAL AVOIRS (Bordure verte) -->
            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-emerald-500 shadow-xs text-center transition">
                <div id="kpiTotalAvoirsFourn" class="text-2xl font-black font-mono text-emerald-600 dark:text-[#00F5A0]">0,00</div>
                <span class="text-[10px] font-black uppercase tracking-wider text-slate-400 mt-1 block">TOTAL AVOIRS</span>
            </div>

            <!-- Carte 4 : SOLDE NET (Bordure violette) -->
            <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] border-t-4 border-t-purple-500 shadow-xs text-center transition">
                <div id="kpiSoldeNetFourn" class="text-2xl font-black font-mono text-slate-900 dark:text-white">0,00</div>
                <span class="text-[10px] font-black uppercase tracking-wider text-slate-400 mt-1 block">SOLDE NET</span>
            </div>
        </div>

        <!-- 3. TABLEAU RÉCAPITULATIF PAR TYPE DE FOURNISSEUR (IMAGE 4) -->
        <div class="bg-white dark:bg-[#0E1B26] rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs overflow-hidden transition">
            <div class="px-4 py-3 border-b border-slate-100 dark:border-[#183042] flex items-center justify-between">
                <h3 class="text-xs font-black uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
                    <i data-lucide="pie-chart" class="w-4 h-4 text-sky-500"></i>
                    Récapitulatif par Type de Fournisseur
                </h3>
                <span class="text-[11px] text-slate-400 font-mono">Vue synthétique</span>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-[#122435] sticky top-0 border-b-2 border-[#1E3A52]">
                        <tr class="text-[12px] sm:text-[13px] font-black uppercase text-white tracking-wider">
                            <th class="py-3 px-4">Type Fournisseur</th>
                            <th class="py-3 px-4 text-center">Nombre</th>
                            <th class="py-3 px-4 text-right text-rose-300">Dettes</th>
                            <th class="py-3 px-4 text-right text-emerald-300">Avoirs</th>
                            <th class="py-3 px-4 text-center w-36">Détails</th>
                        </tr>
                    </thead>
                    <tbody id="recapFournTbody" class="divide-y divide-slate-100 dark:divide-[#183042]/50 text-xs font-semibold">
                    </tbody>
                    <tfoot class="bg-sky-50/70 dark:bg-sky-950/20 border-t-2 border-sky-200 dark:border-sky-900/40 text-xs font-black">
                        <tr>
                            <td class="py-3 px-4 uppercase text-slate-900 dark:text-white">TOTAL</td>
                            <td id="tfootNbFourn" class="py-3 px-4 text-center text-slate-900 dark:text-white font-mono">0</td>
                            <td id="tfootDettesFourn" class="py-3 px-4 text-right text-rose-600 dark:text-rose-400 font-mono">0,00</td>
                            <td id="tfootAvoirsFourn" class="py-3 px-4 text-right text-emerald-600 dark:text-[#00F5A0] font-mono">0,00</td>
                            <td class="py-3 px-4 text-center">
                                <button type="button" onclick="ouvrirModalFourn('ALL')" 
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
    <!-- 4. MODALE POPUP DE DÉTAILS DES FOURNISSEURS (STYLE RAPPORT ENCAISSEMENTS) -->
    <!-- ============================================================================== -->
    <div id="modal-dettes-fourn" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 hidden transition-all">
        
        <div id="modal-box-fourn" class="bg-[#0A1622] border border-[#1b3449] rounded-2xl w-full max-w-5xl h-[88vh] flex flex-col shadow-2xl overflow-hidden transition-all duration-200">
            
            <!-- EN-TÊTE MODALE -->
            <div class="px-5 py-3 border-b border-[#1b3449] bg-[#071018] flex items-center justify-between shrink-0">
                <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-lg bg-sky-500/15 text-sky-400 flex items-center justify-center font-bold">
                        <i data-lucide="truck" class="w-4 h-4"></i>
                    </div>
                    <span class="font-black text-xs uppercase tracking-wider text-slate-200">
                        Détails des Dettes Fournisseurs
                    </span>
                </div>

                <div class="px-4 py-1.5 rounded-xl bg-sky-500/15 border border-sky-400/30 flex items-center gap-2 shadow-xs">
                    <i data-lucide="shield-check" class="w-4 h-4 text-sky-400"></i>
                    <span id="modal-type-titre-fourn" class="text-sm font-black font-mono tracking-widest text-sky-300">
                        TOUS LES TYPES
                    </span>
                </div>

                <div class="flex items-center gap-2">
                    <button type="button" onclick="toggleAgrandirModalFourn()" title="Agrandir / Réduire" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 flex items-center justify-center cursor-pointer transition">
                        <i id="icon-maximize-fourn" data-lucide="maximize-2" class="w-4 h-4"></i>
                    </button>
                    <button type="button" onclick="fermerModalFourn()" title="Fermer" class="w-8 h-8 rounded-lg bg-white/5 hover:bg-rose-500/20 hover:text-rose-400 text-slate-300 flex items-center justify-center cursor-pointer transition">
                        <i data-lucide="x" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <!-- FILTRES INTERNES MODALE -->
            <div class="px-5 py-3 bg-[#0d1d2c] border-b border-[#1b3449] flex flex-wrap items-center justify-between gap-3 shrink-0">
                <div class="flex items-center gap-1.5 bg-[#071018] p-1 rounded-xl border border-[#1e3a52] overflow-x-auto max-w-full">
                    <span class="text-[10px] font-black uppercase text-slate-400 px-2 shrink-0">Type:</span>
                    <button type="button" onclick="setModalTypeFourn('ALL')" id="btn-type-fourn-ALL" class="btn-type-pill-fourn px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition bg-sky-600 text-white shrink-0">Tous</button>
                    <button type="button" onclick="setModalTypeFourn('Carburant')" id="btn-type-fourn-Carburant" class="btn-type-pill-fourn px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white shrink-0">Carburant</button>
                    <button type="button" onclick="setModalTypeFourn('Lubrifiant')" id="btn-type-fourn-Lubrifiant" class="btn-type-pill-fourn px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white shrink-0">Lubrifiant</button>
                    <button type="button" onclick="setModalTypeFourn('Services')" id="btn-type-fourn-Services" class="btn-type-pill-fourn px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white shrink-0">Services</button>
                </div>

                <div class="relative w-48 sm:w-64">
                    <input type="text" id="modalRechercheLibreFourn" oninput="appliquerFiltresModalFourn()" placeholder="Rechercher fournisseur, code..." 
                           class="w-full bg-[#071018] border border-[#1e3a52] rounded-xl px-3 py-1.5 text-xs font-mono font-bold text-sky-300 placeholder-slate-500 outline-none focus:border-sky-400">
                </div>
            </div>

            <!-- COMPTEUR MODALE -->
            <div class="px-5 py-2 bg-[#091520] border-b border-[#1b3449]/70 flex items-center justify-between text-[11px] font-bold text-slate-400 shrink-0">
                <span id="modalCompteurFourn" class="text-sky-400 font-mono">0 fournisseur(s)</span>
                <div class="flex items-center gap-4 font-mono">
                    <span>Dettes : <strong id="modalTotalDettesVal" class="text-rose-400 font-black">0,00 DH</strong></span>
                    <span>Avoirs : <strong id="modalTotalAvoirsVal" class="text-emerald-400 font-black">0,00 DH</strong></span>
                    <span>Net : <strong id="modalTotalNetVal" class="text-white font-black">0,00 DH</strong></span>
                </div>
            </div>

            <!-- TABLEAU DÉTAILLÉ DES FOURNISSEURS -->
            <div class="flex-1 overflow-y-auto bg-[#071018]">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-[#122435] sticky top-0 z-20 border-b-2 border-[#1E3A52] shadow-sm">
                        <tr class="text-[12px] sm:text-[13px] font-black uppercase text-white tracking-wider">
                            <th class="py-3 px-4 text-sky-300">Code</th>
                            <th class="py-3 px-4 text-white">Fournisseur</th>
                            <th class="py-3 px-4 text-center text-white">Type</th>
                            <th class="py-3 px-4 text-right text-slate-300">Total Achats</th>
                            <th class="py-3 px-4 text-right text-teal-300">Total Réglé</th>
                            <th class="py-3 px-4 text-right text-rose-300">Dettes</th>
                            <th class="py-3 px-4 text-right text-emerald-300">Avoirs</th>
                            <th class="py-3 px-4 text-right text-white">Solde Net</th>
                            <th class="py-3 px-4 text-center">Fiche</th>
                        </tr>
                    </thead>
                    <tbody id="modalTbodyFourn" class="divide-y divide-[#183042]/50 text-xs font-semibold text-slate-200">
                    </tbody>
                </table>
                <div id="modalEmptyFourn" class="text-center py-16 text-slate-500 font-bold hidden">
                    Aucun fournisseur ne correspond aux critères.
                </div>
            </div>

        </div>
    </div>

    <!-- SCRIPT DU COMPOSANT : CALCULS, FILTRAGE INSTANTANÉ ET MODALE -->
    <script>
        const RAW_B64_FOURN = "{fournisseurs_b64}";
        const TOUS_LES_FOURNISSEURS = JSON.parse(decodeURIComponent(escape(atob(RAW_B64_FOURN))));

        let fournisseursFiltresActifs = [];
        let typeModalFournActif = 'ALL';
        let estPleinEcranFourn = false;

        function badgeTypeFournisseur(type) {{
            const t = (type || 'Carburant').toLowerCase();
            if (t.includes('carburant')) {{
                return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-[#E5A842] border border-amber-300/40">Carburant</span>';
            }} else if (t.includes('lubrifiant')) {{
                return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-500/20 dark:text-purple-300 border border-purple-300/40">Lubrifiant</span>';
            }} else if (t.includes('service')) {{
                return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-100 text-sky-800 dark:bg-sky-500/20 dark:text-sky-300 border border-sky-300/40">Services</span>';
            }}
            return '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-800 dark:bg-slate-700/40 dark:text-slate-200 border border-slate-300/40">' + htmlEscape(type) + '</span>';
        }}

        function htmlEscape(str) {{
            return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }}

        function filtrerDirectFournisseurs() {{
            const fType = document.getElementById('filtreTypeFournisseur').value;
            const fFournId = document.getElementById('filtreFournisseur').value;
            const fSolde = document.getElementById('filtreSoldeFourn').value;

            fournisseursFiltresActifs = [];
            let sumDettes = 0;
            let sumAvoirs = 0;
            let sumNet = 0;

            let parType = {{}};

            for (let i = 0; i < TOUS_LES_FOURNISSEURS.length; i++) {{
                const f = TOUS_LES_FOURNISSEURS[i];

                if (fType !== 'ALL' && f.type_fournisseur.toLowerCase() !== fType.toLowerCase()) continue;
                if (fFournId !== 'ALL' && String(f.id) !== String(fFournId)) continue;

                if (fSolde === 'DETTE' && f.dette <= 0.001) continue;
                if (fSolde === 'AVOIR' && f.avoir <= 0.001) continue;
                if (fSolde === 'SOLDE' && (f.dette > 0.001 || f.avoir > 0.001)) continue;

                fournisseursFiltresActifs.push(f);

                sumDettes += f.dette;
                sumAvoirs += f.avoir;
                sumNet += f.solde_net;

                const t = f.type_fournisseur || 'Carburant';
                if (!parType[t]) parType[t] = {{ count: 0, dettes: 0, avoirs: 0 }};
                parType[t].count++;
                parType[t].dettes += f.dette;
                parType[t].avoirs += f.avoir;
            }}

            // 1. Mise à jour des 4 KPIs
            document.getElementById('kpiNbFourn').innerText = fournisseursFiltresActifs.length;
            document.getElementById('kpiTotalDettesFourn').innerText = sumDettes.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
            document.getElementById('kpiTotalAvoirsFourn').innerText = sumAvoirs.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
            document.getElementById('kpiSoldeNetFourn').innerText = sumNet.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});

            // 2. Remplissage du tableau Récapitulatif par Type de Fournisseur (Image 4)
            const tbody = document.getElementById('recapFournTbody');
            tbody.innerHTML = '';

            for (const [nomType, info] of Object.entries(parType)) {{
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50/50 dark:hover:bg-white/[0.02] cursor-pointer";
                tr.onclick = function() {{ ouvrirModalFourn(nomType); }};

                tr.innerHTML = `
                    <td class="py-3 px-4">${{badgeTypeFournisseur(nomType)}}</td>
                    <td class="py-3 px-4 text-center font-mono font-bold text-slate-800 dark:text-slate-200">${{info.count}}</td>
                    <td class="py-3 px-4 text-right font-mono font-black text-rose-600 dark:text-rose-400">${{info.dettes.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                    <td class="py-3 px-4 text-right font-mono font-black text-emerald-600 dark:text-[#00F5A0]">${{info.avoirs.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</td>
                    <td class="py-3 px-4 text-center" onclick="event.stopPropagation()">
                        <button type="button" onclick="ouvrirModalFourn('${{nomType}}')" 
                                class="px-2.5 py-1 rounded-lg bg-[#184E68] hover:bg-sky-600 text-white text-[11px] font-bold transition flex items-center gap-1 mx-auto cursor-pointer shadow-xs">
                            <i data-lucide="list" class="w-3.5 h-3.5"></i>
                            <span>Détails</span>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            }}

            document.getElementById('tfootNbFourn').innerText = fournisseursFiltresActifs.length;
            document.getElementById('tfootDettesFourn').innerText = sumDettes.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
            document.getElementById('tfootAvoirsFourn').innerText = sumAvoirs.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});

            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function ouvrirModalFourn(type) {{
            typeModalFournActif = type;
            document.getElementById('modalRechercheLibreFourn').value = '';
            majPillsTypeFourn();
            appliquerFiltresModalFourn();
            document.getElementById('modal-dettes-fourn').classList.remove('hidden');
        }}

        function setModalTypeFourn(type) {{
            typeModalFournActif = type;
            majPillsTypeFourn();
            appliquerFiltresModalFourn();
        }}

        function majPillsTypeFourn() {{
            document.querySelectorAll('.btn-type-pill-fourn').forEach(btn => {{
                btn.className = "btn-type-pill-fourn px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition text-slate-300 hover:text-white shrink-0";
            }});
            const actif = document.getElementById('btn-type-fourn-' + typeModalFournActif);
            if (actif) actif.className = "btn-type-pill-fourn px-2.5 py-1 rounded-lg text-xs font-extrabold uppercase transition bg-sky-600 text-white shadow-sm shrink-0";
            document.getElementById('modal-type-titre-fourn').innerText = (typeModalFournActif === 'ALL') ? 'TOUS LES TYPES' : typeModalFournActif.toUpperCase();
        }}

        function appliquerFiltresModalFourn() {{
            const search = document.getElementById('modalRechercheLibreFourn').value.trim().toLowerCase();
            let lignes = fournisseursFiltresActifs;

            if (typeModalFournActif !== 'ALL') {{
                lignes = lignes.filter(f => f.type_fournisseur.toLowerCase() === typeModalFournActif.toLowerCase());
            }}

            if (search) {{
                lignes = lignes.filter(f => 
                    f.nom.toLowerCase().includes(search) || 
                    f.code.toLowerCase().includes(search) ||
                    f.telephone.toLowerCase().includes(search)
                );
            }}

            afficherLignesModalFourn(lignes);
        }}

        function afficherLignesModalFourn(lignes) {{
            const tbody = document.getElementById('modalTbodyFourn');
            const empty = document.getElementById('modalEmptyFourn');
            const compteur = document.getElementById('modalCompteurFourn');
            const totDettesEl = document.getElementById('modalTotalDettesVal');
            const totAvoirsEl = document.getElementById('modalTotalAvoirsVal');
            const totNetEl = document.getElementById('modalTotalNetVal');

            compteur.innerText = `${{lignes.length}} fournisseur(s)`;

            let sumDettes = 0;
            let sumAvoirs = 0;
            let sumNet = 0;

            if (lignes.length === 0) {{
                tbody.innerHTML = '';
                empty.classList.remove('hidden');
                totDettesEl.innerText = '0,00 DH';
                totAvoirsEl.innerText = '0,00 DH';
                totNetEl.innerText = '0,00 DH';
                return;
            }}

            empty.classList.add('hidden');
            let h = '';
            lignes.forEach(f => {{
                sumDettes += f.dette;
                sumAvoirs += f.avoir;
                sumNet += f.solde_net;

                h += `
                <tr class="hover:bg-white/[0.04] transition-colors border-b border-[#183042]/40">
                    <td class="py-2.5 px-4 font-mono font-bold text-sky-400 text-xs">${{htmlEscape(f.code)}}</td>
                    <td class="py-2.5 px-4 font-bold text-slate-100 uppercase">${{htmlEscape(f.nom)}}</td>
                    <td class="py-2.5 px-4 text-center">${{badgeTypeFournisseur(f.type_fournisseur)}}</td>
                    <td class="py-2.5 px-4 text-right font-mono text-slate-300 font-semibold">${{f.total_achats.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }})}} DH</td>
                    <td class="py-2.5 px-4 text-right font-mono text-teal-400 font-semibold">${{f.total_paye.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }})}} DH</td>
                    <td class="py-2.5 px-4 text-right font-mono font-black text-rose-500">${{f.dette.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }})}} DH</td>
                    <td class="py-2.5 px-4 text-right font-mono font-black text-emerald-400">${{f.avoir.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }})}} DH</td>
                    <td class="py-2.5 px-4 text-right font-mono font-black text-white">${{f.solde_net.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }})}} DH</td>
                    <td class="py-2.5 px-4 text-center">
                        <a href="/fournisseurs?id=${{f.id}}" class="p-1.5 rounded-lg bg-white/5 hover:bg-sky-500/20 text-sky-400 inline-flex items-center justify-center transition" title="Ouvrir dossier fournisseur">
                            <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                        </a>
                    </td>
                </tr>
                `;
            }});

            tbody.innerHTML = h;
            totDettesEl.innerText = sumDettes.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
            totAvoirsEl.innerText = sumAvoirs.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
            totNetEl.innerText = sumNet.toLocaleString('fr-FR', {{ minimumFractionDigits: 2 }}) + ' DH';
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function toggleAgrandirModalFourn() {{
            const box = document.getElementById('modal-box-fourn');
            const icon = document.getElementById('icon-maximize-fourn');
            estPleinEcranFourn = !estPleinEcranFourn;

            if (estPleinEcranFourn) {{
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

        function fermerModalFourn() {{
            document.getElementById('modal-dettes-fourn').classList.add('hidden');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') fermerModalFourn();
        }});

        document.addEventListener('DOMContentLoaded', () => {{
            filtrerDirectFournisseurs();
        }});
    </script>
    """
    return HTMLResponse(layout(content, active_tab="centre_rapports", request=request))