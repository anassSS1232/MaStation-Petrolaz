# pages/home.py
import json
import html
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse

from ui_utils import layout
from database import get_db_connection

router = APIRouter()

def ensure_schema(conn):
    try:
        conn.execute("ALTER TABLE prix_vente ADD COLUMN date_effet TEXT")
        conn.commit()
    except Exception:
        pass

def format_num(val):
    try:
        return f"{float(val or 0):,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return "0,00"

def get_row_val(row, key, default=""):
    if not row:
        return default
    try:
        val = row[key]
        return val if val is not None else default
    except Exception:
        return default

def update_scheduled_prices(conn):
    """Active automatiquement les prix programmés dont la date est arrivée."""
    ensure_schema(conn)
    try:
        scheduled = conn.execute(
            "SELECT id, produit, date_effet, date FROM prix_vente WHERE statut = 'PROGRAMME'"
        ).fetchall()
        
        for item in scheduled:
            dt_raw = get_row_val(item, 'date_effet') or get_row_val(item, 'date')
            try:
                if "-" in dt_raw:
                    dt_parsed = datetime.strptime(dt_raw[:16], "%Y-%m-%d %H:%M") if len(dt_raw) >= 16 else datetime.strptime(dt_raw[:10], "%Y-%m-%d")
                else:
                    dt_parsed = datetime.strptime(dt_raw[:16], "%d/%m/%Y %H:%M")
                
                if dt_parsed <= datetime.now():
                    prod = item['produit']
                    cibles = ['GAZOIL', 'Gazoil', 'Diesel', 'GO', 'Gasoil 10'] if prod in ['GAZOIL', 'Gazoil', 'Diesel', 'GO', 'Gasoil 10'] else ['SSP', 'Essence', 'Sans Plomb']
                    placeholders = ",".join(["?"] * len(cibles))
                    conn.execute(f"UPDATE prix_vente SET statut = 'INACTIF' WHERE produit IN ({placeholders})", cibles)
                    conn.execute("UPDATE prix_vente SET statut = 'ACTIF' WHERE id = ?", (item['id'],))
            except Exception:
                pass
        conn.commit()
    except Exception:
        pass

def render_tank_citerne_svg(tank_id, pct, color_type="SSP"):
    """Citerne industrielle épurée adaptée au style sombre translucide."""
    pct_val = max(0.0, min(100.0, float(pct)))
    fill_height = (pct_val / 100.0) * 54.0
    liquid_y = 70.0 - fill_height

    if color_type == "SSP":
        stroke_color = "#00F5A0"
        glow_color = "rgba(0, 245, 160, 0.45)"
        grad_top = "#00FFA3"
        grad_bot = "#047857"
        grad_back = "#059669"
    else:
        stroke_color = "#FF9F1C"
        glow_color = "rgba(255, 159, 28, 0.45)"
        grad_top = "#FFB347"
        grad_bot = "#C2410C"
        grad_back = "#EA580C"

    return f"""
    <div class="relative w-36 sm:w-40 select-none shrink-0">
        <svg viewBox="0 0 200 88" class="w-full h-auto drop-shadow-[0_4px_14px_{glow_color}] overflow-visible">
            <defs>
                <linearGradient id="grad_front_{tank_id}" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stop-color="{grad_top}" stop-opacity="0.95" />
                    <stop offset="100%" stop-color="{grad_bot}" stop-opacity="0.98" />
                </linearGradient>

                <linearGradient id="grad_back_{tank_id}" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stop-color="{grad_back}" stop-opacity="0.55" />
                    <stop offset="100%" stop-color="{grad_bot}" stop-opacity="0.45" />
                </linearGradient>

                <linearGradient id="rimGrad_{tank_id}" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="{stroke_color}" stop-opacity="0.9" />
                    <stop offset="50%" stop-color="#ffffff" stop-opacity="0.3" />
                    <stop offset="100%" stop-color="{stroke_color}" stop-opacity="0.75" />
                </linearGradient>

                <clipPath id="tankMask_{tank_id}">
                    <rect x="14" y="16" width="172" height="54" rx="27" ry="27" />
                </clipPath>
            </defs>

            <!-- 1. BERCEAUX DE CUVE -->
            <g class="fill-[#1E293B] stroke-[#334155]">
                <polygon points="40,71 34,83 52,83 47,71" stroke-width="1" />
                <rect x="32" y="82" width="22" height="2.5" rx="1.2" class="fill-[#0F172A]" />
                
                <polygon points="153,71 148,83 166,83 160,71" stroke-width="1" />
                <rect x="146" y="82" width="22" height="2.5" rx="1.2" class="fill-[#0F172A]" />
            </g>

            <!-- 2. DÔME SUPÉRIEUR -->
            <g>
                <rect x="94" y="9" width="12" height="6" class="fill-[#1E293B]" stroke="{stroke_color}" stroke-width="1.2" />
                <rect x="87" y="5" width="26" height="5" rx="2.5" class="fill-[#334155]" stroke="{stroke_color}" stroke-width="1.2" />
                <circle cx="92" cy="7.5" r="1" class="fill-[#94A3B8]" />
                <circle cx="108" cy="7.5" r="1" class="fill-[#94A3B8]" />
            </g>

            <!-- 3. CORPS DE CUVE -->
            <rect x="12" y="14" width="176" height="58" rx="29" ry="29" 
                  class="fill-[#061019]" 
                  stroke="url(#rimGrad_{tank_id})" stroke-width="2" />

            <!-- 4. CONTENU INTERNE -->
            <g clip-path="url(#tankMask_{tank_id})">
                <rect x="14" y="16" width="172" height="54" class="fill-[#03080F]" />

                <!-- Anneaux internes -->
                <line x1="60" y1="16" x2="60" y2="70" stroke="currentColor" class="text-white/5" stroke-width="1.5" stroke-dasharray="2 3" />
                <line x1="140" y1="16" x2="140" y2="70" stroke="currentColor" class="text-white/5" stroke-width="1.5" stroke-dasharray="2 3" />

                <!-- Graduations -->
                <line x1="24" y1="30" x2="31" y2="30" stroke="currentColor" class="text-white/25" stroke-width="1.2" stroke-linecap="round" />
                <line x1="24" y1="43" x2="35" y2="43" stroke="currentColor" class="text-white/40" stroke-width="1.5" stroke-linecap="round" />
                <line x1="24" y1="56" x2="31" y2="56" stroke="currentColor" class="text-white/25" stroke-width="1.2" stroke-linecap="round" />

                <!-- Vague arrière -->
                <g transform="translate(0, {liquid_y:.2f})">
                    <path class="tank-wave-back" 
                          d="M -160 0 Q -120 4 -80 0 T 0 0 T 80 0 T 160 0 T 240 0 T 320 0 L 320 80 L -160 80 Z" 
                          fill="url(#grad_back_{tank_id})" />
                </g>

                <!-- Vague avant -->
                <g transform="translate(0, {liquid_y:.2f})">
                    <path class="tank-wave-front" 
                          d="M -160 0 Q -120 -5 -80 0 T 0 0 T 80 0 T 160 0 T 240 0 T 320 0 L 320 80 L -160 80 Z" 
                          fill="url(#grad_front_{tank_id})" />
                    <path class="tank-wave-front" 
                          d="M -160 0 Q -120 -5 -80 0 T 0 0 T 80 0 T 160 0 T 240 0 T 320 0" 
                          fill="none" stroke="rgba(255,255,255,0.6)" stroke-width="1.5" />
                </g>

                <!-- Bulles -->
                <circle cx="68" cy="62" r="1.5" class="tank-bubble-1" fill="#ffffff" />
                <circle cx="128" cy="65" r="2.2" class="tank-bubble-2" fill="#ffffff" />
                <circle cx="150" cy="59" r="1.2" class="tank-bubble-3" fill="#ffffff" />

                <!-- Jauge & niveau -->
                <line x1="100" y1="16" x2="100" y2="70" stroke="currentColor" class="text-white/25" stroke-width="1" stroke-dasharray="2 3" />
                <circle cx="100" cy="{liquid_y:.2f}" r="3" fill="#ffffff" stroke="{stroke_color}" stroke-width="1.5" />
            </g>

            <!-- 5. REFLETS VERRE -->
            <path d="M 38 21 Q 100 17 162 21" stroke="rgba(255, 255, 255, 0.55)" stroke-width="2.2" stroke-linecap="round" fill="none" />
            <path d="M 46 66 Q 100 68 154 66" stroke="rgba(255, 255, 255, 0.15)" stroke-width="1.2" stroke-linecap="round" fill="none" />
        </svg>
    </div>
    """

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    conn = get_db_connection()
    update_scheduled_prices(conn)
    today_sql = datetime.now().strftime("%Y-%m-%d")
    
    actif_gazoil = conn.execute("SELECT * FROM prix_vente WHERE produit IN ('GAZOIL', 'Gazoil', 'Diesel', 'GO', 'Gasoil 10') AND statut = 'ACTIF' ORDER BY id DESC LIMIT 1").fetchone()
    actif_ssp = conn.execute("SELECT * FROM prix_vente WHERE produit IN ('SSP', 'Essence', 'Sans Plomb') AND statut = 'ACTIF' ORDER BY id DESC LIMIT 1").fetchone()
    
    gazoil_history = conn.execute("SELECT * FROM prix_vente WHERE produit IN ('GAZOIL', 'Gazoil', 'Diesel', 'GO', 'Gasoil 10') ORDER BY id DESC LIMIT 15").fetchall()
    ssp_history = conn.execute("SELECT * FROM prix_vente WHERE produit IN ('SSP', 'Essence', 'Sans Plomb') ORDER BY id DESC LIMIT 15").fetchall()

    conn.close()

    # =========================================================================
    # VALEURS RÉELLES SIMULÉES POUR CAPTURE D'ÉCRAN
    # =========================================================================
    clients_a_surveiller = 3
    clients_critiques = 1
    solde_clients_total = 148650.00

    caisse_aujourdhui = 128450.00
    solde_caisse = 42800.00

    dettes_fournisseurs = 384500.00

    releve_essence_l = "3 840"
    releve_gazoil_l = "14 620"

    stock_essence_litres = 18450
    stock_essence_pct = round((stock_essence_litres / 31600.0) * 100, 1)

    stock_gazoil_litres = 38200
    stock_gazoil_pct = round((stock_gazoil_litres / 63200.0) * 100, 1)
    # =========================================================================

    today_dt = datetime.now()
    date_to_val = today_dt.strftime("%Y-%m-%d")
    date_from_val = (today_dt - timedelta(days=30)).strftime("%Y-%m-%d")
    now_iso = today_dt.strftime("%Y-%m-%dT%H:%M")

    prix_gazoil_val = f"{actif_gazoil['prix']:.3f}" if actif_gazoil else "14.000"
    date_gazoil_val = get_row_val(actif_gazoil, 'date_effet') or get_row_val(actif_gazoil, 'date') or today_dt.strftime("%d/%m/%Y %H:%M")

    prix_ssp_val = f"{actif_ssp['prix']:.3f}" if actif_ssp else "15.000"
    date_ssp_val = get_row_val(actif_ssp, 'date_effet') or get_row_val(actif_ssp, 'date') or today_dt.strftime("%d/%m/%Y %H:%M")

    chart_labels = [(today_dt - timedelta(days=i)).strftime("%d/%m") for i in range(25, -1, -1)]
    gazoil_sales = [5600, 3700, 4200, 4800, 5200, 5400, 5600, 4900, 5200, 4900, 5069, 4800, 4750, 5000, 5800, 4900, 5200, 5000, 5300, 5100, 5400, 5800, 4500, 5300, 5200, 5100]
    essence_sales = [1900, 1400, 1600, 1700, 1800, 1900, 1850, 1700, 1900, 1600, 1586, 1600, 1650, 1700, 2100, 1450, 1600, 1500, 1800, 1600, 1700, 2200, 1400, 1700, 1650, 1800]
    total_sales = [d + e for d, e in zip(gazoil_sales, essence_sales)]

    def generate_history_rows(rows, is_gazoil=False):
        if not rows:
            return '<tr><td colspan="4" class="text-center py-6 text-slate-500 text-xs italic">Aucun historique enregistré</td></tr>'
        html_out = ""
        badge_active_cls = "bg-orange-500/15 text-[#FF9F1C] border-orange-500/30" if is_gazoil else "bg-emerald-500/15 text-[#00F5A0] border-emerald-500/30"
        btn_activate_cls = "bg-orange-500/10 hover:bg-[#FF9F1C] text-[#FF9F1C] hover:text-slate-950" if is_gazoil else "bg-emerald-500/10 hover:bg-[#00F5A0] text-[#00F5A0] hover:text-slate-950"

        for r in rows:
            statut = r['statut']
            date_aff = get_row_val(r, 'date_effet') or get_row_val(r, 'date') or '-'
            if statut == 'ACTIF':
                badge = f'<span class="px-2 py-0.5 rounded text-[9px] font-black uppercase border {badge_active_cls}">Actif</span>'
                action = ""
            elif statut == 'PROGRAMME':
                badge = '<span class="px-2 py-0.5 rounded text-[9px] font-black uppercase bg-sky-500/15 text-sky-400 border border-sky-500/30">Programmé</span>'
                action = f"""
                <form action="/home/activer-prix" method="post" class="m-0 inline">
                    <input type="hidden" name="id" value="{r['id']}">
                    <button type="submit" class="{btn_activate_cls} px-2 py-0.5 rounded text-[10px] font-bold uppercase transition">Activer</button>
                </form>
                """
            else:
                badge = '<span class="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-700">Inactif</span>'
                action = f"""
                <form action="/home/activer-prix" method="post" class="m-0 inline">
                    <input type="hidden" name="id" value="{r['id']}">
                    <button type="submit" class="bg-slate-200 hover:bg-[#184E68] text-slate-700 hover:text-white dark:bg-white/5 dark:text-slate-300 px-2 py-0.5 rounded text-[10px] font-bold uppercase transition">Activer</button>
                </form>
                """
                
            html_out += f"""
            <tr class="border-b border-slate-200/80 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition text-xs">
                <td class="py-2.5 px-3 font-mono font-bold text-slate-900 dark:text-white">{r['prix']:.3f} <span class="text-[9px] text-slate-400 font-sans">MAD</span></td>
                <td class="py-2.5 px-3 text-slate-600 dark:text-slate-300 font-mono text-[11px]">{date_aff}</td>
                <td class="py-2.5 px-3">{badge}</td>
                <td class="py-2.5 px-3 text-right">{action}</td>
            </tr>
            """
        return html_out

    gazoil_table = generate_history_rows(gazoil_history, is_gazoil=True)
    ssp_table = generate_history_rows(ssp_history, is_gazoil=False)

    ssp_tank_html = render_tank_citerne_svg("ssp_tank", stock_essence_pct, color_type="SSP")
    gazoil_tank_html = render_tank_citerne_svg("gazoil_tank", stock_gazoil_pct, color_type="GAZOIL")

    content = f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        .glass-panel {{
            background: rgba(255, 255, 255, 0.88) !important;
            backdrop-filter: blur(20px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
            border: 1px solid rgba(226, 232, 240, 0.90) !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.06) !important;
        }}

        html.dark .glass-panel {{
            background: rgba(13, 22, 36, 0.75) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.6) !important;
        }}

        .glass-box-inner {{
            background: rgba(241, 245, 249, 0.85) !important;
            border: 1px solid rgba(203, 213, 225, 0.70) !important;
        }}

        html.dark .glass-box-inner {{
            background: rgba(5, 10, 18, 0.60) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
        }}

        @keyframes tankWaveFront {{
            0% {{ transform: translateX(0); }}
            100% {{ transform: translateX(-80px); }}
        }}
        @keyframes tankWaveBack {{
            0% {{ transform: translateX(-80px); }}
            100% {{ transform: translateX(0); }}
        }}
        @keyframes tankBubbleUp {{
            0% {{ transform: translateY(0); opacity: 0; }}
            40% {{ opacity: 0.65; }}
            80% {{ opacity: 0.4; }}
            100% {{ transform: translateY(-30px); opacity: 0; }}
        }}

        .tank-wave-front {{
            animation: tankWaveFront 3.4s linear infinite;
        }}
        .tank-wave-back {{
            animation: tankWaveBack 5.6s linear infinite;
        }}
        .tank-bubble-1 {{
            animation: tankBubbleUp 3s ease-in infinite;
        }}
        .tank-bubble-2 {{
            animation: tankBubbleUp 4.2s ease-in 1.4s infinite;
        }}
        .tank-bubble-3 {{
            animation: tankBubbleUp 3.6s ease-in 0.7s infinite;
        }}
    </style>

<div class="w-full max-w-7xl mx-auto space-y-4 my-auto animate-in fade-in duration-300">        
        <!-- 1. KPIS AVEC VALEURS RÉELLES VISUELLES -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
            <div class="group relative overflow-hidden bg-gradient-to-br from-[#6366F1]/90 via-[#7C3AED]/90 to-[#9333EA]/90 backdrop-blur-md border border-white/20 text-white rounded-2xl p-3.5 shadow-lg hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between cursor-default">
                <div class="flex items-center justify-between pb-2 border-b border-white/20">
                    <div class="flex items-center gap-1.5">
                        <i data-lucide="users" class="w-3.5 h-3.5 text-white/90"></i>
                        <span class="text-[10.5px] font-black uppercase tracking-wider text-white">Clients</span>
                    </div>
                </div>
                <div class="mt-2.5 space-y-1.5 font-mono text-[11px]">
                    <div class="flex justify-between items-center bg-black/25 px-2.5 py-1 rounded-xl">
                        <span class="font-sans text-[10px] text-indigo-100 font-medium">À surveiller</span>
                        <span class="font-bold text-amber-300">{clients_a_surveiller}</span>
                    </div>
                    <div class="flex justify-between items-center bg-black/25 px-2.5 py-1 rounded-xl">
                        <span class="font-sans text-[10px] text-indigo-100 font-medium">Plafond dépassé</span>
                        <span class="font-bold text-rose-300">{clients_critiques}</span>
                    </div>
                </div>
            </div>

            <div class="group relative overflow-hidden bg-white/90 dark:bg-slate-900/80 backdrop-blur-md border border-slate-200/90 dark:border-white/15 text-slate-900 dark:text-white rounded-2xl p-3.5 shadow-lg hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between cursor-default">
                <div class="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-white/10">
                    <div class="flex items-center gap-1.5">
                        <i data-lucide="fuel" class="w-3.5 h-3.5 text-[#E5A842]"></i>
                        <span class="text-[10.5px] font-black uppercase tracking-wider">Relevé du Jour</span>
                    </div>
                </div>
                <div class="mt-2.5 space-y-1.5 font-mono text-[11px]">
                    <div class="flex justify-between items-center bg-emerald-500/15 border border-emerald-500/25 px-2.5 py-1 rounded-xl">
                        <span class="font-sans text-[10px] text-emerald-600 dark:text-[#00F5A0] font-bold">SSP</span>
                        <span class="font-bold text-slate-900 dark:text-white">{releve_essence_l} <span class="text-[9px] font-normal text-slate-500 dark:text-emerald-200">L</span></span>
                    </div>
                    <div class="flex justify-between items-center bg-orange-500/15 border border-orange-500/25 px-2.5 py-1 rounded-xl">
                        <span class="font-sans text-[10px] text-orange-600 dark:text-[#FF9F1C] font-bold">GAZOIL</span>
                        <span class="font-bold text-slate-900 dark:text-white">{releve_gazoil_l} <span class="text-[9px] font-normal text-slate-500 dark:text-orange-200">L</span></span>
                    </div>
                </div>
            </div>

            <div class="group relative overflow-hidden bg-gradient-to-br from-[#0284C7]/90 via-[#0EA5E9]/90 to-[#38BDF8]/90 backdrop-blur-md border border-white/20 text-white rounded-2xl p-3.5 shadow-lg hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between cursor-default">
                <div class="flex items-center justify-between pb-2 border-b border-white/20">
                    <div class="flex items-center gap-1.5">
                        <i data-lucide="wallet" class="w-3.5 h-3.5 text-white/90"></i>
                        <span class="text-[10.5px] font-black uppercase tracking-wider text-white">Solde Clients</span>
                    </div>
                </div>
                <div class="my-auto pt-2">
                    <div class="text-lg font-black font-mono leading-tight">{format_num(solde_clients_total)} <span class="text-xs font-sans">MAD</span></div>
                    <span class="text-[9.5px] text-sky-100 block mt-0.5 font-medium">Créances totales en cours</span>
                </div>
            </div>

            <div class="group relative overflow-hidden bg-gradient-to-br from-[#059669]/90 via-[#10B981]/90 to-[#34D399]/90 backdrop-blur-md border border-white/20 text-white rounded-2xl p-3.5 shadow-lg hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between cursor-default">
                <div class="flex items-center justify-between pb-2 border-b border-white/20">
                    <div class="flex items-center gap-1.5">
                        <i data-lucide="banknote" class="w-3.5 h-3.5 text-white/90"></i>
                        <span class="text-[10.5px] font-black uppercase tracking-wider text-white">Caisse</span>
                    </div>
                </div>
                <div class="pt-2">
                    <div class="text-lg font-black font-mono leading-tight">{format_num(solde_caisse)} <span class="text-xs font-sans">MAD</span></div>
                    <div class="text-[9.5px] font-mono text-emerald-50 mt-1 bg-black/25 px-2 py-0.5 rounded-lg w-fit">Total jour: {format_num(caisse_aujourdhui)} MAD</div>
                </div>
            </div>

            <div class="group relative overflow-hidden bg-gradient-to-br from-[#E11D48]/90 via-[#F43F5E]/90 to-[#FB7185]/90 backdrop-blur-md border border-white/20 text-white rounded-2xl p-3.5 shadow-lg hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between cursor-default">
                <div class="flex items-center justify-between pb-2 border-b border-white/20">
                    <div class="flex items-center gap-1.5">
                        <i data-lucide="file-text" class="w-3.5 h-3.5 text-white/90"></i>
                        <span class="text-[10.5px] font-black uppercase tracking-wider text-white">Dettes Fournisseurs</span>
                    </div>
                </div>
                <div class="my-auto pt-2">
                    <div class="text-lg font-black font-mono leading-tight">{format_num(dettes_fournisseurs)} <span class="text-xs font-sans">MAD</span></div>
                    <span class="text-[9.5px] text-rose-100 block mt-0.5 font-medium">Solde global à régler</span>
                </div>
            </div>
        </div>

        <!-- 2. STOCKS / CITERNES ET TARIFS -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-stretch">
            
            <div class="lg:col-span-5 flex flex-col justify-between gap-3">
                
                <!-- CARTE SSP -->
                <div class="glass-panel hover:border-[#00F5A0]/60 rounded-2xl p-3.5 shadow-lg transition-all duration-200 flex flex-col justify-between">
                    <div class="flex items-center justify-between pb-2 border-b border-slate-200/80 dark:border-white/10">
                        <div class="flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full bg-[#00F5A0] shadow-[0_0_8px_#00F5A0]"></span>
                            <h3 class="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">SSP</h3>
                        </div>
                        <div class="flex items-center gap-1">
                            <button onclick="openModalHistory('SSP')" class="w-7 h-7 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-700 dark:text-slate-300 flex items-center justify-center transition border border-slate-200 dark:border-white/10" title="Historique">
                                <i data-lucide="history" class="w-3.5 h-3.5"></i>
                            </button>
                            <button onclick="openModalSinglePrice('SSP', '{prix_ssp_val}')" class="w-7 h-7 rounded-lg bg-[#00F5A0]/15 hover:bg-[#00F5A0]/25 text-emerald-600 dark:text-[#00F5A0] flex items-center justify-center transition border border-[#00F5A0]/30" title="Modifier le tarif">
                                <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>

                    <div class="flex items-center justify-between gap-3 pt-3">
                        <div class="flex items-center gap-3">
                            {ssp_tank_html}
                            <div>
                                <div class="text-2xl font-black font-mono text-emerald-600 dark:text-[#00F5A0] leading-none">{stock_essence_pct}%</div>
                                <span class="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 block mt-1.5">{stock_essence_litres} <span class="text-[10px] text-slate-400 font-sans">L</span></span>
                            </div>
                        </div>

                        <div class="text-right glass-box-inner rounded-xl px-3 py-2 shadow-xs shrink-0">
                            <div class="text-[8.5px] font-black text-emerald-600 dark:text-[#00F5A0] uppercase tracking-wider mb-0.5">● EN VIGUEUR</div>
                            <div class="text-lg font-black font-mono text-slate-900 dark:text-white leading-none">
                                {prix_ssp_val} <span class="text-[10px] font-sans font-medium text-slate-500 dark:text-slate-400">MAD/L</span>
                            </div>
                            <span class="text-[9px] font-mono text-slate-500 dark:text-slate-400 block mt-1">{date_ssp_val}</span>
                        </div>
                    </div>
                </div>

                <!-- CARTE GAZOIL -->
                <div class="glass-panel hover:border-[#FF9F1C]/60 rounded-2xl p-3.5 shadow-lg transition-all duration-200 flex flex-col justify-between">
                    <div class="flex items-center justify-between pb-2 border-b border-slate-200/80 dark:border-white/10">
                        <div class="flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full bg-[#FF9F1C] shadow-[0_0_8px_#FF9F1C]"></span>
                            <h3 class="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">GAZOIL</h3>
                        </div>
                        <div class="flex items-center gap-1">
                            <button onclick="openModalHistory('GAZOIL')" class="w-7 h-7 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-700 dark:text-slate-300 flex items-center justify-center transition border border-slate-200 dark:border-white/10" title="Historique">
                                <i data-lucide="history" class="w-3.5 h-3.5"></i>
                            </button>
                            <button onclick="openModalSinglePrice('GAZOIL', '{prix_gazoil_val}')" class="w-7 h-7 rounded-lg bg-[#FF9F1C]/15 hover:bg-[#FF9F1C]/25 text-amber-600 dark:text-[#FF9F1C] flex items-center justify-center transition border border-[#FF9F1C]/30" title="Modifier le tarif">
                                <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>

                    <div class="flex items-center justify-between gap-3 pt-3">
                        <div class="flex items-center gap-3">
                            {gazoil_tank_html}
                            <div>
                                <div class="text-2xl font-black font-mono text-amber-600 dark:text-[#FF9F1C] leading-none">{stock_gazoil_pct}%</div>
                                <span class="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 block mt-1.5">{stock_gazoil_litres} <span class="text-[10px] text-slate-400 font-sans">L</span></span>
                            </div>
                        </div>

                        <div class="text-right glass-box-inner rounded-xl px-3 py-2 shadow-xs shrink-0">
                            <div class="text-[8.5px] font-black text-amber-600 dark:text-[#FF9F1C] uppercase tracking-wider mb-0.5">● EN VIGUEUR</div>
                            <div class="text-lg font-black font-mono text-slate-900 dark:text-white leading-none">
                                {prix_gazoil_val} <span class="text-[10px] font-sans font-medium text-slate-500 dark:text-slate-400">MAD/L</span>
                            </div>
                            <span class="text-[9px] font-mono text-slate-500 dark:text-slate-400 block mt-1">{date_gazoil_val}</span>
                        </div>
                    </div>
                </div>

            </div>

            <!-- GRAPHIQUE DES VENTES -->
            <div class="lg:col-span-7 glass-panel rounded-2xl p-4 shadow-lg flex flex-col justify-between">
                
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2.5 border-b border-slate-200/80 dark:border-white/10">
                    <div class="flex items-center gap-2">
                        <i data-lucide="trending-up" class="w-4 h-4 text-sky-500"></i>
                        <h2 class="text-xs sm:text-sm font-black text-slate-900 dark:text-white tracking-tight">Évolution des Ventes</h2>
                    </div>

                    <div class="flex items-center flex-wrap gap-1.5 text-[11px]">
                        <span class="text-slate-500 dark:text-slate-400 font-bold">Du:</span>
                        <input type="date" value="{date_from_val}" class="glass-box-inner text-slate-800 dark:text-slate-200 px-2.5 py-1 rounded-lg text-xs font-mono outline-none focus:border-sky-400">
                        
                        <span class="text-slate-500 dark:text-slate-400 font-bold">Au:</span>
                        <input type="date" value="{date_to_val}" class="glass-box-inner text-slate-800 dark:text-slate-200 px-2.5 py-1 rounded-lg text-xs font-mono outline-none focus:border-sky-400">
                        
                        <button type="button" class="px-2.5 py-1 bg-sky-500 hover:bg-sky-600 text-white rounded-lg font-bold text-xs flex items-center gap-1 shadow-md transition active:scale-95">
                            <i data-lucide="refresh-cw" class="w-3 h-3"></i> Filtrer
                        </button>
                    </div>
                </div>

                <div class="flex items-center justify-center gap-4 pt-2 text-[11px] font-bold">
                    <div class="flex items-center gap-1.5">
                        <span class="w-2.5 h-2.5 rounded-full bg-[#00F5A0] shadow-[0_0_6px_#00F5A0]"></span>
                        <span class="text-slate-700 dark:text-slate-300">SSP</span>
                    </div>
                    <div class="flex items-center gap-1.5">
                        <span class="w-2.5 h-2.5 rounded-full bg-[#FF9F1C] shadow-[0_0_6px_#FF9F1C]"></span>
                        <span class="text-slate-700 dark:text-slate-300">GAZOIL</span>
                    </div>
                    <div class="flex items-center gap-1.5">
                        <span class="w-2.5 h-2.5 rounded-full bg-[#6366F1] shadow-[0_0_6px_#6366F1]"></span>
                        <span class="text-slate-700 dark:text-slate-300">Total Ventes</span>
                    </div>
                </div>

                <div class="relative w-full h-[180px] sm:h-[220px] xl:h-[240px] mt-2">
                    <canvas id="salesEvolutionChart"></canvas>
                </div>

            </div>

        </div>

    </div>

    <!-- MODAL MODIFICATION TARIF -->
    <div id="modalSinglePrice" class="fixed inset-0 bg-black/60 backdrop-blur-sm hidden z-50 flex items-center justify-center p-3">
        <form action="/home/update-prix-unique" method="post" class="bg-white dark:bg-[#0c1624] w-full max-w-sm rounded-2xl border border-slate-200 dark:border-white/15 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150">
            <input type="hidden" id="modal_produit_nom" name="produit" value="SSP">
            
            <div class="p-3.5 border-b border-slate-100 dark:border-white/10 flex justify-between items-center bg-slate-50 dark:bg-black/30">
                <div class="flex items-center gap-2">
                    <i id="modal_header_icon" data-lucide="tag" class="w-4 h-4 text-emerald-600 dark:text-[#00F5A0]"></i>
                    <h3 class="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">Modifier Tarif <span id="modal_title_fuel" class="text-emerald-600 dark:text-[#00F5A0]">SSP</span></h3>
                </div>
                <button type="button" onclick="closeModalSinglePrice()" class="w-6 h-6 rounded-lg bg-slate-200 dark:bg-white/10 flex items-center justify-center text-xs font-bold text-slate-600 dark:text-slate-300 hover:text-white">✕</button>
            </div>
            
            <div class="p-3.5 space-y-3">
                <div>
                    <label id="modal_price_label" class="text-[10px] font-bold uppercase mb-1 block tracking-wider text-emerald-600 dark:text-[#00F5A0]">
                        Nouveau Prix (MAD / Litre)
                    </label>
                    <input type="number" step="0.001" id="modal_single_prix_input" name="prix" required placeholder="0.000" class="w-full bg-slate-50 dark:bg-black/40 border border-slate-300 dark:border-white/15 rounded-xl p-2.5 font-black text-slate-900 dark:text-white text-base outline-none font-mono focus:border-amber-400">
                </div>

                <div class="bg-slate-50 dark:bg-black/30 p-2.5 rounded-xl border border-slate-200 dark:border-white/10">
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" id="chk_immediate" name="activer_immediat" value="1" checked onchange="toggleScheduledDate(this.checked)" class="w-4 h-4 rounded cursor-pointer">
                        <span class="text-[10.5px] font-bold text-slate-700 dark:text-slate-200 uppercase">Activer immédiatement</span>
                    </label>
                </div>

                <div id="scheduled_date_wrapper" class="hidden space-y-1 bg-slate-50 dark:bg-black/30 p-2.5 rounded-xl border border-slate-200 dark:border-white/10 animate-in fade-in duration-150">
                    <label class="text-[10px] font-bold uppercase block tracking-wider text-sky-500 dark:text-sky-400">
                        Date & Heure d'effet (Changement Automatique)
                    </label>
                    <input type="datetime-local" id="modal_date_effet" name="date_effet" value="{now_iso}" class="w-full bg-white dark:bg-black/40 border border-slate-300 dark:border-white/15 rounded-lg p-2 font-mono text-xs text-slate-900 dark:text-white outline-none">
                </div>
            </div>
            
            <div class="p-3 bg-slate-50 dark:bg-black/30 border-t border-slate-100 dark:border-white/10 flex gap-2">
                <button type="button" onclick="closeModalSinglePrice()" class="flex-1 bg-slate-200 hover:bg-slate-300 dark:bg-white/10 dark:hover:bg-white/15 text-slate-700 dark:text-slate-300 py-2 rounded-xl font-bold uppercase text-[11px]">Annuler</button>
                <button type="submit" id="modal_submit_btn" class="flex-1 bg-[#00F5A0] hover:bg-[#00D084] text-slate-950 py-2 rounded-xl font-black uppercase text-[11px] shadow-sm transition active:scale-95">Enregistrer</button>
            </div>
        </form>
    </div>

    <!-- MODAL HISTORIQUE DES TARIFS -->
    <div id="modalHistory" class="fixed inset-0 bg-black/60 backdrop-blur-sm hidden z-50 flex items-center justify-center p-3">
        <div class="bg-white dark:bg-[#0c1624] w-full max-w-lg rounded-2xl border border-slate-200 dark:border-white/15 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150">
            <div class="p-3 border-b border-slate-100 dark:border-white/10 flex justify-between items-center bg-slate-50 dark:bg-black/30">
                <div class="flex items-center gap-2">
                    <i data-lucide="history" class="w-4 h-4 text-sky-500"></i>
                    <h3 class="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">Historique Tarifs</h3>
                </div>
                <div class="flex items-center gap-1">
                    <button type="button" onclick="switchHistoryTab('SSP')" id="tabBtnSSP" class="px-2.5 py-1 text-[10.5px] font-bold rounded-lg bg-[#00F5A0] text-slate-950">SSP</button>
                    <button type="button" onclick="switchHistoryTab('GAZOIL')" id="tabBtnGazoil" class="px-2.5 py-1 text-[10.5px] font-bold rounded-lg bg-slate-200 dark:bg-white/10 text-slate-700 dark:text-slate-300">GAZOIL</button>
                    <button type="button" onclick="closeModalHistory()" class="w-6 h-6 rounded-lg bg-slate-200 dark:bg-white/10 flex items-center justify-center text-xs font-bold text-slate-600 dark:text-slate-300 ml-1 hover:text-white">✕</button>
                </div>
            </div>
            
            <div class="p-3 overflow-x-auto max-h-72">
                <div id="historySSPContainer">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="border-b border-slate-200 dark:border-white/10 text-[9.5px] uppercase font-bold text-slate-400">
                                <th class="pb-1.5 px-2">Tarif</th>
                                <th class="pb-1.5 px-2">Date d'effet</th>
                                <th class="pb-1.5 px-2">Statut</th>
                                <th class="pb-1.5 px-2 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody>{ssp_table}</tbody>
                    </table>
                </div>
                <div id="historyGazoilContainer" class="hidden">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="border-b border-slate-200 dark:border-white/10 text-[9.5px] uppercase font-bold text-slate-400">
                                <th class="pb-1.5 px-2">Tarif</th>
                                <th class="pb-1.5 px-2">Date d'effet</th>
                                <th class="pb-1.5 px-2">Statut</th>
                                <th class="pb-1.5 px-2 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody>{gazoil_table}</tbody>
                    </table>
                </div>
            </div>

            <div class="p-2.5 bg-slate-50 dark:bg-black/30 border-t border-slate-100 dark:border-white/10 flex justify-end">
                <button type="button" onclick="closeModalHistory()" class="px-3 py-1 bg-slate-200 hover:bg-slate-300 dark:bg-white/10 dark:hover:bg-white/15 text-slate-700 dark:text-slate-300 rounded-lg font-bold uppercase text-[10px]">Fermer</button>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            const ctx = document.getElementById('salesEvolutionChart').getContext('2d');
            
            const labels = {json.dumps(chart_labels)};
            const gazoilData = {json.dumps(gazoil_sales)};
            const essenceData = {json.dumps(essence_sales)};
            const totalData = {json.dumps(total_sales)};

            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Total Ventes',
                            data: totalData,
                            borderColor: '#818CF8',
                            borderWidth: 2,
                            borderDash: [4, 4],
                            pointRadius: 2,
                            fill: false,
                            tension: 0.35
                        }},
                        {{
                            label: 'SSP',
                            data: essenceData,
                            borderColor: '#00F5A0',
                            borderWidth: 2.5,
                            backgroundColor: 'rgba(0, 245, 160, 0.12)',
                            pointRadius: 2.5,
                            fill: true,
                            tension: 0.35
                        }},
                        {{
                            label: 'GAZOIL',
                            data: gazoilData,
                            borderColor: '#FF9F1C',
                            borderWidth: 2.5,
                            backgroundColor: 'rgba(255, 159, 28, 0.12)',
                            pointRadius: 2.5,
                            fill: true,
                            tension: 0.35
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return ' ' + context.dataset.label + ': ' + context.parsed.y.toLocaleString('fr-FR') + ' L';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{ 
                            grid: {{ display: false }},
                            ticks: {{ color: '#94A3B8', font: {{ size: 10 }} }}
                        }},
                        y: {{
                            grid: {{ color: 'rgba(148, 163, 184, 0.15)' }},
                            ticks: {{ 
                                color: '#94A3B8', 
                                font: {{ size: 10 }},
                                callback: function(value) {{ return value + ' L'; }} 
                            }}
                        }}
                    }}
                }}
            }});
        }});

        function toggleScheduledDate(isImmediate) {{
            const wrapper = document.getElementById('scheduled_date_wrapper');
            const dateInput = document.getElementById('modal_date_effet');
            if (isImmediate) {{
                wrapper.classList.add('hidden');
                dateInput.removeAttribute('required');
            }} else {{
                wrapper.classList.remove('hidden');
                dateInput.setAttribute('required', 'required');
            }}
        }}

        function openModalSinglePrice(fuelName, currentPrice) {{
            const isSSP = (fuelName === 'SSP' || fuelName === 'Essence' || fuelName === 'Sans Plomb');
            const cleanFuel = isSSP ? 'SSP' : 'GAZOIL';
            
            document.getElementById('modal_produit_nom').value = cleanFuel;
            document.getElementById('modal_title_fuel').innerText = cleanFuel;
            document.getElementById('modal_single_prix_input').value = currentPrice || '';

            const icon = document.getElementById('modal_header_icon');
            const titleSpan = document.getElementById('modal_title_fuel');
            const label = document.getElementById('modal_price_label');
            const submitBtn = document.getElementById('modal_submit_btn');
            const chk = document.getElementById('chk_immediate');

            if (isSSP) {{
                icon.className = "w-4 h-4 text-emerald-600 dark:text-[#00F5A0]";
                titleSpan.className = "text-emerald-600 dark:text-[#00F5A0]";
                label.className = "text-[10px] font-bold uppercase mb-1 block tracking-wider text-emerald-600 dark:text-[#00F5A0]";
                submitBtn.className = "flex-1 bg-[#00F5A0] hover:bg-[#00D084] text-slate-950 py-2 rounded-xl font-black uppercase text-[11px] shadow-sm transition active:scale-95";
                chk.className = "w-4 h-4 rounded accent-[#00F5A0] cursor-pointer";
            }} else {{
                icon.className = "w-4 h-4 text-amber-600 dark:text-[#FF9F1C]";
                titleSpan.className = "text-amber-600 dark:text-[#FF9F1C]";
                label.className = "text-[10px] font-bold uppercase mb-1 block tracking-wider text-amber-600 dark:text-[#FF9F1C]";
                submitBtn.className = "flex-1 bg-[#FF9F1C] hover:bg-[#ff8f00] text-slate-950 py-2 rounded-xl font-black uppercase text-[11px] shadow-sm transition active:scale-95";
                chk.className = "w-4 h-4 rounded accent-[#FF9F1C] cursor-pointer";
            }}
            
            chk.checked = true;
            toggleScheduledDate(true);
            
            document.getElementById('modalSinglePrice').classList.remove('hidden');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function closeModalSinglePrice() {{
            document.getElementById('modalSinglePrice').classList.add('hidden');
        }}

        function openModalHistory(fuel) {{
            switchHistoryTab(fuel);
            document.getElementById('modalHistory').classList.remove('hidden');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function switchHistoryTab(fuel) {{
            const isGazoil = (fuel === 'GAZOIL' || fuel === 'Gazoil' || fuel === 'Diesel' || fuel === 'GO' || fuel === 'Gasoil 10');
            const gazoilBox = document.getElementById('historyGazoilContainer');
            const sspBox = document.getElementById('historySSPContainer');
            const btnGazoil = document.getElementById('tabBtnGazoil');
            const btnSsp = document.getElementById('tabBtnSSP');

            if(isGazoil) {{
                gazoilBox.classList.remove('hidden');
                sspBox.classList.add('hidden');
                btnGazoil.className = "px-2.5 py-1 text-[10.5px] font-bold rounded-lg bg-[#FF9F1C] text-slate-950";
                btnSsp.className = "px-2.5 py-1 text-[10.5px] font-bold rounded-lg bg-slate-200 dark:bg-white/10 text-slate-700 dark:text-slate-300";
            }} else {{
                gazoilBox.classList.add('hidden');
                sspBox.classList.remove('hidden');
                btnSsp.className = "px-2.5 py-1 text-[10.5px] font-bold rounded-lg bg-[#00F5A0] text-slate-950";
                btnGazoil.className = "px-2.5 py-1 text-[10.5px] font-bold rounded-lg bg-slate-200 dark:bg-white/10 text-slate-700 dark:text-slate-300";
            }}
        }}

        function closeModalHistory() {{
            document.getElementById('modalHistory').classList.add('hidden');
        }}
    </script>
    """
    return HTMLResponse(layout(content, "tableau", request=request))

@router.post("/home/update-prix-unique")
async def update_prix_unique_home(
    produit: str = Form(...), 
    prix: float = Form(...),
    activer_immediat: str = Form(None),
    date_effet: str = Form(None)
):
    conn = get_db_connection()
    ensure_schema(conn)
    cibles = ['GAZOIL', 'Gazoil', 'Diesel', 'GO', 'Gasoil 10'] if produit in ['GAZOIL', 'Gazoil', 'Diesel', 'GO', 'Gasoil 10'] else ['SSP', 'Essence', 'Sans Plomb']
    save_name = 'GAZOIL' if produit in ['GAZOIL', 'Gazoil', 'Diesel', 'GO', 'Gasoil 10'] else 'SSP'
    placeholders = ",".join(["?"] * len(cibles))

    is_immediate = (activer_immediat == "1")
    now_dt = datetime.now()
    
    if is_immediate or not date_effet:
        date_formatted = now_dt.strftime("%d/%m/%Y %H:%M")
        conn.execute(f"UPDATE prix_vente SET statut = 'INACTIF' WHERE produit IN ({placeholders})", cibles)
        conn.execute(
            "INSERT INTO prix_vente (date, date_effet, produit, prix, statut) VALUES (?, ?, ?, ?, 'ACTIF')",
            (date_formatted, date_formatted, save_name, prix)
        )
    else:
        try:
            scheduled_dt = datetime.strptime(date_effet, "%Y-%m-%dT%H:%M")
            date_formatted = scheduled_dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            scheduled_dt = now_dt
            date_formatted = date_effet

        if scheduled_dt <= now_dt:
            conn.execute(f"UPDATE prix_vente SET statut = 'INACTIF' WHERE produit IN ({placeholders})", cibles)
            conn.execute(
                "INSERT INTO prix_vente (date, date_effet, produit, prix, statut) VALUES (?, ?, ?, ?, 'ACTIF')",
                (date_formatted, date_formatted, save_name, prix)
            )
        else:
            conn.execute(
                "INSERT INTO prix_vente (date, date_effet, produit, prix, statut) VALUES (?, ?, ?, ?, 'PROGRAMME')",
                (date_formatted, date_formatted, save_name, prix)
            )

    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/home/activer-prix")
async def activer_prix_home(id: int = Form(...)):
    conn = get_db_connection()
    row = conn.execute("SELECT produit FROM prix_vente WHERE id = ?", (id,)).fetchone()
    if row:
        prod = row['produit']
        cibles = ['GAZOIL', 'Gazoil', 'Diesel', 'GO', 'Gasoil 10'] if prod in ['GAZOIL', 'Gazoil', 'Diesel', 'GO', 'Gasoil 10'] else ['SSP', 'Essence', 'Sans Plomb']
        placeholders = ",".join(["?"] * len(cibles))
        conn.execute(f"UPDATE prix_vente SET statut = 'INACTIF' WHERE produit IN ({placeholders})", cibles)
        conn.execute("UPDATE prix_vente SET statut = 'ACTIF' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)