# pages/notes.py
import html
from datetime import datetime
from fastapi import APIRouter, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse

from ui_utils import layout
from database import get_db_connection

router = APIRouter()

NOTE_THEMES = {
    "yellow": {
        "label": "Ambre",
        "border": "border-amber-500/60 hover:border-amber-400",
        "top_bar": "from-amber-400 to-yellow-500",
        "gradient": "from-amber-500/25 via-[#231805]/90 to-slate-950/95",
        "title": "text-amber-300",
        "dot": "bg-amber-400 shadow-[0_0_12px_rgba(251,191,36,1)]",
        "badge": "bg-amber-500/20 border-amber-500/40 text-amber-300",
        "shadow": "shadow-[0_8px_30px_-6px_rgba(245,158,11,0.35)]",
        "glow": "hover:shadow-[0_12px_35px_-4px_rgba(245,158,11,0.55)]",
        "btn_hover": "hover:bg-amber-500/25 text-amber-200",
        "hex": "#F59E0B"
    },
    "blue": {
        "label": "Cyan",
        "border": "border-sky-500/60 hover:border-sky-400",
        "top_bar": "from-sky-400 to-blue-500",
        "gradient": "from-sky-500/25 via-[#082032]/90 to-slate-950/95",
        "title": "text-sky-300",
        "dot": "bg-sky-400 shadow-[0_0_12px_rgba(56,189,248,1)]",
        "badge": "bg-sky-500/20 border-sky-500/40 text-sky-300",
        "shadow": "shadow-[0_8px_30px_-6px_rgba(14,165,233,0.35)]",
        "glow": "hover:shadow-[0_12px_35px_-4px_rgba(14,165,233,0.55)]",
        "btn_hover": "hover:bg-sky-500/25 text-sky-200",
        "hex": "#0EA5E9"
    },
    "green": {
        "label": "Émeraude",
        "border": "border-emerald-500/60 hover:border-emerald-400",
        "top_bar": "from-emerald-400 to-teal-500",
        "gradient": "from-emerald-500/25 via-[#062419]/90 to-slate-950/95",
        "title": "text-emerald-300",
        "dot": "bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,1)]",
        "badge": "bg-emerald-500/20 border-emerald-500/40 text-emerald-300",
        "shadow": "shadow-[0_8px_30px_-6px_rgba(16,185,129,0.35)]",
        "glow": "hover:shadow-[0_12px_35px_-4px_rgba(16,185,129,0.55)]",
        "btn_hover": "hover:bg-emerald-500/25 text-emerald-200",
        "hex": "#10B981"
    },
    "pink": {
        "label": "Rose / Rouge",
        "border": "border-rose-500/60 hover:border-rose-400",
        "top_bar": "from-rose-400 to-pink-600",
        "gradient": "from-rose-500/25 via-[#2b0c16]/90 to-slate-950/95",
        "title": "text-rose-300",
        "dot": "bg-rose-400 shadow-[0_0_12px_rgba(251,113,133,1)]",
        "badge": "bg-rose-500/20 border-rose-500/40 text-rose-300",
        "shadow": "shadow-[0_8px_30px_-6px_rgba(244,63,94,0.35)]",
        "glow": "hover:shadow-[0_12px_35px_-4px_rgba(244,63,94,0.55)]",
        "btn_hover": "hover:bg-rose-500/25 text-rose-200",
        "hex": "#F43F5E"
    },
    "purple": {
        "label": "Violet",
        "border": "border-purple-500/60 hover:border-purple-400",
        "top_bar": "from-purple-400 to-indigo-500",
        "gradient": "from-purple-500/25 via-[#220c33]/90 to-slate-950/95",
        "title": "text-purple-300",
        "dot": "bg-purple-400 shadow-[0_0_12px_rgba(192,132,252,1)]",
        "badge": "bg-purple-500/20 border-purple-500/40 text-purple-300",
        "shadow": "shadow-[0_8px_30px_-6px_rgba(168,85,247,0.35)]",
        "glow": "hover:shadow-[0_12px_35px_-4px_rgba(168,85,247,0.55)]",
        "btn_hover": "hover:bg-purple-500/25 text-purple-200",
        "hex": "#A855F7"
    }
}

@router.get("/notes", response_class=HTMLResponse)
async def notes_page(request: Request):
    conn = get_db_connection()
    raw_notes = conn.execute("SELECT * FROM notes ORDER BY id DESC").fetchall()
    notes = [dict(n) for n in raw_notes]
    conn.close()

    cards_html = ""
    for n in notes:
        n_id = n["id"]
        titre = html.escape(n.get("titre") or "NOTE")
        raw_contenu = n.get("contenu") or ""
        contenu = html.escape(raw_contenu).replace("\n", "<br>")
        
        attr_titre = html.escape(n.get("titre") or "", quote=True)
        attr_contenu = html.escape(raw_contenu, quote=True)
        
        couleur = n.get("couleur") if n.get("couleur") in NOTE_THEMES else "yellow"
        theme = NOTE_THEMES[couleur]
        date_c = n.get("date_creation") or ""
        auteur = html.escape(n.get("auteur") or "Safouane")

        cards_html += f"""
        <!-- NOTE CARD #{n_id} -->
        <div class="note-item group relative flex flex-col justify-between rounded-2xl bg-gradient-to-b {theme['gradient']} backdrop-blur-xl border {theme['border']} p-5 {theme['shadow']} {theme['glow']} transition-all duration-300 hover:-translate-y-1.5 overflow-hidden"
             data-search="{titre.lower()} {html.escape(raw_contenu.lower(), quote=True)}">
            
            <!-- Ligne lumineuse en haut de carte -->
            <div class="absolute inset-x-0 top-0 h-1 bg-gradient-to-r {theme['top_bar']}"></div>

            <div>
                <!-- En-tête de carte -->
                <div class="flex items-start justify-between gap-3 pb-3 border-b border-white/10">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <span class="w-2.5 h-2.5 rounded-full shrink-0 {theme['dot']}"></span>
                        <h3 class="text-sm font-black tracking-wider {theme['title']} uppercase truncate">
                            {titre}
                        </h3>
                    </div>
                    
                    <!-- Actions -->
                    <div class="flex items-center gap-1 shrink-0 opacity-85 group-hover:opacity-100 transition-opacity">
                        <!-- Palette -->
                        <div class="relative">
                            <button type="button" 
                                    onclick="togglePalette(event, {n_id})" 
                                    class="w-7 h-7 rounded-lg bg-black/30 {theme['btn_hover']} flex items-center justify-center transition border border-white/10" 
                                    title="Changer couleur">
                                <i data-lucide="palette" class="w-3.5 h-3.5"></i>
                            </button>
                            
                            <div id="palette-popover-{n_id}" class="hidden absolute right-0 top-9 bg-[#0B131B]/95 backdrop-blur-md p-2 rounded-xl border border-white/15 shadow-2xl flex gap-1.5 z-30">
                                <button type="button" onclick="changeColor({n_id}, 'green')" class="w-5 h-5 rounded-full bg-[#10B981] hover:scale-125 transition ring-1 ring-white/30"></button>
                                <button type="button" onclick="changeColor({n_id}, 'blue')" class="w-5 h-5 rounded-full bg-[#0EA5E9] hover:scale-125 transition ring-1 ring-white/30"></button>
                                <button type="button" onclick="changeColor({n_id}, 'purple')" class="w-5 h-5 rounded-full bg-[#A855F7] hover:scale-125 transition ring-1 ring-white/30"></button>
                                <button type="button" onclick="changeColor({n_id}, 'pink')" class="w-5 h-5 rounded-full bg-[#F43F5E] hover:scale-125 transition ring-1 ring-white/30"></button>
                                <button type="button" onclick="changeColor({n_id}, 'yellow')" class="w-5 h-5 rounded-full bg-[#F59E0B] hover:scale-125 transition ring-1 ring-white/30"></button>
                            </div>
                        </div>

                        <!-- Modifier -->
                        <button type="button" 
                                data-id="{n_id}"
                                data-titre="{attr_titre}"
                                data-contenu="{attr_contenu}"
                                data-couleur="{couleur}"
                                onclick="openEditModal(this)"
                                class="w-7 h-7 rounded-lg bg-black/30 {theme['btn_hover']} flex items-center justify-center transition border border-white/10" 
                                title="Modifier">
                            <i data-lucide="pencil" class="w-3.5 h-3.5"></i>
                        </button>
                        
                        <!-- Supprimer -->
                        <form action="/notes/delete" method="post" class="m-0 inline" onsubmit="return confirm('Supprimer ce mémo ?');">
                            <input type="hidden" name="id" value="{n_id}">
                            <button type="submit" class="w-7 h-7 rounded-lg bg-black/30 hover:bg-rose-500/30 text-slate-300 hover:text-rose-300 flex items-center justify-center transition border border-white/10" title="Supprimer">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </form>
                    </div>
                </div>

                <!-- Contenu mémo -->
                <div class="py-4 text-[13.5px] leading-relaxed text-slate-100 font-medium whitespace-pre-line max-h-60 overflow-y-auto pr-1">
                    {contenu}
                </div>
            </div>

            <!-- Footer métadonnées -->
            <div class="pt-3 border-t border-white/10 flex items-center justify-between text-[11px]">
                <div class="flex items-center gap-1.5 text-slate-300/80 font-mono">
                    <i data-lucide="clock" class="w-3.5 h-3.5 text-slate-400"></i>
                    <span>{date_c}</span>
                </div>
                
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-extrabold uppercase tracking-wider text-[10px] border {theme['badge']}">
                    <i data-lucide="user" class="w-2.5 h-2.5"></i>
                    {auteur}
                </span>
            </div>
        </div>
        """

    if not notes:
        cards_html = """
        <div id="emptyContainer" class="col-span-full py-20 text-center">
            <div class="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 text-emerald-400 mx-auto flex items-center justify-center mb-3 shadow-inner">
                <i data-lucide="sticky-note" class="w-8 h-8"></i>
            </div>
            <p class="text-base font-bold text-white">Aucun mémo pour l'instant</p>
            <p class="text-xs text-slate-400 mt-1 max-w-sm mx-auto">Créez votre premier mémo ou consigne d'équipe avec le bouton ci-dessous.</p>
        </div>
        """

    total_count = len(notes)

    content = f"""
    <div class="max-w-7xl mx-auto px-3 sm:px-6 py-4 relative min-h-[85vh]" onclick="closeAllPalettes()">
        
        <!-- BARRE SUPÉRIEURE -->
        <div class="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 mb-6 p-4 rounded-2xl bg-[#0B131B]/85 backdrop-blur-xl border border-white/10 shadow-2xl">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400/20 to-teal-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <i data-lucide="message-square-text" class="w-5 h-5"></i>
                </div>
                <div>
                    <h1 class="text-lg font-black tracking-wide text-white uppercase flex items-center gap-2">
                        Notes & Mémos
                        <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">{total_count}</span>
                    </h1>
                    <p class="text-xs text-slate-400">Consignes, relèves de quart et rappels station</p>
                </div>
            </div>

            <!-- Recherche et Bouton rapide -->
            <div class="flex items-center gap-3">
                <div class="relative flex-1 sm:w-64">
                    <i data-lucide="search" class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
                    <input type="text" 
                           id="searchInput" 
                           oninput="filterNotes(this.value)" 
                           placeholder="Rechercher un mémo..." 
                           class="w-full pl-9 pr-3 py-2 bg-white/5 border border-white/10 rounded-xl text-xs text-white placeholder-slate-400 outline-none focus:border-emerald-400/60 focus:bg-white/10 transition">
                </div>

                <button type="button" onclick="openAddModal()" class="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-slate-950 font-black text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-emerald-500/30 active:scale-95 transition">
                    <i data-lucide="plus" class="w-4 h-4 stroke-[3]"></i>
                    <span class="hidden sm:inline">Nouveau Mémo</span>
                </button>
            </div>
        </div>

        <!-- GRILLE DE CARTES -->
        <div id="notesGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {cards_html}
        </div>

        <!-- BOUTON FLOTTANT -->
        <div class="fixed bottom-6 right-6 z-40">
            <button type="button" onclick="openAddModal()" class="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 text-slate-950 flex items-center justify-center shadow-2xl shadow-emerald-500/50 hover:scale-110 active:scale-95 transition-all group" title="Ajouter un mémo">
                <i data-lucide="plus" class="w-7 h-7 stroke-[3] group-hover:rotate-90 transition-transform duration-300"></i>
            </button>
        </div>

    </div>

    <!-- MODAL -->
    <div id="noteModal" class="fixed inset-0 bg-slate-950/85 backdrop-blur-md hidden z-50 flex items-center justify-center p-4">
        <form action="/notes/save" method="post" class="bg-[#0D1620] border border-white/15 w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden">
            <input type="hidden" id="modal_id" name="id" value="0">
            <input type="hidden" id="modal_couleur" name="couleur" value="green">

            <!-- Header Modal -->
            <div class="p-5 border-b border-white/10 flex justify-between items-center bg-white/[0.02]">
                <div class="flex items-center gap-2.5">
                    <div id="modal_dot" class="w-3 h-3 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></div>
                    <h3 id="modal_title" class="text-sm font-black text-white uppercase tracking-wider">Nouveau Mémo</h3>
                </div>
                <button type="button" onclick="closeNoteModal()" class="w-8 h-8 rounded-xl bg-white/5 hover:bg-white/15 text-slate-400 hover:text-white flex items-center justify-center transition">✕</button>
            </div>

            <!-- Body Modal -->
            <div class="p-6 space-y-4">
                <div>
                    <label class="text-[11px] font-black uppercase mb-1.5 block text-slate-400 tracking-wider">Titre du mémo</label>
                    <input type="text" id="modal_titre" name="titre" placeholder="Ex: Lavage auto, Consigne relève..." class="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs font-bold text-white outline-none focus:border-emerald-400 uppercase transition">
                </div>

                <div>
                    <label class="text-[11px] font-black uppercase mb-2 block text-slate-400 tracking-wider">Couleur thématique</label>
                    <div class="flex items-center gap-3">
                        <button type="button" onclick="selectModalColor('green', this)" class="modal-color-opt w-8 h-8 rounded-xl bg-[#10B981] ring-2 ring-white ring-offset-2 ring-offset-slate-900 transition hover:scale-105" data-color="green"></button>
                        <button type="button" onclick="selectModalColor('blue', this)" class="modal-color-opt w-8 h-8 rounded-xl bg-[#0EA5E9] transition hover:scale-105 opacity-60" data-color="blue"></button>
                        <button type="button" onclick="selectModalColor('purple', this)" class="modal-color-opt w-8 h-8 rounded-xl bg-[#A855F7] transition hover:scale-105 opacity-60" data-color="purple"></button>
                        <button type="button" onclick="selectModalColor('pink', this)" class="modal-color-opt w-8 h-8 rounded-xl bg-[#F43F5E] transition hover:scale-105 opacity-60" data-color="pink"></button>
                        <button type="button" onclick="selectModalColor('yellow', this)" class="modal-color-opt w-8 h-8 rounded-xl bg-[#F59E0B] transition hover:scale-105 opacity-60" data-color="yellow"></button>
                    </div>
                </div>

                <div>
                    <label class="text-[11px] font-black uppercase mb-1.5 block text-slate-400 tracking-wider">Détails & Contenu</label>
                    <textarea id="modal_contenu" name="contenu" rows="6" required placeholder="Tapez vos consignes, montants ou notes..." class="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-slate-100 outline-none focus:border-emerald-400 leading-relaxed transition"></textarea>
                </div>
            </div>

            <!-- Footer Modal -->
            <div class="p-4 bg-white/[0.02] border-t border-white/10 flex gap-3">
                <button type="button" onclick="closeNoteModal()" class="flex-1 bg-white/5 hover:bg-white/10 text-slate-300 py-2.5 rounded-xl font-bold uppercase text-[11px] transition">Annuler</button>
                <button type="submit" class="flex-1 bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-slate-950 py-2.5 rounded-xl font-black uppercase text-[11px] shadow-lg shadow-emerald-500/20 active:scale-95 transition">Enregistrer</button>
            </div>
        </form>
    </div>

    <script>
        const THEME_DOTS = {{
            yellow: "bg-amber-400 shadow-[0_0_12px_rgba(251,191,36,1)]",
            blue: "bg-sky-400 shadow-[0_0_12px_rgba(56,189,248,1)]",
            green: "bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,1)]",
            pink: "bg-rose-400 shadow-[0_0_12px_rgba(251,113,133,1)]",
            purple: "bg-purple-400 shadow-[0_0_12px_rgba(192,132,252,1)]"
        }};

        function filterNotes(query) {{
            const q = query.toLowerCase().trim();
            document.querySelectorAll('.note-item').forEach(card => {{
                const content = card.getAttribute('data-search') || '';
                card.style.display = (!q || content.includes(q)) ? 'flex' : 'none';
            }});
        }}

        function togglePalette(event, id) {{
            event.stopPropagation();
            closeAllPalettes();
            const pop = document.getElementById('palette-popover-' + id);
            if (pop) pop.classList.toggle('hidden');
        }}

        function closeAllPalettes() {{
            document.querySelectorAll('[id^="palette-popover-"]').forEach(el => el.classList.add('hidden'));
        }}

        function changeColor(id, color) {{
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/notes/set-color';

            const inId = document.createElement('input');
            inId.type = 'hidden';
            inId.name = 'id';
            inId.value = id;

            const inColor = document.createElement('input');
            inColor.type = 'hidden';
            inColor.name = 'couleur';
            inColor.value = color;

            form.appendChild(inId);
            form.appendChild(inColor);
            document.body.appendChild(form);
            form.submit();
        }}

        function selectModalColor(color, btn) {{
            document.getElementById('modal_couleur').value = color;
            document.querySelectorAll('.modal-color-opt').forEach(b => {{
                b.className = "modal-color-opt w-8 h-8 rounded-xl transition hover:scale-105 opacity-60 " + b.className.split(' ').find(c => c.startsWith('bg-'));
            }});
            if (btn) {{
                btn.className = "modal-color-opt w-8 h-8 rounded-xl ring-2 ring-white ring-offset-2 ring-offset-slate-900 transition hover:scale-105 opacity-100 " + btn.className.split(' ').find(c => c.startsWith('bg-'));
            }}
            const dot = document.getElementById('modal_dot');
            if (dot && THEME_DOTS[color]) {{
                dot.className = "w-3 h-3 rounded-full " + THEME_DOTS[color];
            }}
        }}

        function openAddModal() {{
            document.getElementById('modal_id').value = '0';
            document.getElementById('modal_title').innerText = 'Nouveau Mémo';
            document.getElementById('modal_titre').value = '';
            document.getElementById('modal_contenu').value = '';
            selectModalColor('green', document.querySelector('.modal-color-opt[data-color="green"]'));
            document.getElementById('noteModal').classList.remove('hidden');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function openEditModal(btn) {{
            const id = btn.getAttribute('data-id');
            const titre = btn.getAttribute('data-titre') || '';
            const contenu = btn.getAttribute('data-contenu') || '';
            const couleur = btn.getAttribute('data-couleur') || 'green';

            document.getElementById('modal_id').value = id;
            document.getElementById('modal_title').innerText = 'Modifier le Mémo';
            document.getElementById('modal_titre').value = titre;
            document.getElementById('modal_contenu').value = contenu;
            selectModalColor(couleur, document.querySelector(`.modal-color-opt[data-color="${{couleur}}"]`));

            document.getElementById('noteModal').classList.remove('hidden');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function closeNoteModal() {{
            document.getElementById('noteModal').classList.add('hidden');
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }});
    </script>
    """
    return HTMLResponse(layout(content, "notes", request=request))

@router.post("/notes/save")
async def save_note(
    request: Request,
    id: int = Form(0),
    titre: str = Form(""),
    contenu: str = Form(...),
    couleur: str = Form("green")
):
    conn = get_db_connection()
    user = getattr(request.state, "user", None)
    user_nom = user.get("nom_complet", "Admin") if user else "Admin"

    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    clean_titre = titre.strip().upper() if titre else "MÉMO"

    if id > 0:
        conn.execute("""
            UPDATE notes 
            SET titre = ?, contenu = ?, couleur = ?
            WHERE id = ?
        """, (clean_titre, contenu.strip(), couleur, id))
    else:
        conn.execute("""
            INSERT INTO notes (titre, contenu, couleur, est_epingle, date_creation, auteur)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (clean_titre, contenu.strip(), couleur, date_str, user_nom))

    conn.commit()
    conn.close()
    return RedirectResponse(url="/notes", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/notes/set-color")
async def set_note_color(id: int = Form(...), couleur: str = Form(...)):
    conn = get_db_connection()
    conn.execute("UPDATE notes SET couleur = ? WHERE id = ?", (couleur, id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/notes", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/notes/delete")
async def delete_note(id: int = Form(...)):
    conn = get_db_connection()
    conn.execute("DELETE FROM notes WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/notes", status_code=status.HTTP_303_SEE_OTHER)