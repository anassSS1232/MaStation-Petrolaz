# pages/rapport.py
import json
import html
from datetime import datetime
from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse

from ui_utils import layout
from database import get_db_connection, init_db

from pages.rapport_compteurs import router as compteurs_router
from pages.rapport_historique import router as historique_router

router = APIRouter()
router.include_router(compteurs_router)
router.include_router(historique_router)

@router.get("/rapport-quart", response_class=HTMLResponse)
async def rapport_page(request: Request, tab: str = "supervision", success: bool = False, msg: str = ""):
    if tab == "compteurs":
        return RedirectResponse("/rapport-quart/compteurs")
    if tab == "historique":
        return RedirectResponse("/rapport-quart/historique")

    init_db()
    conn = get_db_connection()

    user = getattr(request.state, "user", None)
    nom_operateur = (user.get("nom_complet", "Opérateur") if user else "Opérateur").upper()
    role = str(user.get("role", "employe") if user else "employe").lower()
    is_admin = role in ["admin", "administrateur", "gerant", "comptable"]
    today_sql = datetime.now().strftime("%Y-%m-%d")

    p_ssp = conn.execute("SELECT prix FROM prix_vente WHERE produit IN ('SSP', 'Essence', 'Sans Plomb') AND statut='ACTIF' ORDER BY id DESC LIMIT 1").fetchone()
    p_go = conn.execute("SELECT prix FROM prix_vente WHERE produit IN ('GAZOIL', 'Gasoil', 'GO', 'Diesel', 'Gasoil 10') AND statut='ACTIF' ORDER BY id DESC LIMIT 1").fetchone()
    prix_ssp = float(p_ssp['prix']) if p_ssp else 15.340
    prix_go = float(p_go['prix']) if p_go else 14.280

    pompes_ssp = [1, 2, 3, 4, 6, 8]
    pompes_go = [1, 2, 3, 4, 5, 7]

    def get_pump_vol(c_type, p_id):
        types_c = ('ESS', 'SSP') if c_type in ('ESS', 'SSP') else ('DIE', 'GO')
        row = conn.execute("""
            SELECT SUM(volume) as total_vol FROM transactions_jour 
            WHERE date_releve = ? AND type IN (?, ?) AND pump_id = ?
        """, (today_sql, types_c[0], types_c[1], p_id)).fetchone()
        return float(row['total_vol']) if (row and row['total_vol']) else 0.0

    total_ssp_l = sum(get_pump_vol('SSP', p) for p in pompes_ssp)
    total_go_l = sum(get_pump_vol('GO', p) for p in pompes_go)
    total_ssp_dh = total_ssp_l * prix_ssp
    total_go_dh = total_go_l * prix_go
    total_fusion_theorique = total_ssp_dh + total_go_dh
    total_volume_total = (total_ssp_l + total_go_l) or 1.0
    pct_vol_ssp = (total_ssp_l / total_volume_total) * 100
    pct_vol_go = (total_go_l / total_volume_total) * 100

    alert_banner = ""
    if success:
        alert_banner = f"""
        <div class="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-4 py-3 rounded-2xl text-xs font-semibold flex items-center justify-between shadow-lg shadow-emerald-950/20 mb-3 backdrop-blur-md">
            <span class="flex items-center gap-2">
                <span class="p-1 rounded-full bg-emerald-500/20 text-emerald-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
                </span>
                {html.escape(msg or 'Opération enregistrée avec succès !')}
            </span>
            <a href="/rapport-quart" class="text-xs text-emerald-400/80 hover:text-emerald-300 font-bold px-2 py-1">✕</a>
        </div>
        """

    if is_admin:
        derniere = conn.execute("SELECT * FROM cloture_quart ORDER BY id DESC LIMIT 1").fetchone()
        conn.close()

        d_op = derniere['operateur'] if derniere else "ANASS"
        d_date_full = derniere['date'] if derniere else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_parts = d_date_full.split()
        d_date_only = date_parts[0] if len(date_parts) > 0 else today_sql
        d_time_only = date_parts[1] if len(date_parts) > 1 else "00:00:00"

        d_esp = float(derniere['especes'] or 0) if derniere else 0.0
        d_tpe = float(derniere['tpe'] or 0) if derniere else 0.0
        d_cred = float(derniere['credits'] or 0) if derniere else 0.0
        d_fus = float(derniere['fusion'] or 0) if derniere else 0.0
        d_net = float(derniere['total_net'] or 0) if derniere else (d_esp + d_tpe + d_cred)
        d_res = float(derniere['resultat'] or 0) if derniere else (d_net - d_fus)

        total_pay = d_esp + d_tpe + d_cred
        pct_especes = (d_esp / total_pay * 100) if total_pay > 0 else 100.0
        pct_digital = ((d_tpe + d_cred) / total_pay * 100) if total_pay > 0 else 0.0

        if abs(d_res) < 0.01:
            ecart_montant_str = "0.00 DH"
            ecart_label_str = "CAISSE CONFORME"
            ecart_glow = "from-emerald-500/10 to-teal-500/5"
            ecart_text_color = "text-emerald-400"
            badge_class = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
        elif d_res > 0:
            ecart_montant_str = f"+{d_res:,.2f} DH"
            ecart_label_str = "SURPLUS EN CAISSE"
            ecart_glow = "from-emerald-500/20 via-emerald-950/20 to-transparent"
            ecart_text_color = "text-[#00F5A0]"
            badge_class = "bg-emerald-500/20 text-[#00F5A0] border-emerald-500/40 shadow-emerald-500/10"
        else:
            ecart_montant_str = f"{d_res:,.2f} DH"
            ecart_label_str = "MANQUANT / DÉFICIT"
            ecart_glow = "from-rose-500/20 via-rose-950/20 to-transparent"
            ecart_text_color = "text-rose-400"
            badge_class = "bg-rose-500/20 text-rose-400 border-rose-500/40 shadow-rose-500/10"

        content = f"""
        <div class="h-full flex flex-col gap-3.5 animate-in fade-in duration-300">
            {alert_banner}

            <div class="space-y-3.5 flex-1 overflow-y-auto pr-0.5 custom-scrollbar">
                
                <div class="grid grid-cols-1 md:grid-cols-12 gap-3.5">
                    
                    <div class="md:col-span-4 rounded-2xl bg-slate-900/70 border border-slate-800/90 backdrop-blur-xl p-4 flex flex-col justify-between shadow-xl shadow-black/20 relative overflow-hidden group">
                        <div class="absolute top-0 right-0 w-32 h-32 bg-sky-500/5 rounded-full blur-2xl pointer-events-none group-hover:bg-sky-500/10 transition-all duration-500"></div>
                        <div>
                            <div class="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
                                <span class="text-[11px] font-extrabold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                                    <span class="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse"></span>
                                    Détails du Quart
                                </span>
                                <span class="text-[10px] font-mono font-medium px-2 py-0.5 rounded-full bg-slate-800/80 text-slate-300 border border-slate-700/50">
                                    POSTE CLÔTURÉ
                                </span>
                            </div>

                            <div class="space-y-2.5">
                                <div class="flex items-center justify-between text-xs">
                                    <span class="text-slate-400 text-[11px] flex items-center gap-1.5">
                                        <svg class="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                                        Opérateur
                                    </span>
                                    <span class="font-bold text-white tracking-wide uppercase px-2 py-0.5 rounded-md bg-slate-800/60">{html.escape(d_op)}</span>
                                </div>
                                <div class="flex items-center justify-between text-xs">
                                    <span class="text-slate-400 text-[11px] flex items-center gap-1.5">
                                        <svg class="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                                        Date
                                    </span>
                                    <span class="font-mono font-semibold text-slate-200">{d_date_only}</span>
                                </div>
                                <div class="flex items-center justify-between text-xs">
                                    <span class="text-slate-400 text-[11px] flex items-center gap-1.5">
                                        <svg class="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                                        Heure
                                    </span>
                                    <span class="font-mono font-semibold text-slate-300">{d_time_only}</span>
                                </div>
                            </div>
                        </div>

                        <div class="pt-3 mt-3 border-t border-slate-800/80 flex items-center justify-between bg-slate-950/40 -mx-4 -mb-4 px-4 py-3">
                            <span class="text-[11px] text-slate-400 font-medium">Pompes (Aujourd'hui)</span>
                            <span class="font-mono font-black text-xs text-sky-300">{total_fusion_theorique:,.2f} MAD</span>
                        </div>
                    </div>

                    <div class="md:col-span-5 rounded-2xl bg-slate-900/70 border border-slate-800/90 backdrop-blur-xl p-4 flex flex-col justify-between shadow-xl shadow-black/20">
                        <div class="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
                            <span class="text-[11px] font-extrabold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                                Chiffres Clés Financiers
                            </span>
                            <span class="text-[10px] font-mono text-slate-500">DH (MAD)</span>
                        </div>

                        <div class="grid grid-cols-2 gap-2.5 flex-1">
                            <div class="bg-gradient-to-br from-slate-800/50 to-slate-900/60 border border-slate-700/50 rounded-xl p-2.5 flex flex-col justify-between hover:border-slate-600/70 transition-all">
                                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Cash Déclaré</span>
                                <span class="text-sm font-black font-mono text-emerald-400 tracking-tight mt-1">{d_esp:,.2f} <span class="text-[10px] font-normal text-slate-500">DH</span></span>
                            </div>

                            <div class="bg-gradient-to-br from-slate-800/50 to-slate-900/60 border border-slate-700/50 rounded-xl p-2.5 flex flex-col justify-between hover:border-slate-600/70 transition-all">
                                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">TPE + Crédits</span>
                                <span class="text-sm font-black font-mono text-cyan-400 tracking-tight mt-1">{(d_tpe + d_cred):,.2f} <span class="text-[10px] font-normal text-slate-500">DH</span></span>
                            </div>

                            <div class="bg-gradient-to-br from-slate-800/70 to-slate-900/80 border border-emerald-500/20 rounded-xl p-2.5 flex flex-col justify-between shadow-inner">
                                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Encaissé</span>
                                <span class="text-sm font-black font-mono text-white tracking-tight mt-1">{d_net:,.2f} <span class="text-[10px] font-normal text-slate-500">DH</span></span>
                            </div>

                            <div class="bg-gradient-to-br from-slate-800/50 to-slate-900/60 border border-slate-700/50 rounded-xl p-2.5 flex flex-col justify-between hover:border-slate-600/70 transition-all">
                                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Ventes Pompes Théo</span>
                                <span class="text-sm font-black font-mono text-slate-200 tracking-tight mt-1">{d_fus:,.2f} <span class="text-[10px] font-normal text-slate-500">DH</span></span>
                            </div>
                        </div>
                    </div>

                    <div class="md:col-span-3 rounded-2xl bg-gradient-to-b {ecart_glow} bg-slate-900/80 border border-slate-800/90 backdrop-blur-xl p-4 flex flex-col justify-between shadow-xl shadow-black/20 text-center relative overflow-hidden">
                        <div class="flex items-center justify-between pb-2 border-b border-slate-800/70">
                            <span class="text-[11px] font-extrabold uppercase tracking-wider text-slate-400 text-left">Audit Caisse</span>
                            <span class="px-2 py-0.5 rounded-full text-[9px] font-extrabold border {badge_class}">
                                {ecart_label_str}
                            </span>
                        </div>

                        <div class="my-auto py-3">
                            <div class="text-3xl font-black font-mono tracking-tight {ecart_text_color} drop-shadow-[0_0_15px_rgba(0,245,160,0.2)]">
                                {ecart_montant_str}
                            </div>
                            <p class="text-[10px] text-slate-400 mt-1">Différence Encaissé vs Compteurs</p>
                        </div>

                        <div class="pt-2 border-t border-slate-800/70 text-[10px] font-mono text-slate-400 flex items-center justify-between">
                            <span>Réel: <b class="text-slate-200">{d_net:,.0f}</b></span>
                            <span class="text-slate-600">|</span>
                            <span>Théo: <b class="text-slate-200">{d_fus:,.0f}</b></span>
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-12 gap-3.5">
                    
                    <div class="md:col-span-5 rounded-2xl bg-slate-900/70 border border-slate-800/90 backdrop-blur-xl p-4 flex flex-col justify-between shadow-xl shadow-black/20">
                        <div>
                            <div class="flex items-center justify-between pb-2.5 border-b border-slate-800/80 mb-3">
                                <span class="text-[11px] font-extrabold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                                    <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/></svg>
                                    Mix de Règlements
                                </span>
                                <span class="text-[10px] text-slate-500 font-mono">100% Clôturé</span>
                            </div>

                            <div class="w-full h-3 bg-slate-800 rounded-full overflow-hidden flex p-0.5 gap-0.5 shadow-inner mb-3">
                                <div style="width: {pct_especes:.1f}%" class="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-l-full transition-all duration-500" title="Espèces : {pct_especes:.1f}%"></div>
                                <div style="width: {pct_digital:.1f}%" class="h-full bg-gradient-to-r from-sky-500 to-blue-500 rounded-r-full transition-all duration-500" title="Digital/Crédits : {pct_digital:.1f}%"></div>
                            </div>

                            <div class="grid grid-cols-2 gap-2">
                                <div class="p-2.5 rounded-xl bg-slate-800/40 border border-slate-700/50 flex flex-col justify-between">
                                    <span class="flex items-center gap-1.5 text-[10px] font-semibold text-slate-300">
                                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                                        Espèces
                                    </span>
                                    <div class="mt-1 flex items-baseline justify-between">
                                        <span class="font-mono font-black text-sm text-white">{pct_especes:.1f}%</span>
                                        <span class="font-mono text-[10px] text-slate-400">{d_esp:,.0f} DH</span>
                                    </div>
                                </div>

                                <div class="p-2.5 rounded-xl bg-slate-800/40 border border-slate-700/50 flex flex-col justify-between">
                                    <span class="flex items-center gap-1.5 text-[10px] font-semibold text-slate-300">
                                        <span class="w-2 h-2 rounded-full bg-sky-400"></span>
                                        Digital / Crédits
                                    </span>
                                    <div class="mt-1 flex items-baseline justify-between">
                                        <span class="font-mono font-black text-sm text-white">{pct_digital:.1f}%</span>
                                        <span class="font-mono text-[10px] text-slate-400">{(d_tpe + d_cred):,.0f} DH</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="pt-3 mt-3 border-t border-slate-800/80 flex justify-between items-center text-xs">
                            <span class="text-slate-400 font-medium">Chiffre d'Affaires Jour</span>
                            <span class="font-mono font-black text-sm text-white">{total_fusion_theorique:,.2f} <span class="text-[10px] text-emerald-400 font-normal">MAD</span></span>
                        </div>
                    </div>

                    <div class="md:col-span-7 rounded-2xl bg-slate-900/70 border border-slate-800/90 backdrop-blur-xl p-4 flex flex-col justify-between shadow-xl shadow-black/20">
                        <div class="flex items-center justify-between pb-2.5 border-b border-slate-800/80 mb-3">
                            <span class="text-[11px] font-extrabold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                                <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                                Bilan des Carburants Distribués
                            </span>
                            <span class="text-[10px] text-slate-500 font-mono">Litres & Chiffre d'Affaires</span>
                        </div>

                        <div class="space-y-3">
                            <div class="p-3 rounded-xl bg-slate-800/30 border border-slate-700/40 hover:bg-slate-800/50 transition">
                                <div class="flex items-center justify-between mb-1.5">
                                    <div class="flex items-center gap-2">
                                        <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]"></span>
                                        <span class="text-xs font-bold text-white tracking-wide">Super Sans Plomb (SSP)</span>
                                    </div>
                                    <div class="font-mono text-xs">
                                        <b class="text-white font-black">{total_ssp_l:,.2f} L</b>
                                        <span class="text-slate-500 font-normal mx-1">•</span>
                                        <span class="text-emerald-400 font-bold">{total_ssp_dh:,.2f} DH</span>
                                    </div>
                                </div>
                                <div class="w-full bg-slate-950/60 h-1.5 rounded-full overflow-hidden">
                                    <div style="width: {pct_vol_ssp:.1f}%" class="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full"></div>
                                </div>
                            </div>

                            <div class="p-3 rounded-xl bg-slate-800/30 border border-slate-700/40 hover:bg-slate-800/50 transition">
                                <div class="flex items-center justify-between mb-1.5">
                                    <div class="flex items-center gap-2">
                                        <span class="w-2.5 h-2.5 rounded-full bg-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.6)]"></span>
                                        <span class="text-xs font-bold text-white tracking-wide">Diesel (Gasoil 10)</span>
                                    </div>
                                    <div class="font-mono text-xs">
                                        <b class="text-white font-black">{total_go_l:,.2f} L</b>
                                        <span class="text-slate-500 font-normal mx-1">•</span>
                                        <span class="text-sky-400 font-bold">{total_go_dh:,.2f} DH</span>
                                    </div>
                                </div>
                                <div class="w-full bg-slate-950/60 h-1.5 rounded-full overflow-hidden">
                                    <div style="width: {pct_vol_go:.1f}%" class="bg-gradient-to-r from-sky-500 to-blue-500 h-full rounded-full"></div>
                                </div>
                            </div>
                        </div>

                        <div class="pt-2.5 mt-2 flex items-center justify-between text-[11px] text-slate-400">
                            <span>Volume Total Pompé :</span>
                            <span class="font-mono font-bold text-slate-200">{(total_ssp_l + total_go_l):,.2f} Litres</span>
                        </div>
                    </div>

                </div>
            </div>
        </div>
        """
        return HTMLResponse(layout(content, "supervision", request=request))

    clients_actifs = conn.execute("SELECT nom, code FROM clients WHERE statut='ACTIF' ORDER BY nom ASC").fetchall()
    clients_options = "".join([f'<option value="{html.escape(c["nom"])}">{html.escape(c["nom"])} ({html.escape(c["code"])})</option>' for c in clients_actifs])
    conn.close()

    billets = [
        {"v": 200, "label": "200 DH"},
        {"v": 100, "label": "100 DH"},
        {"v": 50,  "label": "50 DH"},
        {"v": 20,  "label": "20 DH"},
    ]
    pieces = [{"v": 10, "label": "10 DH"}, {"v": 5, "label": "5 DH"}, {"v": 2, "label": "2 DH"}, {"v": 1, "label": "1 DH"}, {"v": 0.5, "label": "0.50 DH"}]

    content = f"""
    <div class="h-full flex flex-col gap-3 animate-in fade-in duration-300">
        {alert_banner}

        <div class="bg-slate-900/80 border border-slate-800/90 rounded-2xl px-4 py-3 flex justify-between items-center shadow-lg shadow-black/20 backdrop-blur-xl">
            <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center font-black text-slate-950 text-sm shadow-md shadow-emerald-950/40">
                    {nom_operateur[:2]}
                </div>
                <div>
                    <h2 class="text-xs font-black text-white uppercase tracking-wider">{nom_operateur}</h2>
                    <p class="text-[10px] text-slate-400">Saisie & Clôture de Fin de Poste</p>
                </div>
            </div>
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-extrabold uppercase tracking-wide">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Quart Actif
            </span>
        </div>

        <form action="/rapport-quart/valider" method="post" onsubmit="return confirm('Confirmer et clôturer votre caisse ?')" class="space-y-3 flex-1 flex flex-col justify-between">
            <input type="hidden" name="operateur" value="{nom_operateur}">
            <input type="hidden" name="fusion" value="{total_fusion_theorique}">
            <input type="hidden" id="credits_agent_json" name="credits_json" value="[]">

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-3.5 flex-1 overflow-y-auto pr-0.5 custom-scrollbar">
                
                <div class="lg:col-span-7 bg-slate-900/70 border border-slate-800/90 rounded-2xl p-4 space-y-3.5 backdrop-blur-xl shadow-xl shadow-black/20">
                    <div class="flex justify-between items-center pb-2.5 border-b border-slate-800/80">
                        <span class="text-xs font-extrabold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                            <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                            Comptage du Cash
                        </span>
                        <span class="text-xs font-mono font-black text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-lg border border-emerald-500/20" id="txt_total_especes">0,00 DH</span>
                    </div>

                    <div>
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">Coupures (Billets)</span>
                        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
                            {"".join([f'''
                            <div class="bg-slate-800/40 hover:bg-slate-800/70 border border-slate-700/50 rounded-xl p-2.5 text-center transition">
                                <span class="text-[10px] font-black text-slate-300 block mb-1.5">{b['label']}</span>
                                <input type="number" min="0" placeholder="0" data-val="{b['v']}" name="qte_{b['v']}" oninput="calculerCaisseAgent()" class="agent-input w-full text-center bg-slate-950/80 border border-slate-700 focus:border-emerald-500 rounded-lg py-1 font-mono font-black text-xs text-white outline-none transition">
                            </div>
                            ''' for b in billets])}
                        </div>
                    </div>

                    <div>
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">Monnaie (Pièces)</span>
                        <div class="grid grid-cols-3 sm:grid-cols-5 gap-2">
                            {"".join([f'''
                            <div class="bg-slate-800/40 hover:bg-slate-800/70 border border-slate-700/50 rounded-xl p-2 text-center transition">
                                <span class="text-[9px] font-black text-slate-300 block mb-1">{p['label']}</span>
                                <input type="number" min="0" placeholder="0" data-val="{p['v']}" name="qte_{str(p['v']).replace('.','_')}" oninput="calculerCaisseAgent()" class="agent-input w-full text-center bg-slate-950/80 border border-slate-700 focus:border-emerald-500 rounded-lg py-0.5 font-mono font-black text-xs text-white outline-none transition">
                            </div>
                            ''' for p in pieces])}
                        </div>
                    </div>
                </div>

                <div class="lg:col-span-5 flex flex-col gap-3.5">
                    <div class="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-3.5 backdrop-blur-xl space-y-2">
                        <label class="block text-[10px] font-extrabold text-sky-400 uppercase tracking-wider flex items-center justify-between">
                            <span>Tickets TPE / Carte Bancaire</span>
                            <span class="text-slate-500">DH</span>
                        </label>
                        <input type="number" step="0.01" id="agent_tpe" name="tpe" value="0.00" oninput="calculerCaisseAgent()" class="w-full px-3 py-2 bg-slate-950/80 rounded-xl border border-slate-700 focus:border-sky-500 font-mono font-bold text-sm text-white outline-none transition">
                    </div>

                    <div class="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-3.5 backdrop-blur-xl flex flex-col flex-1 shadow-xl shadow-black/20">
                        <div class="flex justify-between items-center pb-2 border-b border-slate-800/80 mb-2">
                            <span class="text-[10px] font-extrabold uppercase tracking-wider text-rose-400">Bons de Crédits</span>
                            <button type="button" onclick="ajouterCreditAgent()" class="px-2.5 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-lg text-[10px] font-bold transition flex items-center gap-1">+ Nouveau Bon</button>
                        </div>
                        <div id="liste_credits_agent" class="space-y-1.5 max-h-[120px] overflow-y-auto pr-1 custom-scrollbar"></div>
                    </div>

                    <div class="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 text-white p-3.5 rounded-2xl flex justify-between items-center font-mono border border-slate-800 shadow-2xl">
                        <div>
                            <span class="text-[9px] uppercase tracking-wider text-slate-400 block font-sans">Total Caisse Encaissé</span>
                            <span class="text-xl font-black text-[#00F5A0]" id="txt_total_agent">0,00 DH</span>
                        </div>
                        <button type="submit" class="px-5 py-2.5 bg-gradient-to-r from-amber-500 to-amber-400 hover:from-amber-400 hover:to-amber-300 text-slate-950 font-black text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-amber-500/20 active:scale-95 transition-all">
                            Clôturer Mon Quart
                        </button>
                    </div>
                </div>
            </div>
        </form>
    </div>

    <script>
        let creditsAgent = [];
        const clientsOptions = `{clients_options}`;

        function ajouterCreditAgent() {{
            creditsAgent.push({{ id: Date.now(), nom: '', montant: 0 }});
            renderCreditsAgent();
        }}
        function supprimerCreditAgent(id) {{
            creditsAgent = creditsAgent.filter(c => c.id !== id);
            renderCreditsAgent();
            calculerCaisseAgent();
        }}
        function updateCreditAgent(id, field, val) {{
            const c = creditsAgent.find(x => x.id === id);
            if (c) c[field] = field === 'montant' ? (parseFloat(val) || 0) : val;
            calculerCaisseAgent();
        }}
        function renderCreditsAgent() {{
            let h = '';
            creditsAgent.forEach(c => {{
                h += `
                <div class="grid grid-cols-12 gap-1.5 items-center bg-slate-800/40 p-1.5 rounded-xl border border-slate-700/60">
                    <select onchange="updateCreditAgent(${{c.id}}, 'nom', this.value)" class="col-span-7 bg-slate-950 text-slate-200 border border-slate-700 rounded-lg p-1 text-[10px] outline-none">
                        <option value="">Sélectionner Client...</option>${{clientsOptions}}
                    </select>
                    <input type="number" step="0.01" placeholder="0.00" value="${{c.montant || ''}}" oninput="updateCreditAgent(${{c.id}}, 'montant', this.value)" class="col-span-4 bg-slate-950 border border-slate-700 rounded-lg p-1 text-right text-rose-400 font-mono text-[10px] outline-none">
                    <button type="button" onclick="supprimerCreditAgent(${{c.id}})" class="col-span-1 text-rose-400 hover:text-rose-300 font-bold text-center">✕</button>
                </div>
                `;
            }});
            document.getElementById('liste_credits_agent').innerHTML = h;
        }}
        function calculerCaisseAgent() {{
            let esp = 0;
            document.querySelectorAll('.agent-input').forEach(i => {{
                esp += ((parseFloat(i.getAttribute('data-val')) || 0) * (parseInt(i.value) || 0));
            }});
            const tpe = parseFloat(document.getElementById('agent_tpe').value) || 0;
            const cred = creditsAgent.reduce((s, c) => s + (parseFloat(c.montant) || 0), 0);
            const total = esp + tpe + cred;
            document.getElementById('txt_total_especes').innerText = esp.toLocaleString('fr-FR', {{minimumFractionDigits: 2}}) + ' DH';
            document.getElementById('txt_total_agent').innerText = total.toLocaleString('fr-FR', {{minimumFractionDigits: 2}}) + ' DH';
            document.getElementById('credits_agent_json').value = JSON.stringify(creditsAgent);
        }}
    </script>
    """
    return HTMLResponse(layout(content, "supervision", request=request))

@router.post("/rapport-quart/valider")
async def valider_rapport_post(fusion: float = Form(0.0), 
                               tpe: float = Form(0.0), 
                               operateur: str = Form("Opérateur"),
                               credits_json: str = Form("[]"),
                               qte_200: int = Form(0), qte_100: int = Form(0), qte_50: int = Form(0), 
                               qte_20: int = Form(0), qte_10: int = Form(0), qte_5: int = Form(0), 
                               qte_2: int = Form(0), qte_1: int = Form(0), qte_0_5: int = Form(0)):
    especes = (qte_200 * 200) + (qte_100 * 100) + (qte_50 * 50) + (qte_20 * 20) + (qte_10 * 10) + (qte_5 * 5) + (qte_2 * 2) + (qte_1 * 1) + (qte_0_5 * 0.5)
    try:
        total_credits = sum([float(i.get('montant', 0) or 0) for i in json.loads(credits_json)])
    except Exception:
        total_credits = 0.0

    total_net = especes + tpe + total_credits
    resultat = total_net - fusion if fusion > 0 else 0.0

    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO cloture_quart (date, operateur, fusion, tpe, especes, credits, total_net, resultat, details_json, credits_json) 
           VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), operateur, fusion, tpe, especes, total_credits, total_net, resultat, "{}", credits_json)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/rapport-quart?success=true&msg=Clôture+enregistrée+avec+succès", status_code=status.HTTP_303_SEE_OTHER)