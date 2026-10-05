# pages/rapport_historique.py
import json
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ui_utils import layout
from database import get_db_connection, init_db

router = APIRouter()

@router.get("/rapport-quart/historique", response_class=HTMLResponse)
async def page_historique(request: Request):
    init_db()
    conn = get_db_connection()
    historique_clotures = conn.execute("SELECT * FROM cloture_quart ORDER BY id DESC").fetchall()

    clotures_list = [{
        "id": c["id"],
        "date": c["date"],
        "operateur": c["operateur"] or "Agent",
        "especes": float(c["especes"] or 0.0),
        "tpe": float(c["tpe"] or 0.0),
        "credits": float(c["credits"] or 0.0),
        "total_net": float(c["total_net"] or 0.0),
        "fusion": float(c["fusion"] or 0.0),
        "resultat": float(c["resultat"] or 0.0),
        "credits_json": c["credits_json"] or "[]"
    } for c in historique_clotures]
    conn.close()

    content = f"""
    <div class="h-full flex flex-col gap-2.5 animate-in fade-in duration-200">
        <!-- BARRE FILTRES -->
        <div class="bg-white dark:bg-[#0E1B26] p-2 rounded-xl border border-slate-200 dark:border-[#183042] flex flex-wrap items-center justify-between gap-2 shadow-xs shrink-0">
            <div class="flex flex-wrap items-center gap-1.5">
                <div class="flex items-center gap-1 bg-slate-50 dark:bg-[#070E15] border border-slate-200 dark:border-[#183042] px-2 py-1 rounded-lg">
                    <span class="text-[9px] font-bold text-slate-400 uppercase">Date:</span>
                    <input type="date" id="filtreDateQuart" oninput="filtrerHistoriqueQuarts()" class="bg-transparent text-slate-900 dark:text-white text-xs outline-none font-mono">
                </div>

                <div class="flex items-center gap-1 bg-slate-50 dark:bg-[#070E15] border border-slate-200 dark:border-[#183042] px-2 py-1 rounded-lg">
                    <span class="text-[9px] font-bold text-slate-400 uppercase">Agent:</span>
                    <input type="text" id="filtreAgentQuart" oninput="filtrerHistoriqueQuarts()" placeholder="Tous..." class="bg-transparent text-slate-900 dark:text-white text-xs outline-none font-bold w-24 sm:w-32">
                </div>

                <div class="flex items-center gap-1 bg-slate-50 dark:bg-[#070E15] border border-slate-200 dark:border-[#183042] px-2 py-1 rounded-lg">
                    <span class="text-[9px] font-bold text-slate-400 uppercase">Bilan:</span>
                    <select id="filtreStatutQuart" onchange="filtrerHistoriqueQuarts()" class="bg-transparent text-slate-900 dark:text-white text-xs outline-none font-bold">
                        <option value="ALL" class="bg-white dark:bg-[#0E1B26]">Tous</option>
                        <option value="EQUILIBRE" class="bg-white dark:bg-[#0E1B26]">Équilibré (0.00)</option>
                        <option value="SURPLUS" class="bg-white dark:bg-[#0E1B26]">Surplus (+)</option>
                        <option value="DEFICIT" class="bg-white dark:bg-[#0E1B26]">Manquant (-)</option>
                    </select>
                </div>

                <button onclick="resetFiltresQuarts()" title="Réinitialiser" class="p-1.5 bg-slate-100 dark:bg-[#070E15] text-slate-600 dark:text-slate-300 rounded-lg border border-slate-200 dark:border-[#183042] hover:bg-slate-200 transition">
                    <i data-lucide="rotate-ccw" class="w-3 h-3"></i>
                </button>
            </div>

            <div class="text-[11px] font-mono text-slate-400 pr-1">
                <span id="countQuartsAffiches" class="text-sky-500 font-bold">0</span> quart(s)
            </div>
        </div>

        <!-- TABLE DES CLÔTURES -->
        <div class="bg-white dark:bg-[#0E1B26] rounded-xl border border-slate-200 dark:border-[#183042] overflow-hidden shadow-xs flex-1 flex flex-col">
            <div class="overflow-x-auto flex-1">
                <table class="w-full text-left min-w-[780px]">
                    <thead class="bg-slate-50 dark:bg-[#070E15] text-[9.5px] uppercase font-bold text-slate-400 sticky top-0 border-b border-slate-200 dark:border-[#183042]">
                        <tr>
                            <th class="py-2 px-3">Date</th>
                            <th class="py-2 px-3">Agent</th>
                            <th class="py-2 px-3 text-right">Espèces</th>
                            <th class="py-2 px-3 text-right">TPE</th>
                            <th class="py-2 px-3 text-right">Crédits</th>
                            <th class="py-2 px-3 text-right font-black">Total Net</th>
                            <th class="py-2 px-3 text-right text-sky-500 font-bold">Fusion Pompes</th>
                            <th class="py-2 px-3 text-center">Écart</th>
                        </tr>
                    </thead>
                    <tbody id="tableBodyHistoriqueQuarts" class="divide-y divide-slate-100 dark:divide-[#183042]/50 font-mono text-xs"></tbody>
                </table>
            </div>

            <div class="p-2 border-t border-slate-200 dark:border-[#183042] bg-slate-50 dark:bg-[#070E15] flex flex-wrap justify-between items-center gap-2 shrink-0 font-mono text-xs">
                <div class="text-slate-500 dark:text-slate-400 text-[11px]">
                    Total Encaissé : <span id="sommeTotalNetQuarts" class="font-black text-slate-900 dark:text-white">0.00 DH</span> | 
                    Total Fusion : <span id="sommeFusionQuarts" class="font-black text-sky-500">0.00 DH</span>
                </div>
                <div class="text-[11px]">
                    Écart Global : <span id="sommeEcartQuarts" class="font-black">0.00 DH</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const TOUTES_LES_CLOTURES = {json.dumps(clotures_list)};
        let cloturesFiltrees = [];

        function resetFiltresQuarts() {{
            document.getElementById('filtreDateQuart').value = "";
            document.getElementById('filtreAgentQuart').value = "";
            document.getElementById('filtreStatutQuart').value = "ALL";
            filtrerHistoriqueQuarts();
        }}

        function filtrerHistoriqueQuarts() {{
            const fDate = document.getElementById('filtreDateQuart').value;
            const fAgent = (document.getElementById('filtreAgentQuart').value || '').trim().toLowerCase();
            const fStatut = document.getElementById('filtreStatutQuart').value;

            cloturesFiltrees = [];
            let sumNet = 0, sumFusion = 0, sumEcart = 0;

            for (let i = 0; i < TOUTES_LES_CLOTURES.length; i++) {{
                const c = TOUTES_LES_CLOTURES[i];
                if (fDate && !c.date.startsWith(fDate)) continue;
                if (fAgent && !c.operateur.toLowerCase().includes(fAgent)) continue;

                const res = c.resultat;
                if (fStatut === 'EQUILIBRE' && Math.abs(res) >= 0.01) continue;
                if (fStatut === 'SURPLUS' && res <= 0.01) continue;
                if (fStatut === 'DEFICIT' && res >= -0.01) continue;

                cloturesFiltrees.push(c);
                sumNet += c.total_net;
                sumFusion += c.fusion;
                sumEcart += c.resultat;
            }}

            document.getElementById('countQuartsAffiches').innerText = cloturesFiltrees.length;
            document.getElementById('sommeTotalNetQuarts').innerText = sumNet.toLocaleString('fr-FR', {{minimumFractionDigits: 2}}) + ' DH';
            document.getElementById('sommeFusionQuarts').innerText = sumFusion.toLocaleString('fr-FR', {{minimumFractionDigits: 2}}) + ' DH';
            
            const ecartEl = document.getElementById('sommeEcartQuarts');
            if (Math.abs(sumEcart) < 0.01) {{
                ecartEl.className = "font-black text-emerald-500";
                ecartEl.innerText = "0.00 DH (Équilibré)";
            }} else if (sumEcart > 0) {{
                ecartEl.className = "font-black text-emerald-500";
                ecartEl.innerText = "+" + sumEcart.toLocaleString('fr-FR', {{minimumFractionDigits: 2}}) + " DH (Surplus)";
            }} else {{
                ecartEl.className = "font-black text-rose-500";
                ecartEl.innerText = sumEcart.toLocaleString('fr-FR', {{minimumFractionDigits: 2}}) + " DH (Manquant)";
            }}
            rendreTableauQuarts();
        }}

        function rendreTableauQuarts() {{
            const tbody = document.getElementById('tableBodyHistoriqueQuarts');
            if (!tbody) return;
            if (cloturesFiltrees.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="8" class="py-8 text-center text-slate-400 font-sans text-xs italic">Aucune clôture de quart trouvée.</td></tr>`;
                return;
            }}

            let html = "";
            for (let i = 0; i < cloturesFiltrees.length; i++) {{
                const c = cloturesFiltrees[i];
                const res = c.resultat;
                let badge = Math.abs(res) < 0.01 
                    ? '<span class="px-2 py-0.2 rounded-full bg-emerald-500/15 text-emerald-500 font-bold text-[9.5px]">Équilibré</span>'
                    : (res > 0 ? `<span class="px-2 py-0.2 rounded-full bg-emerald-500/15 text-emerald-500 font-bold text-[9.5px]">+${{res.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}} DH</span>`
                               : `<span class="px-2 py-0.2 rounded-full bg-rose-500/15 text-rose-500 font-bold text-[9.5px]">${{res.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}} DH</span>`);

                html += `
                <tr class="border-b border-slate-100 dark:border-[#183042]/50 hover:bg-slate-50/80 dark:hover:bg-white/[0.02]">
                    <td class="py-2 px-3 font-sans text-slate-500 text-[11px]">${{c.date}}</td>
                    <td class="py-2 px-3 font-sans font-black text-slate-800 dark:text-white uppercase text-[11px]">${{c.operateur}}</td>
                    <td class="py-2 px-3 text-right text-emerald-600 dark:text-[#00F5A0] font-bold text-[11px]">+${{c.especes.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}}</td>
                    <td class="py-2 px-3 text-right text-sky-500 font-semibold text-[11px]">+${{c.tpe.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}}</td>
                    <td class="py-2 px-3 text-right text-amber-500 font-semibold text-[11px]">+${{c.credits.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}}</td>
                    <td class="py-2 px-3 text-right font-black text-slate-900 dark:text-white text-[11px]">${{c.total_net.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}} DH</td>
                    <td class="py-2 px-3 text-right font-bold text-sky-600 dark:text-[#38BDF8] text-[11px]">${{c.fusion.toLocaleString('fr-FR', {{minimumFractionDigits: 2}})}} DH</td>
                    <td class="py-2 px-3 text-center">${{badge}}</td>
                </tr>
                `;
            }}
            tbody.innerHTML = html;
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            filtrerHistoriqueQuarts();
        }});
    </script>
    """
    return HTMLResponse(layout(content, "historique", request=request))