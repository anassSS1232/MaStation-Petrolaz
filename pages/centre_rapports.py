# ==================================================
# FICHIER : .\pages\centre_rapports.py (CORRIGÉ SANS 404)
# ==================================================

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ui_utils import layout

router = APIRouter()

RAPPORTS_CONFIG = [
    {
        "id": "ventes_carburants",
        "titre": "Ventes Carburants & Pompes",
        "description": "Historique détaillé et volumes vendus par pistolet et période",
        "icone": "fuel",
        "gradient": "from-emerald-500 to-teal-600",
        "glow": "rgba(0, 245, 160, 0.35)",
        "disponible": True,
"url": "/centre-rapports/ventes-carburants"    },
    {
        "id": "encaissements",
        "titre": "Journal des Encaissements",
        "description": "Suivi des règlements clients, espèces, chèques et virements",
        "icone": "banknote",
        "gradient": "from-teal-400 to-emerald-600",
        "glow": "rgba(16, 185, 129, 0.35)",
        "disponible": True,
        "url": "/centre-rapports/encaissements"
    },
    {
        "id": "soldes_clients",
        "titre": "Soldes Clients",
        "description": "État des soldes et créances clients",
        "icone": "users",
        "gradient": "from-pink-500 to-rose-600",
        "glow": "rgba(244, 63, 94, 0.35)",
        "disponible": True,
        "url": "/centre-rapports/soldes-clients"
    },
    {
        "id": "dettes_fournisseurs",
        "titre": "Dettes Fournisseurs",
        "description": "Suivi des dettes et paiements fournisseurs",
        "icone": "truck",
        "gradient": "from-sky-400 to-cyan-500",
        "glow": "rgba(14, 165, 233, 0.35)",
        "disponible": True,
        "url": "/centre-rapports/dettes-fournisseurs"
    },
    {
        "id": "grand_livre",
        "titre": "Grand Livre des Tiers",
        "description": "Mouvements clients et fournisseurs par société avec solde progressif",
        "icone": "book-open",
        "gradient": "from-indigo-600 to-purple-600",
        "glow": "rgba(99, 102, 241, 0.35)",
        "disponible": True,
        "url": "/centre-rapports/grand-livre"
    },
   {
        "id": "etat_stocks",
        "titre": "État des Stocks & Citernes",
        "description": "Inventaire physique et mouvements de cuves",
        "icone": "warehouse",
        "gradient": "from-amber-400 to-orange-500",
        "glow": "rgba(251, 146, 60, 0.35)",
        "disponible": True,
        "url": "/centre-rapports/etat-stocks"
    },
    {
        "id": "benefices",
        "titre": "Marges & Rentabilité",
        "description": "Analyse de la rentabilité nette carburants et lubrifiants",
        "icone": "trending-up",
        "gradient": "from-pink-500 to-rose-600",
        "glow": "rgba(244, 63, 94, 0.35)",
        "disponible": False,
        "url": "#"
    },
    {
        "id": "transactions_bancaires",
        "titre": "Rapprochement Bancaire",
        "description": "Suivi des mouvements bancaires et remises de chèques",
        "icone": "landmark",
        "gradient": "from-purple-500 to-indigo-600",
        "glow": "rgba(168, 85, 247, 0.35)",
        "disponible": False,
        "url": "#"
    }
]

@router.get("/centre-rapports", response_class=HTMLResponse)
async def hub_rapports_page(request: Request):
    cards_html = ""
    for r in RAPPORTS_CONFIG:
        if r["disponible"]:
            badge_html = """
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-500/15 text-emerald-600 dark:text-[#00F5A0] border border-emerald-500/30">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Disponible
            </span>
            """
            click_attr = f'href="{r["url"]}"'
        else:
            badge_html = """
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-500/15 text-slate-500 dark:text-slate-400 border border-slate-500/30">
                Bientôt disponible
            </span>
            """
            click_attr = 'href="javascript:void(0)" onclick="alert(\'Ce module de rapport approfondi est en cours d\\\'intégration et sera actif lors de la prochaine mise à jour.\')"'

        cards_html += f"""
        <a {click_attr} 
           class="group relative overflow-hidden bg-white/80 dark:bg-[#0D1624]/85 hover:dark:bg-[#121E31]/90 backdrop-blur-xl border border-slate-200/90 dark:border-white/10 hover:border-slate-400 dark:hover:border-white/25 rounded-2xl p-4 sm:p-5 shadow-lg hover:shadow-2xl hover:-translate-y-1 transition-all duration-200 flex flex-col justify-between">
            
            <div class="flex items-start gap-4">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br {r['gradient']} flex items-center justify-center text-white shrink-0 shadow-md group-hover:scale-105 transition-transform duration-200"
                     style="box-shadow: 0 8px 16px {r['glow']};">
                    <i data-lucide="{r['icone']}" class="w-6 h-6 stroke-[2.2]"></i>
                </div>

                <div class="space-y-1 pr-1">
                    <h3 class="text-sm font-black text-slate-900 dark:text-white tracking-tight group-hover:text-sky-500 dark:group-hover:text-sky-400 transition-colors">
                        {r['titre']}
                    </h3>
                    <p class="text-xs text-slate-500 dark:text-slate-400 leading-snug line-clamp-2">
                        {r['description']}
                    </p>
                </div>
            </div>

            <div class="mt-4 pt-3 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                {badge_html}
                <i data-lucide="arrow-right" class="w-4 h-4 text-slate-400 group-hover:text-sky-400 group-hover:translate-x-1 transition-all"></i>
            </div>
        </a>
        """

    content = f"""
    <div class="max-w-7xl mx-auto px-3 sm:px-6 py-4 space-y-6 animate-in fade-in duration-300">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200/80 dark:border-white/10">
            <div>
                <h1 class="text-lg sm:text-xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-2.5">
                    <i data-lucide="bar-chart-3" class="w-5 h-5 text-sky-500"></i>
                    Centre de Rapports & Registres
                </h1>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Accédez aux registres opérationnels et visualisez l'état comptable de la station.
                </p>
            </div>
            
            <div class="relative w-full sm:w-64">
                <i data-lucide="search" class="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
                <input type="text" id="reportSearch" placeholder="Rechercher un rapport..." 
                       onkeyup="filterReports()"
                       class="w-full pl-8 pr-3 py-1.5 bg-slate-100 dark:bg-black/30 border border-slate-300 dark:border-white/10 rounded-xl text-xs text-slate-900 dark:text-white placeholder-slate-400 outline-none focus:border-sky-500 transition">
            </div>
        </div>

        <div id="reportsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {cards_html}
        </div>
    </div>

    <script>
        function filterReports() {{
            const input = document.getElementById('reportSearch').value.toLowerCase();
            const cards = document.querySelectorAll('#reportsGrid > a');
            cards.forEach(card => {{
                const title = card.querySelector('h3').innerText.toLowerCase();
                const desc = card.querySelector('p').innerText.toLowerCase();
                if (title.includes(input) || desc.includes(input)) {{
                    card.classList.remove('hidden');
                }} else {{
                    card.classList.add('hidden');
                }}
            }});
        }}
    </script>
    """
    return HTMLResponse(layout(content, "centre_rapports", request=request))