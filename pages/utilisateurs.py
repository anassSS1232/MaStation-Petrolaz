# pages/utilisateurs.py
import html
import json
from datetime import datetime
from fastapi import APIRouter, Request, Form, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse

from database import (
    lister_utilisateurs,
    get_utilisateur_by_id,
    ajouter_utilisateur,
    modifier_utilisateur,
    supprimer_utilisateur
)
from ui_utils import layout

# ==========================================================
# IMPORTATION MODULAIRE DE TOUTES LES ATTESTATIONS SÉPARÉES
# ==========================================================
from pages.attestations.travail import generer_attestation_travail
from pages.attestations.salaire import generer_attestation_salaire
from pages.attestations.conge import generer_attestation_conge
from pages.attestations.contrat import generer_contrat_travail

router = APIRouter(prefix="/utilisateurs", tags=["utilisateurs"])

COLOR_PALETTES = [
    {
        "border": "border-l-[4px] border-l-blue-500",
        "avatar_bg": "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20",
    },
    {
        "border": "border-l-[4px] border-l-emerald-500",
        "avatar_bg": "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20",
    },
    {
        "border": "border-l-[4px] border-l-amber-500",
        "avatar_bg": "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20",
    },
    {
        "border": "border-l-[4px] border-l-purple-500",
        "avatar_bg": "bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20",
    },
    {
        "border": "border-l-[4px] border-l-cyan-500",
        "avatar_bg": "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20",
    },
    {
        "border": "border-l-[4px] border-l-rose-500",
        "avatar_bg": "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20",
    }
]

def get_initials(nom: str) -> str:
    parts = [p for p in (nom or "").strip().split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    elif len(parts) == 1 and len(parts[0]) >= 2:
        return parts[0][:2].upper()
    elif len(parts) == 1:
        return parts[0][0].upper()
    return "EM"

# ==========================================================
# 1. PAGE PRINCIPALE : DOSSIERS COLLABORATEURS
# ==========================================================
@router.get("", response_class=HTMLResponse)
async def page_utilisateurs(
    request: Request,
    q: str = Query(None),
    filtre: str = Query("tous")
):
    users = lister_utilisateurs()
    total_users = len(users)
    today_iso = datetime.now().strftime("%Y-%m-%d")

    cards_html = ""
    table_rows_html = ""

    for idx, u in enumerate(users):
        u_id = u["id"]
        nom_raw = u.get("nom_complet") or "Sans Nom"
        nom_safe = html.escape(nom_raw)
        username_safe = html.escape(u.get("username") or "")
        role_raw = str(u.get("role") or "employe").lower()
        cin_safe = html.escape(u.get("cin") or "—")
        cnss_safe = html.escape(u.get("cnss") or "—")
        tel_safe = html.escape(u.get("telephone") or "+212 600 000 000")
        date_emb_safe = html.escape(u.get("date_embauche") or "—")
        salaire = float(u.get("salaire_base") or 0.0)
        statut = (u.get("statut") or "ACTIF").upper()
        is_actif = (statut == "ACTIF")

        theme = COLOR_PALETTES[idx % len(COLOR_PALETTES)]
        initials = get_initials(nom_raw)

        if role_raw == "admin":
            role_label = "Administrateur"
            badge_role = "bg-amber-500/15 text-[#E5A842] border-amber-500/30"
        elif role_raw == "comptable":
            role_label = "Comptable"
            badge_role = "bg-sky-500/15 text-sky-400 border-sky-500/30"
        else:
            role_label = "Employé (Pompiste)"
            badge_role = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"

        statut_badge = f"""
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
            Actif
        </span>
        """ if is_actif else f"""
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-500/15 text-slate-600 dark:text-slate-400 border border-slate-500/20">
            Inactif
        </span>
        """

        search_blob = f"{nom_raw} {username_safe} {role_label} {cin_safe} {cnss_safe} {tel_safe}".lower()

        user_data_json = html.escape(json.dumps({
            "id": u_id,
            "nom_complet": nom_raw,
            "username": u.get("username") or "",
            "role": role_raw,
            "cin": u.get("cin") or "",
            "cnss": u.get("cnss") or "",
            "telephone": u.get("telephone") or "",
            "date_embauche": u.get("date_embauche") or "",
            "salaire_base": salaire,
            "adresse": u.get("adresse") or "",
            "statut": statut
        }))

        # CARTE DOSSIER
        cards_html += f"""
        <div class="user-card group relative bg-white/95 dark:bg-[#0A1624]/95 backdrop-blur-xl border border-slate-200 dark:border-white/10 rounded-2xl p-4 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between {theme['border']}"
             data-search="{html.escape(search_blob, quote=True)}"
             data-role="{role_raw}"
             data-statut="{'actif' if is_actif else 'inactif'}">
            
            <div>
                <div class="flex items-start justify-between gap-3 pb-3 border-b border-slate-100 dark:border-white/10">
                    <div class="flex items-center gap-3 min-w-0">
                        <div class="w-12 h-12 rounded-2xl flex items-center justify-center font-black text-[15px] tracking-wider shrink-0 {theme['avatar_bg']}">
                            {initials}
                        </div>
                        <div class="min-w-0">
                            <h3 class="font-extrabold text-[15px] text-slate-950 dark:text-white truncate group-hover:text-[#E5A842] transition-colors">
                                {nom_safe}
                            </h3>
                            <div class="flex items-center gap-2 mt-1">
                                <span class="px-2 py-0.5 rounded text-[10.5px] font-black uppercase tracking-wider border {badge_role}">
                                    {role_label}
                                </span>
                                {statut_badge}
                            </div>
                        </div>
                    </div>

                    <span class="text-[11px] font-mono font-bold text-slate-400 bg-slate-100 dark:bg-white/5 px-2 py-1 rounded-lg">
                        @{username_safe}
                    </span>
                </div>

                <div class="py-3 space-y-2 text-[12.5px] text-slate-800 dark:text-slate-200 font-semibold">
                    <div class="flex items-center justify-between">
                        <span class="text-slate-500 dark:text-slate-400 flex items-center gap-1.5"><i data-lucide="phone" class="w-3.5 h-3.5"></i> Tél :</span>
                        <span class="font-mono text-slate-900 dark:text-white">{tel_safe}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-500 dark:text-slate-400 flex items-center gap-1.5"><i data-lucide="id-card" class="w-3.5 h-3.5"></i> CIN / CNSS :</span>
                        <span class="font-mono font-bold text-[#E5A842]">{cin_safe} <span class="text-slate-400">/</span> {cnss_safe}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="text-slate-500 dark:text-slate-400 flex items-center gap-1.5"><i data-lucide="calendar" class="w-3.5 h-3.5"></i> Embauche :</span>
                        <span class="font-mono text-slate-700 dark:text-slate-300">{date_emb_safe}</span>
                    </div>
                    <div class="flex items-center justify-between pt-1.5 border-t border-slate-100 dark:border-white/5">
                        <span class="text-slate-500 dark:text-slate-400 font-bold">Salaire de Base :</span>
                        <span class="font-mono font-black text-emerald-600 dark:text-emerald-400 text-[13.5px]">{salaire:,.2f} MAD</span>
                    </div>
                </div>
            </div>

            <!-- Footer Actions -->
            <div class="pt-3 border-t border-slate-100 dark:border-white/10 flex items-center justify-end gap-2 relative">
                <div class="relative">
                    <button type="button" 
                            onclick="toggleUserMenu(event, 'menu-usr-{u_id}')" 
                            class="w-9 h-9 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 text-slate-600 hover:text-slate-950 dark:text-slate-400 dark:hover:text-white border border-slate-200/60 dark:border-white/5 flex items-center justify-center transition cursor-pointer" 
                            title="Options du collaborateur">
                        <i data-lucide="more-vertical" class="w-4 h-4 stroke-[2]"></i>
                    </button>

                    <!-- Menu Déroulant -->
                    <div id="menu-usr-{u_id}" 
                         class="user-dropdown-menu hidden absolute right-0 bottom-full mb-2 w-52 bg-white dark:bg-[#0c1926] border border-slate-200 dark:border-white/10 rounded-2xl shadow-xl shadow-slate-900/10 dark:shadow-black/50 py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100 font-sans text-left">
                        
                        <button type="button" 
                                data-user="{user_data_json}" 
                                onclick="fermerTousLesMenusUsers(); afficherModalModifierUser(this);" 
                                class="w-full text-left px-3.5 py-2 text-[13px] font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 flex items-center gap-2.5 transition rounded-lg">
                            <i data-lucide="pencil" class="w-4 h-4 text-slate-400 dark:text-slate-500 shrink-0"></i>
                            <span>Modifier</span>
                        </button>

                        <button type="button" 
                                onclick="fermerTousLesMenusUsers(); afficherDocsRH({u_id}, '{nom_safe}', '{role_label}');" 
                                class="w-full text-left px-3.5 py-2 text-[13px] font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 flex items-center gap-2.5 transition rounded-lg">
                            <i data-lucide="file-text" class="w-4 h-4 text-slate-400 dark:text-slate-500 shrink-0"></i>
                            <span>Documents & RH</span>
                        </button>

                        <div class="h-px bg-slate-100 dark:bg-white/10 my-1"></div>

                        <button type="button" 
                                onclick="fermerTousLesMenusUsers(); declencherSuppressionUser({u_id});"
                                class="w-full text-left px-3.5 py-2 text-[13px] font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 flex items-center gap-2.5 transition rounded-lg cursor-pointer">
                            <i data-lucide="trash-2" class="w-4 h-4 text-rose-500 shrink-0"></i>
                            <span>Supprimer</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
        """

        # LIGNE TABLEAU
        table_rows_html += f"""
        <tr class="user-table-row border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/5 transition text-[13px]"
            data-search="{html.escape(search_blob, quote=True)}"
            data-role="{role_raw}">
            <td class="py-3 px-4 font-mono font-bold text-[#E5A842]">@{username_safe}</td>
            <td class="py-3 px-4">
                <div class="font-extrabold text-slate-950 dark:text-white text-[14px]">{nom_safe}</div>
                <div class="text-[12px] text-slate-500 dark:text-slate-400 font-medium">CIN: {cin_safe} • CNSS: {cnss_safe}</div>
            </td>
            <td class="py-3 px-4">
                <span class="px-2.5 py-0.5 rounded text-[11px] font-black uppercase tracking-wider border {badge_role}">
                    {role_label}
                </span>
            </td>
            <td class="py-3 px-4 font-mono text-slate-700 dark:text-slate-300 font-semibold">{tel_safe}</td>
            <td class="py-3 px-4 font-mono font-bold text-right text-emerald-600 dark:text-emerald-400">{salaire:,.2f} MAD</td>
            <td class="py-3 px-4 text-center">{statut_badge}</td>
            <td class="py-3 px-4 text-right whitespace-nowrap">
                <div class="flex items-center justify-end gap-2 relative">
                    <button type="button" 
                            onclick="toggleUserMenu(event, 'menu-tbl-usr-{u_id}')" 
                            class="p-1.5 rounded-lg bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-600 dark:text-slate-300 transition" title="Options">
                        <i data-lucide="more-vertical" class="w-4 h-4"></i>
                    </button>
                    <div id="menu-tbl-usr-{u_id}" 
                         class="user-dropdown-menu hidden absolute right-0 bottom-full mb-1 w-48 bg-white dark:bg-[#0c1926] border border-slate-200 dark:border-white/10 rounded-xl shadow-xl py-1.5 z-50 font-sans text-left">
                        <button type="button" data-user="{user_data_json}" onclick="fermerTousLesMenusUsers(); afficherModalModifierUser(this);" class="w-full text-left px-3 py-2 text-[12.5px] font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 flex items-center gap-2">
                            <i data-lucide="pencil" class="w-3.5 h-3.5 text-slate-400"></i> Modifier
                        </button>
                        <button type="button" onclick="fermerTousLesMenusUsers(); afficherDocsRH({u_id}, '{nom_safe}', '{role_label}');" class="w-full text-left px-3 py-2 text-[12.5px] font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 flex items-center gap-2">
                            <i data-lucide="file-text" class="w-3.5 h-3.5 text-slate-400"></i> Documents RH
                        </button>
                        <div class="h-px bg-slate-100 dark:bg-white/10 my-1"></div>
                        <button type="button" onclick="fermerTousLesMenusUsers(); declencherSuppressionUser({u_id});" class="w-full text-left px-3 py-2 text-[12.5px] font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 flex items-center gap-2 cursor-pointer">
                            <i data-lucide="trash-2" class="w-3.5 h-3.5 text-rose-500"></i> Supprimer
                        </button>
                    </div>
                </div>
            </td>
        </tr>
        """

    content = f"""
    <div class="max-w-7xl mx-auto space-y-4 animate-in fade-in duration-200">
        
        <!-- Formulaire de suppression caché -->
        <form id="formSupprimerUser" method="POST" action="" class="hidden"></form>

        <!-- BANDEAU FUSIONNÉ UNIQUE : TITRE + RECHERCHE + FILTRE + ACTIONS -->
        <div class="bg-white/80 dark:bg-[#0A1624]/80 backdrop-blur-xl p-3 sm:p-3.5 rounded-2xl border border-slate-200 dark:border-white/10 shadow-xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
            
            <!-- GAUCHE : TITRE -->
            <div class="flex items-center gap-3 shrink-0">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-sky-500 text-white flex items-center justify-center shadow-md shadow-blue-500/20 shrink-0">
                    <i data-lucide="user-check" class="w-5 h-5 stroke-[2.5]"></i>
                </div>
                <h1 class="text-base sm:text-lg font-black text-slate-950 dark:text-white tracking-tight">Gestion Employés</h1>
            </div>

            <!-- DROITE : RECHERCHE RÉDUITE + FILTRE + VUE + BOUTON NOUVEAU -->
            <div class="flex flex-wrap items-center justify-end gap-2.5 flex-1">
                
                <!-- Champ Recherche Réduit -->
                <div class="relative w-full sm:w-48 lg:w-56 shrink-0">
                    <i data-lucide="search" class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"></i>
                    <input type="text" id="liveSearchUsers" oninput="filtrerUsersDirect()" value="{q or ''}" 
                           placeholder="Recherche..." 
                           class="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 text-[13px] font-semibold text-slate-950 dark:text-white placeholder-slate-400 outline-none focus:border-[#E5A842] transition">
                </div>

                <!-- Filtre par rôle -->
                <div class="relative min-w-[140px] shrink-0">
                    <select id="filterRoleSelect" onchange="filtrerUsersDirect()"
                            class="w-full pl-8 pr-7 py-2 rounded-xl bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 text-[12.5px] font-bold text-slate-900 dark:text-white outline-none cursor-pointer appearance-none">
                        <option value="tous">Tous les rôles</option>
                        <option value="employe">Employés</option>
                        <option value="comptable">Comptables</option>
                        <option value="admin">Administrateurs</option>
                    </select>
                    <i data-lucide="filter" class="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"></i>
                    <i data-lucide="chevron-down" class="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none"></i>
                </div>

                <!-- Sélecteur Vue Grille / Liste -->
                <div class="inline-flex p-0.5 rounded-xl bg-slate-100 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 shrink-0">
                    <button type="button" id="btnViewGridUsers" onclick="basculerVueUsers('grid')" 
                            class="w-8 h-8 rounded-lg flex items-center justify-center transition bg-blue-600 text-white shadow-xs" title="Vue Grille">
                        <i data-lucide="layout-grid" class="w-4 h-4"></i>
                    </button>
                    <button type="button" id="btnViewListUsers" onclick="basculerVueUsers('list')" 
                            class="w-8 h-8 rounded-lg flex items-center justify-center transition text-slate-500 hover:text-slate-900 dark:hover:text-white" title="Vue Liste">
                        <i data-lucide="list" class="w-4 h-4"></i>
                    </button>
                </div>

                <!-- Bouton Nouveau (Sans le +) -->
                <button type="button" onclick="toggleModalAddUser(true)" 
                        class="inline-flex items-center justify-center px-5 py-2 rounded-xl font-black text-[12.5px] uppercase tracking-wider text-white bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 shadow-md shadow-orange-500/20 transition active:scale-95 cursor-pointer shrink-0">
                    Nouveau
                </button>

            </div>
        </div>

        <!-- 1. GRILLE DE CARTES -->
        <div id="usersGridView" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {cards_html if cards_html else '<div class="col-span-full py-16 text-center text-slate-400 font-bold">Aucun collaborateur trouvé.</div>'}
        </div>

        <!-- 2. VUE TABLEAU -->
        <div id="usersListView" class="hidden bg-white/95 dark:bg-[#0A1624]/95 backdrop-blur-xl rounded-2xl border border-slate-200 dark:border-white/10 shadow-xs overflow-hidden flex-col">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse min-w-[700px]">
                    <thead class="bg-slate-50 dark:bg-[#060D15] border-b border-slate-200 dark:border-white/10 text-[11px] font-black uppercase text-slate-500">
                        <tr>
                            <th class="py-3 px-4 w-32">Identifiant</th>
                            <th class="py-3 px-4">Collaborateur</th>
                            <th class="py-3 px-4">Rôle</th>
                            <th class="py-3 px-4">Téléphone</th>
                            <th class="py-3 px-4 text-right">Salaire Base</th>
                            <th class="py-3 px-4 text-center w-28">Statut</th>
                            <th class="py-3 px-4 text-right w-36">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html if table_rows_html else '<tr><td colspan="7" class="text-center py-12 text-slate-400 text-sm font-semibold">Aucun collaborateur trouvé.</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="flex items-center justify-between px-3 py-2 text-[13px] text-slate-600 dark:text-slate-400 bg-white/50 dark:bg-white/5 rounded-xl border border-slate-200/50 dark:border-white/5">
            <div class="font-medium">
                Effectif total : <span id="countDisplayedUsers" class="font-extrabold text-slate-950 dark:text-white">{total_users}</span> collaborateur(s)
            </div>
            <div class="text-[12px] font-bold text-slate-500">
                PETROLAZ Mansour Dahbi
            </div>
        </div>

    </div>

    <!-- MODALE 1 : NOUVEAU COLLABORATEUR -->
    <div id="modalAddUser" class="fixed inset-0 bg-slate-950/75 backdrop-blur-xs hidden z-50 flex items-center justify-center p-4">
        <form action="/utilisateurs/ajouter" method="POST" 
              class="bg-white dark:bg-[#0A1624] w-full max-w-2xl rounded-3xl border border-slate-200 dark:border-white/10 shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150">
            
            <div class="px-6 py-4 border-b border-slate-200 dark:border-white/10 flex justify-between items-center bg-slate-50/80 dark:bg-[#060D15]/80">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-2xl bg-blue-500/15 text-blue-500 flex items-center justify-center font-bold">
                        <i data-lucide="user-plus" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <h3 class="font-black text-slate-950 dark:text-white text-base tracking-wide uppercase">
                            Nouveau Collaborateur / Pompiste
                        </h3>
                        <p class="text-[12px] text-slate-500 dark:text-slate-400 font-medium">Création de compte d'accès et dossier administratif RH.</p>
                    </div>
                </div>
                <button type="button" onclick="toggleModalAddUser(false)" class="w-8 h-8 rounded-xl text-slate-400 hover:text-slate-950 dark:hover:text-white flex items-center justify-center transition">
                    <i data-lucide="x" class="w-5 h-5"></i>
                </button>
            </div>
            
            <div class="p-6 space-y-4 text-[13px] max-h-[80vh] overflow-y-auto">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Nom & Prénom *</label>
                        <input type="text" id="add_modal_nom" name="nom_complet" required placeholder="Ex: MOHAMED ALAMI" 
                               oninput="genererUsernameModal('add')"
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-bold uppercase text-slate-950 dark:text-white outline-none focus:border-blue-500 text-[13.5px]">
                    </div>
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Rôle & Fonction *</label>
                        <select id="add_modal_role" name="role" required onchange="genererUsernameModal('add')" 
                                class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-bold outline-none text-slate-950 dark:text-white text-[13px]">
                            <option value="employe" selected>Employé (Pompiste)</option>
                            <option value="comptable">Comptable</option>
                            <option value="admin">Administrateur</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Identifiant de Connexion *</label>
                        <input type="text" id="add_modal_username" name="username" required 
                               class="w-full bg-slate-100 dark:bg-[#060D15]/80 border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono font-bold text-[#E5A842] outline-none text-[13px]">
                    </div>
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Mot de Passe Provisoire *</label>
                        <input type="password" name="password" required placeholder="••••••••" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono text-slate-950 dark:text-white outline-none focus:border-blue-500 text-[13px]">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-100 dark:border-white/10">
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">N° CIN</label>
                        <input type="text" name="cin" placeholder="Ex: S123456" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono uppercase text-slate-950 dark:text-white outline-none focus:border-blue-500 text-[13px]">
                    </div>
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">N° CNSS</label>
                        <input type="text" name="cnss" placeholder="Ex: 109283746" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono text-slate-950 dark:text-white outline-none focus:border-blue-500 text-[13px]">
                    </div>
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Téléphone</label>
                        <input type="tel" name="telephone" placeholder="+212 600 000 000" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono text-slate-950 dark:text-white outline-none focus:border-blue-500 text-[13px]">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Date d'Embauche</label>
                        <input type="date" name="date_embauche" value="{today_iso}" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono text-slate-950 dark:text-white outline-none text-[13px]">
                    </div>
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Salaire de Base Mensuel (MAD)</label>
                        <input type="number" step="0.01" name="salaire_base" value="3500.00" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono font-bold text-emerald-600 dark:text-emerald-400 outline-none text-[13px]">
                    </div>
                </div>

                <div>
                    <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Adresse de Résidence</label>
                    <input type="text" name="adresse" placeholder="Quartier, Ville (ex: Nador)" 
                           class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 text-slate-950 dark:text-white outline-none text-[13px]">
                </div>
            </div>

            <div class="px-6 py-4 bg-slate-50/80 dark:bg-[#060D15]/80 border-t border-slate-200 dark:border-white/10 flex justify-end gap-3">
                <button type="button" onclick="toggleModalAddUser(false)" class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 font-bold text-[13px] transition cursor-pointer">Annuler</button>
                <button type="submit" class="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-black text-[13px] uppercase tracking-wider shadow-md transition active:scale-95 cursor-pointer">Créer le Collaborateur</button>
            </div>
        </form>
    </div>

    <!-- MODALE 2 : MODIFIER INFORMATIONS -->
    <div id="modalEditUser" class="fixed inset-0 bg-slate-950/75 backdrop-blur-xs hidden z-50 flex items-center justify-center p-4">
        <form action="/utilisateurs/modifier" method="POST" 
              class="bg-white dark:bg-[#0A1624] w-full max-w-2xl rounded-3xl border border-slate-200 dark:border-white/10 shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150">
            <input type="hidden" id="edit_modal_user_id" name="user_id" value="">

            <div class="px-6 py-4 border-b border-slate-200 dark:border-white/10 flex justify-between items-center bg-slate-50/80 dark:bg-[#060D15]/80">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-2xl bg-amber-500/15 text-amber-500 flex items-center justify-center font-bold">
                        <i data-lucide="edit-3" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <h3 class="font-black text-slate-950 dark:text-white text-base tracking-wide uppercase">
                            Modifier le Dossier Collaborateur
                        </h3>
                        <p class="text-[12px] text-slate-500 dark:text-slate-400 font-medium">Mise à jour des coordonnées, rôle, mot de passe et salaire.</p>
                    </div>
                </div>
                <button type="button" onclick="toggleModalEditUser(false)" class="w-8 h-8 rounded-xl text-slate-400 hover:text-slate-950 dark:hover:text-white flex items-center justify-center transition">
                    <i data-lucide="x" class="w-5 h-5"></i>
                </button>
            </div>
            
            <div class="p-6 space-y-4 text-[13px] max-h-[80vh] overflow-y-auto">
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div class="sm:col-span-2">
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Nom & Prénom *</label>
                        <input type="text" id="edit_modal_nom" name="nom_complet" required 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-bold uppercase text-slate-950 dark:text-white outline-none focus:border-amber-500 text-[13.5px]">
                    </div>
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Statut</label>
                        <select id="edit_modal_statut" name="statut" 
                                class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-bold outline-none text-slate-950 dark:text-white text-[13px]">
                            <option value="ACTIF">ACTIF</option>
                            <option value="INACTIF">INACTIF</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Identifiant *</label>
                        <input type="text" id="edit_modal_username" name="username" required 
                               class="w-full bg-slate-100 dark:bg-[#060D15]/80 border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono font-bold text-[#E5A842] outline-none text-[13px]">
                    </div>
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Rôle & Accès</label>
                        <select id="edit_modal_role" name="role" required 
                                class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-bold outline-none text-slate-950 dark:text-white text-[13px]">
                            <option value="employe">Employé (Pompiste)</option>
                            <option value="comptable">Comptable</option>
                            <option value="admin">Administrateur</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-slate-100 dark:border-white/10">
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">N° CIN</label>
                        <input type="text" id="edit_modal_cin" name="cin" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono uppercase text-slate-950 dark:text-white outline-none text-[13px]">
                    </div>
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">N° CNSS</label>
                        <input type="text" id="edit_modal_cnss" name="cnss" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono text-slate-950 dark:text-white outline-none text-[13px]">
                    </div>
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Téléphone</label>
                        <input type="tel" id="edit_modal_tel" name="telephone" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono text-slate-950 dark:text-white outline-none text-[13px]">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Date d'Embauche</label>
                        <input type="date" id="edit_modal_date_emb" name="date_embauche" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono text-slate-950 dark:text-white outline-none text-[13px]">
                    </div>
                    <div>
                        <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Salaire de Base Mensuel (MAD)</label>
                        <input type="number" step="0.01" id="edit_modal_salaire" name="salaire_base" 
                               class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono font-bold text-emerald-600 dark:text-emerald-400 outline-none text-[13px]">
                    </div>
                </div>

                <div>
                    <label class="font-bold text-slate-900 dark:text-white mb-1.5 block text-[12px]">Changer Mot de Passe (Laisser vide pour conserver)</label>
                    <input type="password" name="password" placeholder="Nouveau mot de passe..." 
                           class="w-full bg-slate-50 dark:bg-[#060D15] border border-slate-300 dark:border-white/10 rounded-xl px-3.5 py-2.5 font-mono text-slate-950 dark:text-white outline-none focus:border-amber-500 text-[13px]">
                </div>
            </div>

            <div class="px-6 py-4 bg-slate-50/80 dark:bg-[#060D15]/80 border-t border-slate-200 dark:border-white/10 flex justify-end gap-3">
                <button type="button" onclick="toggleModalEditUser(false)" class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 font-bold text-[13px] transition cursor-pointer">Annuler</button>
                <button type="submit" class="px-6 py-2.5 rounded-xl bg-[#E5A842] hover:bg-[#d89b35] text-slate-950 font-black text-[13px] uppercase tracking-wider shadow-md transition active:scale-95 cursor-pointer">Mettre à Jour</button>
            </div>
        </form>
    </div>

    <!-- MODALE 3 : ACCÈS AUX DOCUMENTS RH -->
    <div id="modalDocumentsRH" class="fixed inset-0 bg-slate-950/75 backdrop-blur-xs hidden z-50 flex items-center justify-center p-4">
        <div class="bg-white dark:bg-[#0A1624] w-full max-w-lg rounded-3xl border border-slate-200 dark:border-white/10 shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-150">
            
            <div class="px-6 py-4 border-b border-slate-200 dark:border-white/10 flex justify-between items-center bg-slate-50/80 dark:bg-[#060D15]/80">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-2xl bg-sky-500/15 text-sky-500 flex items-center justify-center font-bold">
                        <i data-lucide="file-badge" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <h3 id="doc_modal_nom" class="font-black text-slate-950 dark:text-white text-base tracking-wide uppercase">
                            Documents Collaborateur
                        </h3>
                        <p id="doc_modal_role" class="text-[12px] text-sky-600 dark:text-sky-400 font-bold">Pompiste</p>
                    </div>
                </div>
                <button type="button" onclick="toggleModalDocuments(false)" class="w-8 h-8 rounded-xl text-slate-400 hover:text-slate-950 dark:hover:text-white flex items-center justify-center transition">
                    <i data-lucide="x" class="w-5 h-5"></i>
                </button>
            </div>

            <div class="p-6 space-y-3">
                <span class="text-[11px] font-black uppercase tracking-wider text-slate-400 block mb-1">Documents Officiels (Format A4 & Cachet Station)</span>

                <!-- 1. Attestation de Travail -->
                <a id="link_doc_travail" href="#" target="_blank" 
                   class="flex items-center justify-between p-3.5 rounded-2xl bg-slate-50 dark:bg-white/5 hover:bg-sky-500/10 hover:border-sky-500/30 border border-slate-200 dark:border-white/10 transition group">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-xl bg-sky-500/15 text-sky-500 flex items-center justify-center">
                            <i data-lucide="briefcase" class="w-4 h-4"></i>
                        </div>
                        <div>
                            <h4 class="font-extrabold text-slate-900 dark:text-white text-[13px] group-hover:text-sky-500 transition-colors">Attestation de Travail</h4>
                            <p class="text-[11px] text-slate-500">Pour visa, banque, démarches administratives</p>
                        </div>
                    </div>
                    <i data-lucide="printer" class="w-4 h-4 text-slate-400 group-hover:text-sky-500 transition-colors"></i>
                </a>

                <!-- 2. Attestation de Salaire -->
                <a id="link_doc_salaire" href="#" target="_blank" 
                   class="flex items-center justify-between p-3.5 rounded-2xl bg-slate-50 dark:bg-white/5 hover:bg-emerald-500/10 hover:border-emerald-500/30 border border-slate-200 dark:border-white/10 transition group">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-xl bg-emerald-500/15 text-emerald-500 flex items-center justify-center">
                            <i data-lucide="badge-percent" class="w-4 h-4"></i>
                        </div>
                        <div>
                            <h4 class="font-extrabold text-slate-900 dark:text-white text-[13px] group-hover:text-emerald-500 transition-colors">Attestation de Salaire</h4>
                            <p class="text-[11px] text-slate-500">Justificatif de rémunération brute & nette</p>
                        </div>
                    </div>
                    <i data-lucide="printer" class="w-4 h-4 text-slate-400 group-hover:text-emerald-500 transition-colors"></i>
                </a>

                <!-- 3. Titre de Congé -->
                <a id="link_doc_conge" href="#" target="_blank" 
                   class="flex items-center justify-between p-3.5 rounded-2xl bg-slate-50 dark:bg-white/5 hover:bg-amber-500/10 hover:border-amber-500/30 border border-slate-200 dark:border-white/10 transition group">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-xl bg-amber-500/15 text-amber-500 flex items-center justify-center">
                            <i data-lucide="palmtree" class="w-4 h-4"></i>
                        </div>
                        <div>
                            <h4 class="font-extrabold text-slate-900 dark:text-white text-[13px] group-hover:text-amber-500 transition-colors">Titre / Attestation de Congé</h4>
                            <p class="text-[11px] text-slate-500">Autorisation de départ et reprise de service</p>
                        </div>
                    </div>
                    <i data-lucide="printer" class="w-4 h-4 text-slate-400 group-hover:text-amber-500 transition-colors"></i>
                </a>

                <!-- 4. Contrat CDI -->
                <a id="link_doc_contrat" href="#" target="_blank" 
                   class="flex items-center justify-between p-3.5 rounded-2xl bg-slate-50 dark:bg-white/5 hover:bg-purple-500/10 hover:border-purple-500/30 border border-slate-200 dark:border-white/10 transition group">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-xl bg-purple-500/15 text-purple-500 flex items-center justify-center">
                            <i data-lucide="file-signature" class="w-4 h-4"></i>
                        </div>
                        <div>
                            <h4 class="font-extrabold text-slate-900 dark:text-white text-[13px] group-hover:text-purple-500 transition-colors">Contrat de Travail (CDI)</h4>
                            <p class="text-[11px] text-slate-500">Modèle officiel station-service avec clauses</p>
                        </div>
                    </div>
                    <i data-lucide="printer" class="w-4 h-4 text-slate-400 group-hover:text-purple-500 transition-colors"></i>
                </a>
            </div>

            <div class="px-6 py-4 bg-slate-50/80 dark:bg-[#060D15]/80 border-t border-slate-200 dark:border-white/10 flex justify-end">
                <button type="button" onclick="toggleModalDocuments(false)" class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 text-slate-800 dark:text-slate-200 font-bold text-[13px] transition cursor-pointer">Fermer</button>
            </div>
        </div>
    </div>

    <!-- SCRIPTS JAVASCRIPT -->
    <script>
        const abrevsRoles = {{
            'admin': 'adm',
            'comptable': 'cpt',
            'employe': 'emp'
        }};

        function genererUsernameModal(mode) {{
            const nomInput = document.getElementById(mode === 'add' ? 'add_modal_nom' : 'edit_modal_nom');
            const roleSelect = document.getElementById(mode === 'add' ? 'add_modal_role' : 'edit_modal_role');
            const userInput = document.getElementById(mode === 'add' ? 'add_modal_username' : 'edit_modal_username');

            if (!nomInput || !userInput) return;
            const nom = nomInput.value.trim();
            if (!nom) return;

            const base = nom.split(' ')[0]
                .toLowerCase()
                .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
                .replace(/[^a-z0-9]/g, '');

            const codeRole = abrevsRoles[roleSelect.value] || 'usr';
            userInput.value = `${{base}}_${{codeRole}}`;
        }}

        function toggleUserMenu(event, menuId) {{
            event.stopPropagation();
            const targetMenu = document.getElementById(menuId);
            if (!targetMenu) return;
            const isHidden = targetMenu.classList.contains('hidden');
            
            fermerTousLesMenusUsers();

            if (isHidden) {{
                targetMenu.classList.remove('hidden');
                const card = targetMenu.closest('.user-card') || targetMenu.closest('tr');
                if (card) card.classList.add('z-50');
                if (typeof lucide !== 'undefined') lucide.createIcons();
            }}
        }}

        function fermerTousLesMenusUsers() {{
            document.querySelectorAll('.user-dropdown-menu').forEach(menu => {{
                menu.classList.add('hidden');
            }});
            document.querySelectorAll('.user-card, tr').forEach(el => {{
                el.classList.remove('z-50');
            }});
        }}

        document.addEventListener('click', () => {{
            fermerTousLesMenusUsers();
        }});

        function toggleModalAddUser(show) {{
            document.getElementById('modalAddUser').classList.toggle('hidden', !show);
            if (show) genererUsernameModal('add');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function toggleModalEditUser(show) {{
            document.getElementById('modalEditUser').classList.toggle('hidden', !show);
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function toggleModalDocuments(show) {{
            document.getElementById('modalDocumentsRH').classList.toggle('hidden', !show);
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function afficherModalModifierUser(btn) {{
            const data = JSON.parse(btn.getAttribute('data-user'));
            document.getElementById('edit_modal_user_id').value = data.id;
            document.getElementById('edit_modal_nom').value = data.nom_complet;
            document.getElementById('edit_modal_username').value = data.username;
            document.getElementById('edit_modal_role').value = data.role;
            document.getElementById('edit_modal_statut').value = data.statut;
            document.getElementById('edit_modal_cin').value = data.cin;
            document.getElementById('edit_modal_cnss').value = data.cnss;
            document.getElementById('edit_modal_tel').value = data.telephone;
            document.getElementById('edit_modal_date_emb').value = data.date_embauche;
            document.getElementById('edit_modal_salaire').value = data.salaire_base;

            toggleModalEditUser(true);
        }}

        function afficherDocsRH(userId, userName, userRole) {{
            document.getElementById('doc_modal_nom').innerText = userName;
            document.getElementById('doc_modal_role').innerText = userRole;

            document.getElementById('link_doc_travail').href = `/utilisateurs/${{userId}}/attestation/travail`;
            document.getElementById('link_doc_salaire').href = `/utilisateurs/${{userId}}/attestation/salaire`;
            document.getElementById('link_doc_conge').href = `/utilisateurs/${{userId}}/attestation/conge`;
            document.getElementById('link_doc_contrat').href = `/utilisateurs/${{userId}}/attestation/contrat`;

            toggleModalDocuments(true);
        }}

        function declencherSuppressionUser(userId) {{
            if (confirm('Attention : Confirmer la suppression de ce collaborateur ?')) {{
                const f = document.getElementById('formSupprimerUser');
                f.action = `/utilisateurs/supprimer/${{userId}}`;
                f.submit();
            }}
        }}

        function basculerVueUsers(vue) {{
            const gridView = document.getElementById('usersGridView');
            const listView = document.getElementById('usersListView');
            const btnGrid = document.getElementById('btnViewGridUsers');
            const btnList = document.getElementById('btnViewListUsers');

            if (vue === 'grid') {{
                gridView.classList.remove('hidden');
                listView.classList.add('hidden');
                btnGrid.className = "w-8 h-8 rounded-lg flex items-center justify-center transition bg-blue-600 text-white shadow-xs";
                btnList.className = "w-8 h-8 rounded-lg flex items-center justify-center transition text-slate-500 hover:text-slate-900 dark:hover:text-white";
                localStorage.setItem('petrolaz_user_view', 'grid');
            }} else {{
                gridView.classList.add('hidden');
                listView.classList.remove('hidden');
                btnList.className = "w-8 h-8 rounded-lg flex items-center justify-center transition bg-blue-600 text-white shadow-xs";
                btnGrid.className = "w-8 h-8 rounded-lg flex items-center justify-center transition text-slate-500 hover:text-slate-900 dark:hover:text-white";
                localStorage.setItem('petrolaz_user_view', 'list');
            }}
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function filtrerUsersDirect() {{
            const q = (document.getElementById('liveSearchUsers').value || '').toLowerCase().trim();
            const roleFilter = document.getElementById('filterRoleSelect').value;
            const cards = document.querySelectorAll('.user-card');
            const tableRows = document.querySelectorAll('.user-table-row');
            let visibleCount = 0;

            cards.forEach(card => {{
                const blob = card.getAttribute('data-search') || '';
                const role = card.getAttribute('data-role') || '';
                const matchQ = !q || blob.includes(q);
                const matchRole = (roleFilter === 'tous') || (role === roleFilter);

                const match = matchQ && matchRole;
                card.style.display = match ? 'flex' : 'none';
                if (match) visibleCount++;
            }});

            tableRows.forEach(row => {{
                const blob = row.getAttribute('data-search') || '';
                const role = row.getAttribute('data-role') || '';
                const matchQ = !q || blob.includes(q);
                const matchRole = (roleFilter === 'tous') || (role === roleFilter);

                const match = matchQ && matchRole;
                row.style.display = match ? '' : 'none';
            }});

            document.getElementById('countDisplayedUsers').innerText = visibleCount;
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            const savedView = localStorage.getItem('petrolaz_user_view') || 'grid';
            basculerVueUsers(savedView);
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }});
    </script>
    """
    return HTMLResponse(layout(content, "utilisateurs", request=request))

# ==========================================================
# 2. ROUTES POST : AJOUT, MODIF & SUPPRESSION
# ==========================================================
@router.post("/ajouter")
async def action_ajouter_utilisateur(
    nom_complet: str = Form(...), 
    username: str = Form(...), 
    password: str = Form(...), 
    role: str = Form(...),
    cin: str = Form(""),
    cnss: str = Form(""),
    telephone: str = Form(""),
    date_embauche: str = Form(""),
    salaire_base: float = Form(0.0),
    adresse: str = Form(""),
    statut: str = Form("ACTIF")
):
    ajouter_utilisateur(
        username=username.strip(),
        nom_complet=nom_complet.strip().upper(),
        password=password.strip(),
        role=role.strip(),
        cin=cin.strip().upper(),
        cnss=cnss.strip(),
        telephone=telephone.strip(),
        date_embauche=date_embauche.strip(),
        salaire_base=salaire_base,
        adresse=adresse.strip(),
        statut=statut.strip()
    )
    return RedirectResponse(url="/utilisateurs", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/modifier")
async def action_modifier_utilisateur(
    user_id: int = Form(...),
    nom_complet: str = Form(...),
    username: str = Form(...),
    role: str = Form(...),
    password: str = Form(None),
    cin: str = Form(""),
    cnss: str = Form(""),
    telephone: str = Form(""),
    date_embauche: str = Form(""),
    salaire_base: float = Form(0.0),
    adresse: str = Form(""),
    statut: str = Form("ACTIF")
):
    modifier_utilisateur(
        user_id=user_id,
        nom_complet=nom_complet.strip().upper(),
        username=username.strip(),
        role=role.strip(),
        password=password.strip() if password else None,
        cin=cin.strip().upper(),
        cnss=cnss.strip(),
        telephone=telephone.strip(),
        date_embauche=date_embauche.strip(),
        salaire_base=salaire_base,
        adresse=adresse.strip(),
        statut=statut.strip()
    )
    return RedirectResponse(url="/utilisateurs", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/supprimer/{user_id}")
async def action_supprimer_utilisateur(user_id: int):
    supprimer_utilisateur(user_id)
    return RedirectResponse(url="/utilisateurs", status_code=status.HTTP_303_SEE_OTHER)

# ==========================================================
# 3. ROUTES VERS LES ATTESTATIONS SÉPARÉES
# ==========================================================
@router.get("/{user_id}/attestation/travail", response_class=HTMLResponse)
async def route_attestation_travail(user_id: int):
    u = get_utilisateur_by_id(user_id)
    if not u:
        return HTMLResponse("Employé introuvable", status_code=404)
    return HTMLResponse(generer_attestation_travail(u))

@router.get("/{user_id}/attestation/salaire", response_class=HTMLResponse)
async def route_attestation_salaire(user_id: int):
    u = get_utilisateur_by_id(user_id)
    if not u:
        return HTMLResponse("Employé introuvable", status_code=404)
    return HTMLResponse(generer_attestation_salaire(u))

@router.get("/{user_id}/attestation/conge", response_class=HTMLResponse)
async def route_attestation_conge(user_id: int):
    u = get_utilisateur_by_id(user_id)
    if not u:
        return HTMLResponse("Employé introuvable", status_code=404)
    return HTMLResponse(generer_attestation_conge(u))

@router.get("/{user_id}/attestation/contrat", response_class=HTMLResponse)
async def route_contrat_travail(user_id: int):
    u = get_utilisateur_by_id(user_id)
    if not u:
        return HTMLResponse("Employé introuvable", status_code=404)
    return HTMLResponse(generer_contrat_travail(u))