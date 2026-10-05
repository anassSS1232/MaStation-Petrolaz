
# pages/prix.py
import html
from datetime import datetime
from fastapi import APIRouter, Form, Query, Request, status
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

def get_row_val(row, key, default=""):
    if not row:
        return default
    try:
        val = row[key]
        return val if val is not None else default
    except Exception:
        return default

def update_scheduled_prices(conn):
    """Active automatiquement les prix dont l'échéance est arrivée."""
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

@router.get("/prix", response_class=HTMLResponse)
async def prix_page(request: Request, status_filter: str = Query("Tous")):
    conn = get_db_connection()
    update_scheduled_prices(conn)
    
    query = "SELECT * FROM prix_vente WHERE 1=1"
    params = []
    if status_filter and status_filter != "Tous":
        query += " AND statut = ?"
        params.append(status_filter.upper())
    
    query += " ORDER BY id DESC"
    all_prices = conn.execute(query, params).fetchall()
    conn.close()

    diesel_history = [p for p in all_prices if p['produit'] in ['GAZOIL', 'Gazoil', 'Diesel', 'GO', 'Gasoil 10']]
    ssp_history = [p for p in all_prices if p['produit'] in ['SSP', 'Essence', 'Sans Plomb']]

    def generate_price_card(p):
        is_actif = p['statut'] == "ACTIF"
        is_prog = p['statut'] == "PROGRAMME"
        
        if is_actif:
            border_cls = "border-emerald-500/30 bg-emerald-500/10"
            status_action = """
                <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-emerald-500/20 text-[#00F5A0]">
                    ● Actuel
                </span>
            """
        elif is_prog:
            border_cls = "border-sky-500/30 bg-sky-500/10"
            status_action = """
                <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-sky-500/20 text-sky-400">
                    ● Programmé
                </span>
            """
        else:
            border_cls = "border-slate-200 dark:border-[#183042] bg-slate-50 dark:bg-[#070E15]"
            status_action = """
                <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-200 dark:bg-slate-800 text-slate-400">
                    Historique
                </span>
            """
        
        date_aff = get_row_val(p, 'date_effet') or get_row_val(p, 'date') or '-'

        return f"""
        <div class="border {border_cls} rounded-xl p-2.5 mb-2 flex justify-between items-center transition">
            <div>
                <p class="text-base font-black font-mono text-slate-900 dark:text-white leading-none">
                    {p['prix']:.3f} <span class="text-[10px] font-sans font-bold text-slate-400">MAD/L</span>
                </p>
                <span class="text-[10px] font-mono text-slate-500 mt-1 block">Date d'effet : <b>{date_aff}</b></span>
            </div>
            <div>
                {status_action}
            </div>
        </div>
        """

    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M")

    content = f"""
    <div class="h-full flex flex-col gap-3 animate-in fade-in duration-200">
        
        <div class="flex justify-between items-center bg-white dark:bg-[#0E1B26] px-4 py-2.5 rounded-2xl border border-slate-200/90 dark:border-[#183042] shadow-xs">
            <div class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-xl bg-[#00F5A0]/10 text-[#00F5A0] flex items-center justify-center">
                    <i data-lucide="tag" class="w-4 h-4"></i>
                </div>
                <h1 class="text-xs sm:text-sm font-black text-slate-900 dark:text-white uppercase tracking-wider">
                    Tarifs des Carburants (SSP & Diesel)
                </h1>
            </div>
            <button onclick="toggleModal(true)" class="inline-flex items-center gap-1 px-3.5 py-1.5 rounded-xl bg-[#00F5A0] hover:bg-[#00D084] text-slate-950 font-black text-xs uppercase shadow-xs transition active:scale-95">
                <i data-lucide="plus" class="w-3.5 h-3.5 stroke-[3]"></i>
                <span>Nouveau Tarif</span>
            </button>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-3 flex-1 overflow-y-auto">
            
            <div class="bg-white dark:bg-[#0E1B26] rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs p-3 flex flex-col justify-between">
                <div class="flex justify-between items-center pb-2 mb-2 border-b border-slate-100 dark:border-[#183042]">
                    <span class="font-black uppercase tracking-wider text-[#00F5A0] text-xs flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-[#00F5A0]"></span> SSP
                    </span>
                    <span class="text-[10px] font-mono text-slate-400">{len(ssp_history)} tarif(s) enregistré(s)</span>
                </div>
                <div class="flex-1 overflow-y-auto max-h-[420px] pr-1">
                    {"".join([generate_price_card(p) for p in ssp_history]) if ssp_history else '<p class="text-center text-slate-400 text-xs py-8 italic">Aucun tarif enregistré</p>'}
                </div>
            </div>

            <div class="bg-white dark:bg-[#0E1B26] rounded-2xl border border-slate-200 dark:border-[#183042] shadow-xs p-3 flex flex-col justify-between">
                <div class="flex justify-between items-center pb-2 mb-2 border-b border-slate-100 dark:border-[#183042]">
                    <span class="font-black uppercase tracking-wider text-[#00F5A0] text-xs flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-[#00F5A0]"></span> Diesel (Gazoil)
                    </span>
                    <span class="text-[10px] font-mono text-slate-400">{len(diesel_history)} tarif(s) enregistré(s)</span>
                </div>
                <div class="flex-1 overflow-y-auto max-h-[420px] pr-1">
                    {"".join([generate_price_card(p) for p in diesel_history]) if diesel_history else '<p class="text-center text-slate-400 text-xs py-8 italic">Aucun tarif enregistré</p>'}
                </div>
            </div>

        </div>
    </div>

    <div id="modalAddPrix" class="fixed inset-0 bg-slate-950/70 backdrop-blur-xs hidden z-50 flex items-center justify-center p-3">
        <form action="/update-prix" method="post" class="bg-white dark:bg-[#0E1B26] w-full max-w-sm rounded-2xl border border-slate-200 dark:border-[#183042] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150">
            <div class="p-3 border-b border-slate-200 dark:border-[#183042] flex justify-between items-center bg-slate-50 dark:bg-[#070E15]">
                <div class="flex items-center gap-2">
                    <i data-lucide="tag" class="w-4 h-4 text-[#00F5A0]"></i>
                    <h3 class="text-xs font-black text-slate-900 dark:text-white uppercase">Appliquer un Nouveau Tarif</h3>
                </div>
                <button type="button" onclick="toggleModal(false)" class="text-slate-400 hover:text-white font-bold text-xs">✕</button>
            </div>
            
            <div class="p-4 space-y-3 text-xs">
                <div>
                    <label class="text-[10.5px] font-bold text-slate-700 dark:text-slate-300 uppercase mb-1 block">Produit</label>
                    <select name="produit" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-200 dark:border-[#183042] rounded-xl px-2.5 py-1.5 font-bold outline-none text-slate-900 dark:text-white">
                        <option value="SSP">SSP</option>
                        <option value="GAZOIL">Diesel / Gazoil</option>
                    </select>
                </div>

                <div>
                    <label class="text-[10.5px] font-bold text-emerald-600 dark:text-[#00F5A0] uppercase mb-1 block">Prix (MAD / Litre) *</label>
                    <input type="number" step="0.001" name="nouveau_prix" placeholder="Ex: 14.500" required class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-200 dark:border-[#183042] focus:border-[#00F5A0] rounded-xl px-2.5 py-2 font-black font-mono text-[#00F5A0] text-base outline-none">
                </div>

                <div class="bg-slate-50 dark:bg-[#070E15] p-2.5 rounded-xl border border-slate-200 dark:border-[#183042]">
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" id="modal_prix_immediate" name="activer_immediat" value="1" checked onchange="togglePrixModalDate(this.checked)" class="w-4 h-4 rounded accent-[#00F5A0] cursor-pointer">
                        <span class="text-[10.5px] font-bold text-slate-700 dark:text-slate-200 uppercase">Activer immédiatement</span>
                    </label>
                </div>

                <div id="modal_prix_date_wrapper" class="hidden space-y-1 bg-slate-50 dark:bg-[#070E15] p-2.5 rounded-xl border border-slate-200 dark:border-[#183042]">
                    <label class="text-[10px] font-bold uppercase block tracking-wider text-sky-500">
                        Date & Heure d'effet (Automatique)
                    </label>
                    <input type="datetime-local" id="input_prix_date_effet" name="date_effet" value="{now_iso}" class="w-full bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#183042] rounded-lg p-2 font-mono text-xs text-slate-900 dark:text-white outline-none">
                </div>
            </div>
            
            <div class="p-3 bg-slate-50 dark:bg-[#070E15] border-t border-slate-200 dark:border-[#183042] flex justify-end gap-1.5">
                <button type="button" onclick="toggleModal(false)" class="px-3 py-1.5 rounded-xl text-xs font-bold text-slate-400 hover:text-white">Annuler</button>
                <button type="submit" class="px-4 py-1.5 rounded-xl bg-[#00F5A0] text-slate-950 font-black text-xs uppercase shadow-xs hover:bg-[#00D084] transition active:scale-95">Enregistrer</button>
            </div>
        </form>
    </div>

    <script>
        function togglePrixModalDate(isImmediate) {{
            const wrapper = document.getElementById('modal_prix_date_wrapper');
            const dateInput = document.getElementById('input_prix_date_effet');
            if (isImmediate) {{
                wrapper.classList.add('hidden');
                dateInput.removeAttribute('required');
            }} else {{
                wrapper.classList.remove('hidden');
                dateInput.setAttribute('required', 'required');
            }}
        }}

        function toggleModal(show) {{
            const modal = document.getElementById('modalAddPrix');
            modal.classList.toggle('hidden', !show);
            if (show) {{
                const chk = document.getElementById('modal_prix_immediate');
                chk.checked = true;
                togglePrixModalDate(true);
            }}
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}
    </script>
    """
    return HTMLResponse(layout(content, "prix", request=request))

@router.post("/update-prix")
async def update_prix(
    produit: str = Form(...), 
    nouveau_prix: float = Form(...),
    activer_immediat: str = Form(None),
    date_effet: str = Form(None)
):
    conn = get_db_connection()
    ensure_schema(conn)
    cibles = ['GAZOIL', 'Gasoil', 'Diesel', 'GO', 'Gasoil 10'] if produit in ['GAZOIL', 'Gasoil', 'Diesel', 'GO', 'Gasoil 10'] else ['SSP', 'Essence', 'Sans Plomb']
    save_name = 'GAZOIL' if produit in ['GAZOIL', 'Gasoil', 'Diesel', 'GO', 'Gasoil 10'] else 'SSP'
    placeholders = ",".join(["?"] * len(cibles))
    
    is_immediate = (activer_immediat == "1")
    now_dt = datetime.now()

    if is_immediate or not date_effet:
        date_formatted = now_dt.strftime("%d/%m/%Y %H:%M")
        conn.execute(f"UPDATE prix_vente SET statut = 'INACTIF' WHERE produit IN ({placeholders})", cibles)
        conn.execute(
            "INSERT INTO prix_vente (date, date_effet, produit, prix, statut) VALUES (?, ?, ?, ?, 'ACTIF')",
            (date_formatted, date_formatted, save_name, nouveau_prix)
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
                (date_formatted, date_formatted, save_name, nouveau_prix)
            )
        else:
            conn.execute(
                "INSERT INTO prix_vente (date, date_effet, produit, prix, statut) VALUES (?, ?, ?, ?, 'PROGRAMME')",
                (date_formatted, date_formatted, save_name, nouveau_prix)
            )

    conn.commit()
    conn.close()
    return RedirectResponse(url="/prix", status_code=status.HTTP_303_SEE_OTHER)
