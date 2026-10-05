# ==============================================================================
# FICHIER : pages/rapport_grand_livre.py (CORRIGÉ & ROBUSTE)
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
    if not date_str:
        return ""
    clean = str(date_str).strip().split(" ")[0]
    if "/" in clean:
        p = clean.split("/")
        if len(p) == 3:
            return f"{p[2]}-{p[1].zfill(2)}-{p[0].zfill(2)}"
    return clean

def formater_date_fr(date_str: str) -> str:
    iso = normaliser_date_iso(date_str)
    if not iso or len(iso) < 10:
        return date_str or "—"
    p = iso.split("-")
    return f"{p[2]}/{p[1]}/{p[0]}"

@router.get("/centre-rapports/grand-livre", response_class=HTMLResponse)
async def page_grand_livre(
    request: Request,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None
):
    today = datetime.now()
    d_debut_defaut = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    d_fin_defaut = today.strftime("%Y-%m-%d")

    val_debut = date_debut or d_debut_defaut
    val_fin = date_fin or d_fin_defaut

    conn = get_db_connection()

    # 1. Conversion directe en dictionnaires Python pour éviter l'erreur sqlite3.Row.get()
    clients_rows = [dict(r) for r in conn.execute("SELECT * FROM clients ORDER BY nom ASC").fetchall()]
    factures_rows = [dict(r) for r in conn.execute("SELECT * FROM factures_clients ORDER BY date_facture ASC, id ASC").fetchall()]
    encaissements_rows = [dict(r) for r in conn.execute("SELECT * FROM client_encaissements ORDER BY date_paiement ASC, id ASC").fetchall()]

    # 2. Fournisseurs & leurs écritures
    fournisseurs_rows = [dict(r) for r in conn.execute("SELECT * FROM fournisseurs ORDER BY nom ASC").fetchall()]
    achats_rows = [dict(r) for r in conn.execute("SELECT * FROM achats_fournisseurs ORDER BY date ASC, id ASC").fetchall()]
    reglements_rows = [dict(r) for r in conn.execute("SELECT * FROM reglements_fournisseurs ORDER BY date ASC, id ASC").fetchall()]

    conn.close()

    # =========================================================================
    # RECONSTITUTION CHRONOLOGIQUE DES COMPTES DE TIERS
    # =========================================================================
    tiers_data = []

    # A. TRAITEMENT DES CLIENTS
    for c in clients_rows:
        cid = c["id"]
        c_nom = (c.get("nom") or "Client Sans Nom").strip()
        c_code = (c.get("code") or f"CL{cid:03d}").strip()
        solde_actuel = float(c.get("solde") or 0.0)

        mouvements = []

        # Factures / Ventes à crédit -> DÉBIT
        for f in factures_rows:
            if f.get("client_id") == cid:
                d_brute = f.get("date_facture") or ""
                num_piece = f.get("numero_facture") or f"FAC-{f.get('id')}"
                if not num_piece.startswith("VC-") and not num_piece.startswith("FAC"):
                    num_piece = f"VC-{num_piece}"
                montant = float(f.get("montant_ttc") or 0.0)
                mouvements.append({
                    "date_iso": normaliser_date_iso(d_brute),
                    "date_fr": formater_date_fr(d_brute),
                    "num_piece": num_piece,
                    "libelle": f.get("notes") or "Vente à crédit",
                    "debit": montant,
                    "credit": 0.0
                })

        # Encaissements / Règlements -> CRÉDIT
        for e in encaissements_rows:
            if e.get("client_id") == cid:
                d_brute = e.get("date_paiement") or ""
                ref = (e.get("reference") or "").strip()
                num_piece = ref if ref else f"ENC-{e.get('id')}"
                mode = e.get("mode_paiement") or "Espèces"
                montant = float(e.get("montant") or 0.0)
                mouvements.append({
                    "date_iso": normaliser_date_iso(d_brute),
                    "date_fr": formater_date_fr(d_brute),
                    "num_piece": num_piece,
                    "libelle": f"Encaissement ({mode})",
                    "debit": 0.0,
                    "credit": montant
                })

        # Tri chronologique des écritures
        mouvements.sort(key=lambda x: (x["date_iso"], x["num_piece"]))

        tiers_data.append({
            "id": f"cli_{cid}",
            "type_tiers": "Client",
            "nom": c_nom,
            "code": c_code,
            "solde_initial": 0.0,
            "solde_actuel": solde_actuel,
            "mouvements": mouvements
        })

    # B. TRAITEMENT DES FOURNISSEURS
    for f in fournisseurs_rows:
        fid = f["id"]
        f_nom = (f.get("nom") or "Fournisseur").strip()
        f_code = (f.get("code") or f"FOUR-{fid:03d}").strip()
        solde_init = float(f.get("solde_initial") or 0.0)

        mouvements = []

        # Achats / BL -> CRÉDIT (dette envers le fournisseur)
        for a in achats_rows:
            if a.get("fournisseur_id") == fid:
                d_brute = a.get("date") or ""
                num_piece = a.get("numero_facture") or a.get("reference_bl") or f"BL-{a.get('id')}"
                montant = float(a.get("montant_total") or 0.0)
                prod = a.get("produit") or "Carburant"
                mouvements.append({
                    "date_iso": normaliser_date_iso(d_brute),
                    "date_fr": formater_date_fr(d_brute),
                    "num_piece": num_piece,
                    "libelle": f"Achat / BL ({prod})",
                    "debit": 0.0,
                    "credit": montant
                })

        # Règlements -> DÉBIT (diminution de la dette)
        for r in reglements_rows:
            if r.get("fournisseur_id") == fid:
                d_brute = r.get("date") or ""
                num_piece = r.get("reference_paiement") or f"REG-{r.get('id')}"
                mode = r.get("mode_paiement") or "Virement"
                montant = float(r.get("montant") or 0.0)
                mouvements.append({
                    "date_iso": normaliser_date_iso(d_brute),
                    "date_fr": formater_date_fr(d_brute),
                    "num_piece": num_piece,
                    "libelle": f"Règlement ({mode})",
                    "debit": montant,
                    "credit": 0.0
                })

        mouvements.sort(key=lambda x: (x["date_iso"], x["num_piece"]))

        # Calcul solde fournisseur actuel
        tot_ach = sum(m["credit"] for m in mouvements)
        tot_pay = sum(m["debit"] for m in mouvements)
        solde_fourn = (solde_init + tot_ach) - tot_pay

        tiers_data.append({
            "id": f"fourn_{fid}",
            "type_tiers": "Fournisseur",
            "nom": f_nom,
            "code": f_code,
            "solde_initial": solde_init,
            "solde_actuel": solde_fourn,
            "mouvements": mouvements
        })

    # Encodage sécurisé en Base64 pour le JS
    tiers_b64 = base64.b64encode(json.dumps(tiers_data).encode('utf-8')).decode('utf-8')

    content = f"""
    <div class="max-w-7xl mx-auto space-y-4 animate-in fade-in duration-150">
        
        <!-- 1. EN-TÊTE + BARRE DE FILTRES -->
        <div class="bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs space-y-3">
            
            <div class="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-[#183042]">
                <div class="flex items-center gap-2 text-xs font-black uppercase text-slate-800 dark:text-white tracking-wider">
                    <i data-lucide="filter" class="w-4 h-4 text-purple-500"></i>
                    <span>Filtres</span>
                </div>

                <div class="flex items-center gap-2">
                    <button type="button" onclick="basculerTousAccordions(true)" class="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-[#132738] dark:hover:bg-[#1b354d] text-slate-700 dark:text-slate-200 transition cursor-pointer">
                        Déplier Tout
                    </button>
                    <button type="button" onclick="basculerTousAccordions(false)" class="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-[#132738] dark:hover:bg-[#1b354d] text-slate-700 dark:text-slate-200 transition cursor-pointer">
                        Replier Tout
                    </button>
                    <a href="/centre-rapports" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-[#132738] text-slate-700 dark:text-slate-200 text-xs font-bold transition">
                        <i data-lucide="arrow-left" class="w-3.5 h-3.5"></i>
                        <span>Retour Hub</span>
                    </a>
                </div>
            </div>

            <!-- LES 4 CHAMPS DU FILTRE -->
            <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
                <div class="sm:col-span-3">
                    <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Société *</label>
                    <select id="filtreSociete" onchange="filtrerGrandLivre()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-black text-slate-900 dark:text-white outline-none">
                        <option value="PETROLAZ" selected>PETROLAZ</option>
                        <option value="OKAY">OKAY ENERGY</option>
                    </select>
                </div>

                <div class="sm:col-span-3">
                    <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Type de Tiers</label>
                    <select id="filtreTypeTiers" onchange="filtrerGrandLivre()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none cursor-pointer">
                        <option value="ALL" selected>Tous les tiers</option>
                        <option value="Client">Clients</option>
                        <option value="Fournisseur">Fournisseurs</option>
                    </select>
                </div>

                <div class="sm:col-span-3">
                    <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Date début</label>
                    <input type="date" id="filtreDateDebut" value="{val_debut}" onchange="filtrerGrandLivre()" oninput="filtrerGrandLivre()" 
                           class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold font-mono text-slate-900 dark:text-white outline-none cursor-pointer">
                </div>

                <div class="sm:col-span-3">
                    <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Date fin</label>
                    <input type="date" id="filtreDateFin" value="{val_fin}" onchange="filtrerGrandLivre()" oninput="filtrerGrandLivre()" 
                           class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold font-mono text-slate-900 dark:text-white outline-none cursor-pointer">
                </div>
            </div>

        </div>

        <!-- 2. CONTENEUR DES ACCORDÉONS TIERS -->
        <div id="grandLivreContainer" class="space-y-3.5">
        </div>

        <div id="emptyGrandLivre" class="hidden text-center py-16 bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-2xl text-slate-400 font-bold italic">
            Aucun mouvement enregistré pour la sélection et la période indiquées.
        </div>

    </div>

    <!-- MOTEUR JS INTERACTIF DU GRAND LIVRE -->
    <script>
        const RAW_TIERS_B64 = "{tiers_b64}";
        const TOUS_LES_TIERS = JSON.parse(decodeURIComponent(escape(atob(RAW_TIERS_B64))));

        let etatsAccordions = {{}};

        function basculerTousAccordions(ouvrir) {{
            document.querySelectorAll('.tier-content-box').forEach(el => {{
                el.classList.toggle('hidden', !ouvrir);
            }});
            document.querySelectorAll('.chevron-tier').forEach(icon => {{
                icon.style.transform = ouvrir ? 'rotate(180deg)' : 'rotate(0deg)';
            }});
        }}

        function toggleTier(tierId) {{
            const box = document.getElementById('box-' + tierId);
            const chevron = document.getElementById('chevron-' + tierId);
            if (!box) return;

            const estCache = box.classList.contains('hidden');
            box.classList.toggle('hidden', !estCache);
            etatsAccordions[tierId] = estCache;

            if (chevron) {{
                chevron.style.transform = estCache ? 'rotate(180deg)' : 'rotate(0deg)';
            }}
        }}

        function badgeTiers(type) {{
            if (type === 'Client') {{
                return '<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-100 text-sky-800 dark:bg-sky-500/20 dark:text-sky-300 border border-sky-300/40"><i data-lucide="user" class="w-3 h-3"></i> Client</span>';
            }}
            return '<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-[#E5A842] border border-amber-300/40"><i data-lucide="truck" class="w-3 h-3"></i> Fournisseur</span>';
        }}

        function filtrerGrandLivre() {{
            const fType = document.getElementById('filtreTypeTiers').value;
            const dDeb = document.getElementById('filtreDateDebut').value;
            const dFin = document.getElementById('filtreDateFin').value;

            const container = document.getElementById('grandLivreContainer');
            const emptyBox = document.getElementById('emptyGrandLivre');
            container.innerHTML = '';

            let nombreTiersAffiches = 0;

            TOUS_LES_TIERS.forEach(tier => {{
                // 1. Filtre type de tiers
                if (fType !== 'ALL' && tier.type_tiers !== fType) return;

                // 2. Filtre mouvements dans la période
                let mouvementsFiltres = [];
                let soldeInitialPeriode = tier.solde_initial || 0.0;

                tier.mouvements.forEach(m => {{
                    if (dDeb && m.date_iso && m.date_iso < dDeb) {{
                        if (tier.type_tiers === 'Client') {{
                            soldeInitialPeriode += (m.debit - m.credit);
                        }} else {{
                            soldeInitialPeriode += (m.credit - m.debit);
                        }}
                        return;
                    }}
                    if (dFin && m.date_iso && m.date_iso > dFin) return;

                    mouvementsFiltres.push(m);
                }});

                // Si aucun mouvement dans la période et aucun solde, on masque pour alléger
                if (mouvementsFiltres.length === 0 && Math.abs(soldeInitialPeriode) < 0.01 && Math.abs(tier.solde_actuel) < 0.01) {{
                    return;
                }}

                nombreTiersAffiches++;

                // CALCUL PROGRESSIF DU SOLDE LIGNE PAR LIGNE
                let soldeCourant = soldeInitialPeriode;
                let totalDebit = 0;
                let totalCredit = 0;

                let lignesTableHtml = '';

                mouvementsFiltres.forEach(m => {{
                    totalDebit += m.debit;
                    totalCredit += m.credit;

                    if (tier.type_tiers === 'Client') {{
                        soldeCourant += (m.debit - m.credit);
                    }} else {{
                        soldeCourant += (m.credit - m.debit);
                    }}

                    const debitStr = m.debit > 0 
                        ? `<span class="text-rose-600 dark:text-rose-400 font-bold">${{m.debit.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</span>`
                        : `<span class="text-slate-400">-</span>`;

                    const creditStr = m.credit > 0 
                        ? `<span class="text-emerald-600 dark:text-[#00F5A0] font-bold">${{m.credit.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</span>`
                        : `<span class="text-slate-400">-</span>`;

                    const soldeStr = `<span class="font-black text-slate-900 dark:text-white">${{soldeCourant.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</span>`;

                    lignesTableHtml += `
                    <tr class="hover:bg-slate-50 dark:hover:bg-white/[0.02] border-b border-slate-100 dark:border-[#183042]/50 text-xs">
                        <td class="py-2.5 px-4 font-mono text-slate-600 dark:text-slate-300">${{m.date_fr}}</td>
                        <td class="py-2.5 px-4 font-mono font-bold text-sky-600 dark:text-sky-400">${{htmlEscape(m.num_piece)}}</td>
                        <td class="py-2.5 px-4 text-slate-700 dark:text-slate-200">${{htmlEscape(m.libelle)}}</td>
                        <td class="py-2.5 px-4 text-right font-mono">${{debitStr}}</td>
                        <td class="py-2.5 px-4 text-right font-mono">${{creditStr}}</td>
                        <td class="py-2.5 px-4 text-right font-mono">${{soldeStr}}</td>
                    </tr>
                    `;
                }});

                if (mouvementsFiltres.length === 0) {{
                    lignesTableHtml = `<tr><td colspan="6" class="py-4 text-center text-slate-400 text-xs italic">Aucun mouvement sur la période sélectionnée.</td></tr>`;
                }}

                const soldeActuelAffiche = (mouvementsFiltres.length > 0) ? soldeCourant : soldeInitialPeriode;
                const estDeplie = etatsAccordions[tier.id] !== false;

                const cardHtml = `
                <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-2xl shadow-xs overflow-hidden transition-all duration-200">
                    
                    <!-- EN-TÊTE ACCORDÉON TIERS -->
                    <div onclick="toggleTier('${{tier.id}}')" class="px-4 py-3.5 flex items-center justify-between cursor-pointer select-none hover:bg-slate-50/70 dark:hover:bg-white/[0.02] border-b border-slate-100 dark:border-[#183042]/60 transition">
                        <div class="flex items-center gap-3">
                            <i id="chevron-${{tier.id}}" data-lucide="chevron-down" class="chevron-tier w-4 h-4 text-slate-400 transition-transform duration-200" style="transform: ${{estDeplie ? 'rotate(180deg)' : 'rotate(0deg)'}}"></i>
                            <div class="flex items-center gap-2">
                                <h3 class="font-black text-slate-900 dark:text-white text-xs sm:text-sm uppercase tracking-wide">
                                    ${{htmlEscape(tier.nom)}}
                                </h3>
                                ${{badgeTiers(tier.type_tiers)}}
                                <span class="text-[11px] font-mono text-slate-400 font-bold">(${{htmlEscape(tier.code)}})</span>
                            </div>
                        </div>

                        <!-- SOLDES EN HAUT À DROITE -->
                        <div class="flex items-center gap-4 text-xs font-mono">
                            <div class="text-slate-500 dark:text-slate-400">
                                Solde initial: <strong class="text-slate-800 dark:text-slate-200">${{soldeInitialPeriode.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</strong>
                            </div>
                            <span class="text-slate-300 dark:text-slate-700">|</span>
                            <div class="text-slate-500 dark:text-slate-400">
                                Solde actuel: <strong class="text-slate-900 dark:text-white font-black">${{soldeActuelAffiche.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}</strong>
                            </div>
                        </div>
                    </div>

                    <!-- TABLEAU DES MOUVEMENTS -->
                    <div id="box-${{tier.id}}" class="tier-content-box overflow-x-auto ${{estDeplie ? '' : 'hidden'}}">
                        <table class="w-full text-left min-w-[700px]">
                            <thead class="bg-slate-50 dark:bg-[#070E15] text-[10.5px] uppercase font-bold text-slate-400 border-b border-slate-200 dark:border-[#183042]">
                                <tr>
                                    <th class="py-2.5 px-4 w-28">DATE</th>
                                    <th class="py-2.5 px-4 w-32">N° PIÈCE</th>
                                    <th class="py-2.5 px-4">LIBELLÉ</th>
                                    <th class="py-2.5 px-4 text-right w-32">DÉBIT</th>
                                    <th class="py-2.5 px-4 text-right w-32">CRÉDIT</th>
                                    <th class="py-2.5 px-4 text-right w-32">SOLDE</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100 dark:divide-[#183042]/50 font-semibold">
                                ${{lignesTableHtml}}
                            </tbody>
                            <tfoot class="bg-slate-50/80 dark:bg-[#070E15] border-t border-slate-200 dark:border-[#183042] text-xs font-black">
                                <tr>
                                    <td colspan="3" class="py-2.5 px-4 text-right uppercase text-slate-900 dark:text-white">TOTAUX</td>
                                    <td class="py-2.5 px-4 text-right font-mono text-rose-600 dark:text-rose-400">
                                        ${{totalDebit.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}
                                    </td>
                                    <td class="py-2.5 px-4 text-right font-mono text-emerald-600 dark:text-[#00F5A0]">
                                        ${{totalCredit.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}
                                    </td>
                                    <td class="py-2.5 px-4 text-right font-mono text-slate-900 dark:text-white">
                                        ${{soldeActuelAffiche.toLocaleString('fr-FR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }})}}
                                    </td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>

                </div>
                `;

                container.insertAdjacentHTML('beforeend', cardHtml);
            }});

            emptyBox.classList.toggle('hidden', nombreTiersAffiches > 0);
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function htmlEscape(str) {{
            return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            filtrerGrandLivre();
        }});
    </script>
    """
    return HTMLResponse(layout(content, active_tab="centre_rapports", request=request))