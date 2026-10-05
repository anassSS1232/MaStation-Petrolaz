import os
import re
import json
import time
import html
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Request, Form, UploadFile, File, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse

import database
from database import get_db_connection
from ui_utils import layout

router = APIRouter()

UPLOAD_DIR = Path("static/uploads/factures")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/webp"}

def s_assurer_colonne_lignes_json():
    """Vérifie et ajoute la colonne lignes_json si absente."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE achats_fournisseurs ADD COLUMN lignes_json TEXT DEFAULT '[]'")
        conn.commit()
        conn.close()
    except Exception:
        pass

s_assurer_colonne_lignes_json()

def format_mad(valeur):
    """Formatage propre en MAD."""
    try:
        val = float(valeur or 0.0)
        return f"{val:,.2f}".replace(",", " ").replace(".", ",") + " MAD"
    except Exception:
        return "0,00 MAD"

def formater_date_fr(date_str: str) -> str:
    if not date_str:
        return "—"
    try:
        if "-" in date_str:
            p = date_str.split("-")
            if len(p) == 3:
                return f"{p[2]}/{p[1]}/{p[0]}"
    except Exception:
        pass
    return date_str

@router.get("/achats", response_class=HTMLResponse)
async def page_achats(
    request: Request,
    date_debut: str = Query(""),
    date_fin: str = Query(""),
    fournisseur_id: int = Query(0),
    min_m: float = Query(0.0),
    max_m: float = Query(0.0)
):
    fournisseurs = database.get_fournisseurs()
    achats = database.get_achats_filtres(
        date_debut=date_debut if date_debut else None,
        date_fin=date_fin if date_fin else None,
        fournisseur_id=int(fournisseur_id) if fournisseur_id else None,
        min_montant=float(min_m) if min_m else None,
        max_montant=float(max_m) if max_m else None
    )

    total_ttc = sum(float(a.get("montant_total") or 0.0) for a in achats)
    total_ht = sum(float(a.get("montant_ht") or 0.0) for a in achats)
    total_tva = sum(float(a.get("montant_tva") or 0.0) for a in achats)
    nb_achats = len(achats)

    prochain_num = database.generer_prochain_numero_facture()
    today_iso = datetime.now().strftime("%Y-%m-%d")

    # Sélection automatique de OKAY ENERGY par défaut
    okay_energy_id = None
    for f in fournisseurs:
        if "OKAY" in f.get("nom", "").upper():
            okay_energy_id = f["id"]
            break

    # Options Fournisseurs
    fournisseurs_options_filter = '<option value="0"' + (' selected' if fournisseur_id == 0 else '') + '>Tous les fournisseurs</option>'
    fournisseurs_options_modal = ''

    for f in fournisseurs:
        f_nom_safe = html.escape(f.get("nom", ""))
        f_code_safe = html.escape(f.get("code", "FRN"))
        
        sel_filter = " selected" if fournisseur_id == f["id"] else ""
        fournisseurs_options_filter += f'<option value="{f["id"]}"{sel_filter}>{f_nom_safe}</option>'

        is_default = (f["id"] == okay_energy_id) or (okay_energy_id is None and f == fournisseurs[0])
        sel_modal = " selected" if is_default else ""
        fournisseurs_options_modal += f'<option value="{f["id"]}"{sel_modal}>{f_nom_safe} ({f_code_safe})</option>'

    # Tableau des achats
    rows_html = ""
    for a in achats:
        a_id = a.get("id")
        raw_date = a.get("date") or ""
        date_affichee = formater_date_fr(raw_date)
        fnom = a.get("fournisseur_nom") or "OKAY ENERGY"
        fcode = a.get("fournisseur_code") or "OKF"
        num_facture = a.get("numero_facture") or "FAC-DIRECT"
        fichier_path = a.get("fichier_facture") or ""
        montant_ht = float(a.get("montant_ht") or 0.0)
        montant_tva = float(a.get("montant_tva") or 0.0)
        montant_ttc = float(a.get("montant_total") or 0.0)
        taux_tva = float(a.get("taux_tva") or 10.0)
        notes = a.get("observations") or ""
        produit_principal = a.get("produit") or "Diesel"

        lignes_json_raw = a.get("lignes_json") or "[]"
        try:
            lignes_achetees = json.loads(lignes_json_raw)
        except Exception:
            lignes_achetees = []

        if not lignes_achetees:
            lignes_achetees = [{
                "produit": produit_principal,
                "citerne": "Citerne 1",
                "qte": float(a.get("volume_litres") or 0.0),
                "pu_ht": float(a.get("prix_unitaire") or 0.0),
                "montant_ht": montant_ht
            }]

        achat_json_data = {
            "id": a_id,
            "numero_facture": num_facture,
            "date": raw_date,
            "fournisseur_id": a.get("fournisseur_id"),
            "fournisseur_nom": fnom,
            "fournisseur_code": fcode,
            "montant_ht": montant_ht,
            "taux_tva": taux_tva,
            "montant_tva": montant_tva,
            "montant_total": montant_ttc,
            "observations": notes,
            "fichier_facture": fichier_path,
            "lignes": lignes_achetees
        }
        achat_json_escaped = html.escape(json.dumps(achat_json_data), quote=True)

        if fichier_path:
            is_pdf = fichier_path.lower().endswith(".pdf")
            icon_file = "file-text" if is_pdf else "image"
            badge_file = (
                f'<a href="{fichier_path}" target="_blank" onclick="event.stopPropagation()" '
                f'class="inline-flex items-center gap-1 text-[11px] text-sky-400 font-bold hover:underline mt-0.5">'
                f'<i data-lucide="{icon_file}" class="w-3 h-3"></i> Facture</a>'
            )
        else:
            badge_file = """
            <span class="inline-flex items-center gap-1 text-[11px] text-slate-400 dark:text-slate-500 font-medium mt-0.5">
                <i data-lucide="file" class="w-3 h-3"></i> Facture
            </span>
            """

        search_blob = f"{num_facture} {fnom} {fcode} {notes}".lower()

        rows_html += f"""
        <tr onclick="afficherDetailAchat({achat_json_escaped})" 
            class="achat-row cursor-pointer border-b border-slate-100 dark:border-[#183042]/50 hover:bg-sky-50/50 dark:hover:bg-[#132738]/50 transition text-sm group"
            data-search="{html.escape(search_blob, quote=True)}"
            data-date="{raw_date}"
            data-fournisseur="{a.get('fournisseur_id', 0)}"
            data-ttc="{montant_ttc}">
            <td class="py-3 px-4 font-mono font-bold text-slate-800 dark:text-slate-100 text-[13px] whitespace-nowrap">
                {date_affichee}
            </td>
            <td class="py-3 px-4 whitespace-nowrap">
                <div class="font-extrabold text-[13.5px] text-sky-600 dark:text-sky-400 group-hover:underline font-mono">{html.escape(num_facture)}</div>
                {badge_file}
            </td>
            <td class="py-3 px-4 whitespace-nowrap">
                <span class="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-[#132738] border border-slate-200/80 dark:border-[#224563] text-slate-900 dark:text-white text-xs font-bold">
                    {html.escape(fnom)}
                </span>
            </td>
            <td class="py-3 px-4 text-right font-mono font-black text-amber-600 dark:text-[#E5A842] text-[14.5px] whitespace-nowrap">
                {montant_ttc:,.2f} <span class="text-[11px] font-sans font-semibold text-slate-400">MAD</span>
            </td>
            <td class="py-3 px-4 text-right whitespace-nowrap" onclick="event.stopPropagation()">
                <div class="relative inline-block text-left actions-dropdown-container">
                    <button type="button" 
                            onclick="toggleMenuAchat(event, 'menu-achat-{a_id}')" 
                            class="w-8 h-8 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-[#132738] dark:hover:bg-[#18354c] text-slate-700 dark:text-slate-200 flex items-center justify-center transition shadow-2xs cursor-pointer"
                            title="Actions">
                        <i data-lucide="more-vertical" class="w-4 h-4"></i>
                    </button>

                    <div id="menu-achat-{a_id}" 
                         class="dropdown-menu-achat hidden absolute right-0 mt-1.5 w-44 rounded-2xl bg-white dark:bg-[#0E1B26] border border-slate-200/90 dark:border-[#183042] shadow-2xl py-1.5 z-50 text-left">
                        <button type="button" 
                                onclick="afficherDetailAchat({achat_json_escaped}); fermerTousLesMenusAchats();" 
                                class="w-full px-3.5 py-2 text-left text-xs font-bold text-slate-700 dark:text-slate-200 hover:bg-sky-50 dark:hover:bg-[#132738] flex items-center gap-2.5 transition cursor-pointer">
                            <i data-lucide="eye" class="w-4 h-4 text-sky-500"></i>
                            <span>Détails</span>
                        </button>
                        <button type="button" 
                                onclick="ouvrirModalModification({achat_json_escaped}); fermerTousLesMenusAchats();" 
                                class="w-full px-3.5 py-2 text-left text-xs font-bold text-amber-600 dark:text-[#E5A842] hover:bg-amber-500/10 flex items-center gap-2.5 transition cursor-pointer">
                            <i data-lucide="edit-3" class="w-4 h-4 text-[#E5A842]"></i>
                            <span>Modifier</span>
                        </button>
                        <div class="my-1 border-t border-slate-100 dark:border-[#183042]/60"></div>
                        <button type="button" 
                                onclick="confirmerSuppression({a_id}, '{html.escape(num_facture)}'); fermerTousLesMenusAchats();" 
                                class="w-full px-3.5 py-2 text-left text-xs font-bold text-rose-500 hover:bg-rose-500/10 flex items-center gap-2.5 transition cursor-pointer">
                            <i data-lucide="trash-2" class="w-4 h-4 text-rose-500"></i>
                            <span>Supprimer</span>
                        </button>
                    </div>
                </div>
            </td>
        </tr>
        """

    if not rows_html:
        rows_html = '<tr><td colspan="5" class="text-center py-12 text-slate-400 text-xs font-medium">Aucun achat enregistré.</td></tr>'

    # Construction du corps HTML
    html_markup = f"""
    <style>
        #achats-table-body tr:nth-last-child(-n+2) .dropdown-menu-achat {{
            bottom: 100%;
            top: auto;
            margin-bottom: 0.4rem;
            margin-top: 0;
        }}
    </style>

    <div class="max-w-7xl mx-auto space-y-4 animate-in fade-in duration-150">

        <!-- 1. EN-TÊTE -->
        <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white dark:bg-[#0E1B26] p-4 rounded-2xl border border-slate-200/90 dark:border-[#183042] shadow-xs">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-amber-500/10 text-[#E5A842] flex items-center justify-center font-bold">
                    <i data-lucide="shopping-cart" class="w-5 h-5"></i>
                </div>
                <div>
                    <h1 class="font-black text-slate-900 dark:text-white text-base uppercase tracking-wider">Gestion des Achats</h1>
                    <p class="text-xs text-slate-600 dark:text-slate-300 font-semibold">Affichage : <strong id="live-count-achats" class="text-sky-500 font-mono text-sm">{nb_achats}</strong> achat(s)</p>
                </div>
            </div>

            <div class="flex items-center gap-3 font-mono text-xs">
                <div class="bg-slate-50 dark:bg-[#070E15] px-3.5 py-2 rounded-xl border border-slate-200 dark:border-[#183042]">
                    <span class="text-[11px] text-slate-500 dark:text-slate-400 uppercase block font-sans font-bold">Total HT</span>
                    <strong id="live-total-ht" class="text-slate-900 dark:text-slate-100 text-sm font-black">{format_mad(total_ht)}</strong>
                </div>
                <div class="bg-slate-50 dark:bg-[#070E15] px-3.5 py-2 rounded-xl border border-slate-200 dark:border-[#183042]">
                    <span class="text-[11px] text-slate-500 dark:text-slate-400 uppercase block font-sans font-bold">Total TTC</span>
                    <strong id="live-total-ttc" class="text-[#E5A842] text-sm font-black">{format_mad(total_ttc)}</strong>
                </div>

                <button onclick="ouvrirModalNouvelAchat()" class="btn-primary flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl cursor-pointer bg-[#E5A842] hover:bg-[#d69632] text-slate-950 font-black text-sm shadow-md transition">
                    <i data-lucide="plus" class="w-4 h-4 stroke-[3]"></i>
                    <span>Nouvel Achat</span>
                </button>
            </div>
        </div>

        <!-- 2. FILTRES -->
        <div class="bg-white dark:bg-[#0E1B26] p-3 rounded-2xl border border-slate-200/90 dark:border-[#183042] shadow-xs space-y-2.5">
            <div class="grid grid-cols-1 sm:grid-cols-12 gap-2.5 items-center">
                <div class="sm:col-span-4 relative">
                    <i data-lucide="search" class="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none"></i>
                    <input type="text" id="live-search-q" oninput="filtrerAchatsEnDirect()" placeholder="Rechercher (N° Facture, Fournisseur, Notes)..." 
                           class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] focus:border-[#E5A842] rounded-xl pl-10 pr-3.5 py-2 text-xs sm:text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 outline-none transition">
                </div>

                <div class="sm:col-span-3 flex items-center gap-2 bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-1.5">
                    <span class="text-xs font-bold uppercase text-slate-500 dark:text-slate-400 shrink-0">Du:</span>
                    <input type="date" id="live-date-debut" value="{date_debut}" oninput="filtrerAchatsEnDirect()" onchange="filtrerAchatsEnDirect()"
                           class="w-full bg-transparent border-0 text-xs sm:text-sm font-bold font-mono text-slate-900 dark:text-white outline-none cursor-pointer">
                </div>

                <div class="sm:col-span-3 flex items-center gap-2 bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-1.5">
                    <span class="text-xs font-bold uppercase text-slate-500 dark:text-slate-400 shrink-0">Au:</span>
                    <input type="date" id="live-date-fin" value="{date_fin}" oninput="filtrerAchatsEnDirect()" onchange="filtrerAchatsEnDirect()"
                           class="w-full bg-transparent border-0 text-xs sm:text-sm font-bold font-mono text-slate-900 dark:text-white outline-none cursor-pointer">
                </div>

                <div class="sm:col-span-2 flex items-center gap-2">
                    <select id="live-filter-fournisseur" onchange="filtrerAchatsEnDirect()" class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-2.5 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none">
                        {fournisseurs_options_filter}
                    </select>
                </div>
            </div>
        </div>

        <!-- 3. TABLEAU -->
        <div class="bg-white dark:bg-[#0E1B26] rounded-2xl border border-slate-200/90 dark:border-[#183042] shadow-xs overflow-hidden flex flex-col">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse min-w-[750px]">
                    <thead class="bg-slate-50 dark:bg-[#070E15] border-b border-slate-200 dark:border-[#183042] text-xs font-black uppercase text-slate-700 dark:text-slate-300">
                        <tr>
                            <th class="py-3 px-4">Date</th>
                            <th class="py-3 px-4">N° Facture</th>
                            <th class="py-3 px-4">Fournisseur</th>
                            <th class="py-3 px-4 text-right">Montant TTC</th>
                            <th class="py-3 px-4 text-right w-20">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="achats-table-body" class="divide-y divide-slate-100 dark:divide-[#183042]/50">
                        {rows_html}
                    </tbody>
                </table>
            </div>
            <div id="achats-empty-state" class="hidden text-center py-12 text-slate-400 text-xs font-medium italic">
                Aucun achat ne correspond aux filtres sélectionnés.
            </div>
        </div>

    </div>

    <!-- MODAL FORMULAIRE ACHAT -->
    <div id="modal-form-achat" class="fixed inset-0 bg-slate-900/75 backdrop-blur-sm z-50 hidden flex items-center justify-center p-2 sm:p-4 overflow-y-auto">
        <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#1E3A52] rounded-3xl max-w-4xl w-full shadow-2xl overflow-hidden flex flex-col my-auto max-h-[95vh] transition-all duration-200">
            
            <div class="flex items-center justify-between p-4 border-b border-slate-200 dark:border-[#183042] bg-slate-50 dark:bg-[#070E15]">
                <div class="flex items-center gap-2.5">
                    <div class="w-9 h-9 rounded-xl bg-amber-500/10 text-[#E5A842] flex items-center justify-center font-bold">
                        <i data-lucide="plus-circle" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <h2 id="modal-form-title" class="text-sm font-black text-slate-900 dark:text-white uppercase tracking-wider">Nouvel Achat</h2>
                        <p class="text-[11px] text-slate-500 dark:text-slate-400 font-medium">Facture d'achat et approvisionnement des stocks</p>
                    </div>
                </div>
                <button type="button" onclick="fermerModalAchat()" class="w-8 h-8 rounded-xl bg-slate-100 dark:bg-white/10 hover:bg-slate-200 dark:hover:bg-white/20 text-slate-600 dark:text-slate-200 flex items-center justify-center transition cursor-pointer">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            </div>

            <form id="form-achat" method="POST" action="/achats/enregistrer" enctype="multipart/form-data" class="p-4 sm:p-5 overflow-y-auto space-y-4 flex-1">
                <input type="hidden" name="achat_id" id="fa-id" value="">
                <input type="hidden" name="lignes_json" id="fa-hidden-lignes" value="[]">

                <div class="bg-slate-50 dark:bg-[#070E15] p-4 rounded-2xl border border-slate-200 dark:border-[#1E3A52] space-y-3">
                    <span class="font-black uppercase tracking-wider text-xs text-slate-700 dark:text-slate-200 flex items-center gap-2">
                        <i data-lucide="clipboard-list" class="w-4 h-4 text-sky-500"></i>
                        <span>Informations Générales</span>
                    </span>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">Fournisseur *</label>
                            <select name="fournisseur_id" id="fa-fournisseur" required class="w-full bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-[#E5A842]">
                                {fournisseurs_options_modal}
                            </select>
                        </div>

                        <div>
                            <label class="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">Numéro de Facture</label>
                            <input type="text" name="numero_facture" id="fa-numero" placeholder="Ex: OKFA-90021986" required class="w-full bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-mono font-bold text-slate-900 dark:text-white outline-none focus:border-[#E5A842]">
                        </div>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">Date d'Achat *</label>
                            <input type="date" name="date_achat" id="fa-date" value="{today_iso}" required class="w-full bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-mono font-bold text-slate-900 dark:text-white outline-none focus:border-[#E5A842]">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">Facture (PDF / Image)</label>
                            <input type="file" name="fichier" accept=".pdf,.png,.jpg,.jpeg,.webp" class="w-full text-xs text-slate-500 dark:text-slate-300 file:mr-2 file:py-1 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-[#E5A842]/15 file:text-[#E5A842] hover:file:bg-[#E5A842]/25">
                        </div>
                    </div>
                </div>

                <div class="bg-slate-50 dark:bg-[#070E15] p-4 rounded-2xl border border-slate-200 dark:border-[#1E3A52] space-y-3">
                    <div class="flex items-center justify-between border-b border-slate-200 dark:border-[#183042] pb-2">
                        <span class="font-black uppercase tracking-wider text-xs text-slate-700 dark:text-slate-200 flex items-center gap-2">
                            <i data-lucide="package" class="w-4 h-4 text-[#E5A842]"></i>
                            <span>Produits Achetés</span>
                        </span>
                        
                        <button type="button" onclick="ajouterLigneAchat()" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-200/80 hover:bg-slate-300 dark:bg-[#132738] dark:hover:bg-[#1c3850] text-slate-800 dark:text-white text-xs font-bold transition cursor-pointer">
                            <i data-lucide="plus" class="w-3.5 h-3.5"></i>
                            <span>Ajouter une ligne</span>
                        </button>
                    </div>

                    <div class="border border-slate-200 dark:border-[#1E3A52] rounded-xl overflow-hidden">
                        <table class="w-full text-left border-collapse">
                            <thead class="bg-slate-100 dark:bg-[#0E1B26] border-b border-slate-200 dark:border-[#1E3A52] text-[11px] font-bold uppercase text-slate-600 dark:text-slate-300">
                                <tr>
                                    <th class="p-2.5">Produit *</th>
                                    <th class="p-2.5 w-36">Citerne / Stock</th>
                                    <th class="p-2.5 w-28 text-center">Quantité</th>
                                    <th class="p-2.5 w-32 text-right">Prix Unitaire HT</th>
                                    <th class="p-2.5 w-36 text-right">Montant HT</th>
                                    <th class="p-2.5 w-12 text-center"></th>
                                </tr>
                            </thead>
                            <tbody id="fa-lignes-body" class="divide-y divide-slate-100 dark:divide-[#183042]">
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="bg-slate-50 dark:bg-[#070E15] p-4 rounded-2xl border border-slate-200 dark:border-[#1E3A52] space-y-3">
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">Montant HT (MAD)</label>
                            <input type="number" step="0.01" id="fa-montant-ht" name="montant_ht" readonly class="w-full bg-slate-200/50 dark:bg-[#0E1B26] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-mono font-bold text-slate-900 dark:text-white">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">Taux TVA (%)</label>
                            <select id="fa-taux-tva" name="taux_tva" onchange="calculerTotauxAchat()" class="w-full bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-[#E5A842]">
                                <option value="10" selected>10% (Carburants)</option>
                                <option value="20">20% (Général)</option>
                                <option value="0">0% (Exonéré)</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">Montant TVA (MAD)</label>
                            <input type="number" step="0.01" id="fa-montant-tva" name="montant_tva" readonly class="w-full bg-slate-200/50 dark:bg-[#0E1B26] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-mono font-bold text-slate-900 dark:text-white">
                        </div>
                    </div>

                    <div class="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/25 flex items-center justify-between">
                        <span class="text-xs font-black uppercase text-amber-900 dark:text-[#E5A842]">Montant Total TTC :</span>
                        <span id="fa-display-ttc" class="font-mono text-xl font-black text-amber-600 dark:text-[#E5A842]">0,00 MAD</span>
                        <input type="hidden" id="fa-hidden-ttc" name="montant_total" value="0.00">
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-bold text-slate-700 dark:text-slate-200 mb-1">Notes / Observations</label>
                    <textarea name="observations" id="fa-notes" rows="2" placeholder="Notes supplémentaires sur cet achat (Ex: N° Bon de livraison, N° Camion)..." class="w-full bg-slate-50 dark:bg-[#070E15] border border-slate-300 dark:border-[#1E3A52] rounded-xl px-3 py-2 text-xs font-medium text-slate-900 dark:text-white outline-none focus:border-[#E5A842]"></textarea>
                </div>

                <div class="pt-3 border-t border-slate-200 dark:border-[#183042] flex items-center justify-end gap-2.5">
                    <button type="button" onclick="fermerModalAchat()" class="px-4 py-2 bg-slate-100 dark:bg-[#132738] hover:bg-slate-200 dark:hover:bg-[#1c3850] text-slate-700 dark:text-slate-200 text-xs font-bold rounded-xl transition cursor-pointer">
                        Annuler
                    </button>
                    <button type="submit" class="px-5 py-2 bg-[#E5A842] hover:bg-[#d69632] text-slate-950 font-black rounded-xl text-xs uppercase tracking-wider shadow-md transition flex items-center gap-1.5 cursor-pointer">
                        <i data-lucide="check" class="w-4 h-4 stroke-[3]"></i>
                        <span id="fa-btn-submit">Enregistrer l'Achat</span>
                    </button>
                </div>
            </form>

        </div>
    </div>

    <!-- MODAL DÉTAILS -->
    <div id="modal-details-achat" class="fixed inset-0 bg-slate-900/75 backdrop-blur-sm z-50 hidden flex items-center justify-center p-3">
        <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-3xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-150">
            
            <div class="flex items-center justify-between p-4 border-b border-slate-200 dark:border-[#183042] bg-slate-50 dark:bg-[#070E15]">
                <div class="flex items-center gap-2.5">
                    <div class="w-9 h-9 rounded-xl bg-sky-500/10 text-sky-500 flex items-center justify-center font-bold">
                        <i data-lucide="eye" class="w-5 h-5"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <h3 id="da-num" class="font-black text-sm text-slate-900 dark:text-white font-mono">Détails de l'Achat</h3>
                            <span class="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-500 text-[10px] font-bold uppercase">Validé</span>
                        </div>
                        <p id="da-date" class="text-xs text-slate-500 dark:text-slate-400 font-mono">Date : --</p>
                    </div>
                </div>
                <button type="button" onclick="fermerModalDetails()" class="w-8 h-8 rounded-xl bg-slate-100 dark:bg-white/10 hover:bg-slate-200 dark:hover:bg-white/20 text-slate-600 dark:text-slate-200 flex items-center justify-center transition">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            </div>

            <div class="p-5 overflow-y-auto space-y-4 text-xs">
                <div class="grid grid-cols-2 gap-3 bg-slate-50 dark:bg-[#070E15] p-3.5 rounded-2xl border border-slate-200 dark:border-[#183042]">
                    <div>
                        <span class="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 block mb-0.5">Fournisseur :</span>
                        <p id="da-fournisseur" class="font-black text-slate-900 dark:text-white text-sm">--</p>
                    </div>
                    <div class="text-right">
                        <span class="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 block mb-0.5">N° Facture :</span>
                        <p id="da-numero-facture" class="font-mono font-bold text-sky-500 text-sm">--</p>
                    </div>
                </div>

                <div>
                    <span class="text-[11px] uppercase font-black tracking-wider text-slate-600 dark:text-slate-300 block mb-2">Produits Achetés</span>
                    <div class="border border-slate-200 dark:border-[#183042] rounded-xl overflow-hidden">
                        <table class="w-full text-left border-collapse">
                            <thead class="bg-slate-100 dark:bg-[#070E15] border-b border-slate-200 dark:border-[#183042] text-[10px] font-bold uppercase text-slate-600 dark:text-slate-300">
                                <tr>
                                    <th class="p-2.5">Produit</th>
                                    <th class="p-2.5 text-center">Quantité</th>
                                    <th class="p-2.5 text-right">Prix Unitaire</th>
                                    <th class="p-2.5 text-right">Montant</th>
                                    <th class="p-2.5">Citerne</th>
                                </tr>
                            </thead>
                            <tbody id="da-lignes-body" class="divide-y divide-slate-100 dark:divide-[#183042]">
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="flex justify-end pt-2">
                    <div class="w-72 space-y-1.5 bg-slate-50 dark:bg-[#070E15] p-3 rounded-2xl border border-slate-200 dark:border-[#183042]">
                        <div class="flex justify-between items-center text-xs">
                            <span class="text-slate-600 dark:text-slate-300 font-semibold">Montant HT :</span>
                            <span id="da-ht" class="font-mono font-bold text-slate-900 dark:text-white">0,00 MAD</span>
                        </div>
                        <div class="flex justify-between items-center text-xs">
                            <span id="da-tva-label" class="text-slate-600 dark:text-slate-300 font-semibold">TVA (10%) :</span>
                            <span id="da-tva" class="font-mono font-bold text-amber-500">0,00 MAD</span>
                        </div>
                        <div class="border-t border-slate-200 dark:border-[#183042] pt-1.5 flex justify-between items-center">
                            <span class="font-black text-slate-900 dark:text-white text-xs uppercase">Montant TTC :</span>
                            <span id="da-ttc" class="font-mono font-black text-base text-[#E5A842]">0,00 MAD</span>
                        </div>
                    </div>
                </div>

                <div id="da-piece-container" class="p-3 rounded-xl bg-slate-50 dark:bg-[#070E15] border border-slate-200 dark:border-[#183042] hidden">
                    <span class="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 block mb-1">Pièce Jointe :</span>
                    <div id="da-piece-content"></div>
                </div>

                <div id="da-notes-container" class="p-3 rounded-xl bg-slate-50 dark:bg-[#070E15] border border-slate-200 dark:border-[#183042] hidden">
                    <span class="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 block mb-0.5">Notes :</span>
                    <p id="da-notes" class="text-xs text-slate-700 dark:text-slate-200 italic"></p>
                </div>
            </div>

            <div class="p-3.5 border-t border-slate-200 dark:border-[#183042] bg-slate-50 dark:bg-[#070E15] flex items-center justify-end">
                <button type="button" onclick="fermerModalDetails()" class="px-5 py-2 bg-slate-200 dark:bg-[#132738] hover:bg-slate-300 dark:hover:bg-[#1c3850] text-slate-800 dark:text-white font-bold rounded-xl text-xs transition cursor-pointer">
                    Fermer
                </button>
            </div>

        </div>
    </div>
    """

    # Bloc JS non f-string : aucune erreur de syntaxe possible
    js_script = """
    <script>
        let lignesAchat = [];

        const LISTE_PRODUITS = [
            "Diesel",
            "Essence",
            "10W40",
            "15W40 CF4",
            "SAE 50",
            "Lavage",
            "Autre"
        ];

        const LISTE_CITERNES = [
            "Citerne 1",
            "Citerne 2",
            "Citerne 3",
            "Stock Lubrifiants",
            "Autre"
        ];

        function toggleMenuAchat(event, menuId) {
            event.stopPropagation();
            const targetMenu = document.getElementById(menuId);
            if (!targetMenu) return;

            const isHidden = targetMenu.classList.contains('hidden');
            fermerTousLesMenusAchats();

            if (isHidden) {
                targetMenu.classList.remove('hidden');
            }
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }

        function fermerTousLesMenusAchats() {
            document.querySelectorAll('.dropdown-menu-achat').forEach(menu => {
                menu.classList.add('hidden');
            });
        }

        document.addEventListener('click', function(e) {
            if (!e.target.closest('.actions-dropdown-container')) {
                fermerTousLesMenusAchats();
            }
        });

        function filtrerAchatsEnDirect() {
            fermerTousLesMenusAchats();
            const q = (document.getElementById('live-search-q').value || '').toLowerCase().trim();
            const dDebut = document.getElementById('live-date-debut').value;
            const dFin = document.getElementById('live-date-fin').value;
            const fournId = document.getElementById('live-filter-fournisseur').value;

            const rows = document.querySelectorAll('.achat-row');
            let countVisible = 0;
            let sumTtc = 0;

            rows.forEach(row => {
                const searchBlob = row.getAttribute('data-search') || '';
                const rowDate = row.getAttribute('data-date') || '';
                const rowFourn = row.getAttribute('data-fournisseur') || '0';
                const ttc = parseFloat(row.getAttribute('data-ttc')) || 0;

                let match = true;

                if (q && !searchBlob.includes(q)) match = false;
                if (match && dDebut && rowDate && rowDate < dDebut) match = false;
                if (match && dFin && rowDate && rowDate > dFin) match = false;
                if (match && fournId !== "0" && rowFourn !== fournId) match = false;

                if (match) {
                    row.style.display = '';
                    countVisible++;
                    sumTtc += ttc;
                } else {
                    row.style.display = 'none';
                }
            });

            document.getElementById('live-count-achats').innerText = countVisible;
            document.getElementById('live-total-ttc').innerText = sumTtc.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' MAD';

            const emptyEl = document.getElementById('achats-empty-state');
            if (emptyEl) {
                emptyEl.classList.toggle('hidden', countVisible > 0 || rows.length === 0);
            }
        }

        function ouvrirModalNouvelAchat() {
            document.getElementById('fa-id').value = "";
            document.getElementById('modal-form-title').innerText = "Nouvel Achat";
            document.getElementById('fa-btn-submit').innerText = "Enregistrer l'Achat";
            document.getElementById('fa-numero').value = PROCHAIN_NUM_DEFAULT;
            document.getElementById('fa-date').value = TODAY_ISO_DEFAULT;
            document.getElementById('fa-notes').value = "";
            document.getElementById('fa-taux-tva').value = "10";

            lignesAchat = [
                { produit: "Diesel", citerne: "Citerne 2", qte: 0, pu_ht: 0, montant_ht: 0 }
            ];
            renderLignesAchat();

            document.getElementById('modal-form-achat').classList.remove('hidden');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }

        function ouvrirModalModification(achat) {
            document.getElementById('fa-id').value = achat.id;
            document.getElementById('modal-form-title').innerText = "Modifier l'Achat " + achat.numero_facture;
            document.getElementById('fa-btn-submit').innerText = "Mettre à jour";
            document.getElementById('fa-numero').value = achat.numero_facture || "";
            document.getElementById('fa-date').value = achat.date || "";
            document.getElementById('fa-notes').value = achat.observations || "";
            document.getElementById('fa-taux-tva').value = String(achat.taux_tva || 10);
            
            if (achat.fournisseur_id) {
                document.getElementById('fa-fournisseur').value = achat.fournisseur_id;
            }

            if (achat.lignes && achat.lignes.length > 0) {
                lignesAchat = achat.lignes;
            } else {
                lignesAchat = [
                    { produit: "Diesel", citerne: "Citerne 2", qte: 1, pu_ht: achat.montant_ht, montant_ht: achat.montant_ht }
                ];
            }
            renderLignesAchat();

            document.getElementById('modal-form-achat').classList.remove('hidden');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }

        function fermerModalAchat() {
            document.getElementById('modal-form-achat').classList.add('hidden');
        }

        function ajouterLigneAchat() {
            lignesAchat.push({
                produit: "Diesel",
                citerne: "Citerne 1",
                qte: 0,
                pu_ht: 0,
                montant_ht: 0
            });
            renderLignesAchat();
        }

        function supprimerLigneAchat(index) {
            if (lignesAchat.length > 1) {
                lignesAchat.splice(index, 1);
                renderLignesAchat();
            } else {
                alert("Vous devez avoir au moins une ligne d'achat.");
            }
        }

        function updateLigneVal(index, field, value) {
            lignesAchat[index][field] = value;
            if (field === 'qte' || field === 'pu_ht') {
                const qte = parseFloat(lignesAchat[index].qte) || 0;
                const pu = parseFloat(lignesAchat[index].pu_ht) || 0;
                lignesAchat[index].montant_ht = qte * pu;
            }
            renderLignesAchat();
        }

        function renderLignesAchat() {
            const tbody = document.getElementById('fa-lignes-body');
            tbody.innerHTML = '';

            lignesAchat.forEach((ligne, idx) => {
                let optionsProduits = LISTE_PRODUITS.map(p => 
                    `<option value="${p}" ${p === ligne.produit ? 'selected' : ''}>${p}</option>`
                ).join('');

                let optionsCiternes = LISTE_CITERNES.map(c => 
                    `<option value="${c}" ${c === ligne.citerne ? 'selected' : ''}>${c}</option>`
                ).join('');

                const tr = document.createElement('tr');
                tr.className = "text-xs";
                tr.innerHTML = `
                    <td class="p-2">
                        <select onchange="updateLigneVal(${idx}, 'produit', this.value)" class="w-full bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#1E3A52] rounded-lg px-2 py-1.5 font-semibold text-slate-900 dark:text-white outline-none">
                            ${optionsProduits}
                        </select>
                    </td>
                    <td class="p-2">
                        <select onchange="updateLigneVal(${idx}, 'citerne', this.value)" class="w-full bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#1E3A52] rounded-lg px-2 py-1.5 font-semibold text-slate-900 dark:text-white outline-none">
                            ${optionsCiternes}
                        </select>
                    </td>
                    <td class="p-2">
                        <input type="number" step="0.01" value="${ligne.qte}" oninput="updateLigneVal(${idx}, 'qte', this.value)" class="w-full bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#1E3A52] rounded-lg px-2 py-1.5 font-mono font-bold text-center text-slate-900 dark:text-white outline-none">
                    </td>
                    <td class="p-2">
                        <input type="number" step="0.0001" value="${ligne.pu_ht}" oninput="updateLigneVal(${idx}, 'pu_ht', this.value)" class="w-full bg-white dark:bg-[#0E1B26] border border-slate-300 dark:border-[#1E3A52] rounded-lg px-2 py-1.5 font-mono font-bold text-right text-slate-900 dark:text-white outline-none">
                    </td>
                    <td class="p-2 text-right font-mono font-black text-slate-900 dark:text-white">
                        ${(ligne.montant_ht || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td class="p-2 text-center">
                        <button type="button" onclick="supprimerLigneAchat(${idx})" class="p-1 text-rose-500 hover:text-rose-600 cursor-pointer">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            calculerTotauxAchat();
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }

        function calculerTotauxAchat() {
            let totalHT = 0;
            lignesAchat.forEach(l => {
                totalHT += parseFloat(l.montant_ht) || 0;
            });

            const tauxTVA = parseFloat(document.getElementById('fa-taux-tva').value) || 0;
            const montantTVA = totalHT * (tauxTVA / 100);
            const montantTTC = totalHT + montantTVA;

            document.getElementById('fa-montant-ht').value = totalHT.toFixed(2);
            document.getElementById('fa-montant-tva').value = montantTVA.toFixed(2);
            document.getElementById('fa-hidden-ttc').value = montantTTC.toFixed(2);
            document.getElementById('fa-display-ttc').innerText = montantTTC.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' MAD';

            document.getElementById('fa-hidden-lignes').value = JSON.stringify(lignesAchat);
        }

        function afficherDetailAchat(a) {
            document.getElementById('da-num').innerText = "Détails : " + a.numero_facture;
            document.getElementById('da-date').innerText = "Date : " + a.date;
            document.getElementById('da-fournisseur').innerText = a.fournisseur_nom;
            document.getElementById('da-numero-facture').innerText = a.numero_facture;

            document.getElementById('da-ht').innerText = a.montant_ht.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' MAD';
            document.getElementById('da-tva-label').innerText = "TVA (" + a.taux_tva + "%) :";
            document.getElementById('da-tva').innerText = a.montant_tva.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' MAD';
            document.getElementById('da-ttc').innerText = a.montant_total.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' MAD';

            const tbody = document.getElementById('da-lignes-body');
            tbody.innerHTML = '';
            if (a.lignes && a.lignes.length > 0) {
                a.lignes.forEach(l => {
                    const tr = document.createElement('tr');
                    tr.className = "text-xs font-medium text-slate-800 dark:text-slate-200";
                    tr.innerHTML = `
                        <td class="p-2.5 font-bold">${l.produit || 'Produit'}</td>
                        <td class="p-2.5 text-center font-mono">${l.qte || 0}</td>
                        <td class="p-2.5 text-right font-mono">${(parseFloat(l.pu_ht) || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} MAD</td>
                        <td class="p-2.5 text-right font-mono font-bold">${(parseFloat(l.montant_ht) || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })} MAD</td>
                        <td class="p-2.5 text-slate-500">${l.citerne || '-'}</td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-slate-400 italic">Aucun détail de ligne pour cet achat.</td></tr>';
            }

            const pieceCont = document.getElementById('da-piece-container');
            const pieceContent = document.getElementById('da-piece-content');
            if (a.fichier_facture && a.fichier_facture.trim() !== '') {
                pieceCont.classList.remove('hidden');
                pieceContent.innerHTML = `
                    <a href="${a.fichier_facture}" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-sky-500/10 text-sky-500 hover:bg-sky-500/20 rounded-xl font-bold transition">
                        <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                        <span>Consulter la pièce jointe</span>
                    </a>
                `;
            } else {
                pieceCont.classList.add('hidden');
            }

            const notesCont = document.getElementById('da-notes-container');
            if (a.observations && a.observations.trim() !== '') {
                notesCont.classList.remove('hidden');
                document.getElementById('da-notes').innerText = a.observations;
            } else {
                notesCont.classList.add('hidden');
            }

            document.getElementById('modal-details-achat').classList.remove('hidden');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }

        function fermerModalDetails() {
            document.getElementById('modal-details-achat').classList.add('hidden');
        }

        function confirmerSuppression(id, num) {
            if (confirm("Voulez-vous vraiment supprimer définitivement l'achat " + num + " ?")) {
                window.location.href = "/achats/supprimer/" + id;
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            filtrerAchatsEnDirect();
        });
    </script>
    """

    variables_js = f"""
    <script>
        const PROCHAIN_NUM_DEFAULT = "{prochain_num}";
        const TODAY_ISO_DEFAULT = "{today_iso}";
    </script>
    """

    content = html_markup + variables_js + js_script
    return HTMLResponse(content=layout(content, active_tab="achats", request=request))

@router.post("/achats/enregistrer")
async def action_enregistrer_achat(
    achat_id: Optional[str] = Form(None),
    fournisseur_id: int = Form(...),
    numero_facture: str = Form(""),
    date_achat: str = Form(...),
    montant_ht: float = Form(0.0),
    taux_tva: float = Form(10.0),
    montant_tva: float = Form(0.0),
    montant_total: float = Form(...),
    observations: str = Form(""),
    lignes_json: str = Form("[]"),
    fichier: UploadFile = File(None)
):
    fichier_facture = None
    if fichier and fichier.filename:
        ext = os.path.splitext(fichier.filename)[1].lower()
        content_type = (fichier.content_type or "").lower()

        if ext in ALLOWED_EXTENSIONS or content_type in ALLOWED_MIME_TYPES:
            clean_num = "".join(c for c in numero_facture if c.isalnum() or c in ("-", "_")) or "FAC"
            nom_unique = f"facture_{int(time.time())}_{clean_num}{ext}"
            chemin_disque = UPLOAD_DIR / nom_unique
            
            with open(chemin_disque, "wb") as buffer:
                buffer.write(await fichier.read())
            fichier_facture = f"/static/uploads/factures/{nom_unique}"

    produit_principal = "Diesel"
    volume_total = 0.0
    pu_premier = 0.0
    try:
        lignes = json.loads(lignes_json)
        if lignes:
            produit_principal = lignes[0].get("produit", "Diesel")
            volume_total = sum(float(l.get("qte", 0.0)) for l in lignes)
            pu_premier = float(lignes[0].get("pu_ht", 0.0))
    except Exception:
        pass

    conn = get_db_connection()
    try:
        if achat_id and str(achat_id).strip().isdigit():
            aid = int(achat_id)
            if fichier_facture:
                conn.execute("""
                    UPDATE achats_fournisseurs 
                    SET fournisseur_id = ?, numero_facture = ?, date = ?, produit = ?, volume_litres = ?, prix_unitaire = ?,
                        montant_ht = ?, taux_tva = ?, montant_tva = ?, montant_total = ?, observations = ?, 
                        lignes_json = ?, fichier_facture = ?
                    WHERE id = ?
                """, (fournisseur_id, numero_facture.strip(), date_achat, produit_principal, volume_total, pu_premier, montant_ht, taux_tva, montant_tva, montant_total, observations.strip(), lignes_json, fichier_facture, aid))
            else:
                conn.execute("""
                    UPDATE achats_fournisseurs 
                    SET fournisseur_id = ?, numero_facture = ?, date = ?, produit = ?, volume_litres = ?, prix_unitaire = ?,
                        montant_ht = ?, taux_tva = ?, montant_tva = ?, montant_total = ?, observations = ?, 
                        lignes_json = ?
                    WHERE id = ?
                """, (fournisseur_id, numero_facture.strip(), date_achat, produit_principal, volume_total, pu_premier, montant_ht, taux_tva, montant_tva, montant_total, observations.strip(), lignes_json, aid))
        else:
            conn.execute("""
                INSERT INTO achats_fournisseurs 
                (fournisseur_id, numero_facture, date, produit, volume_litres, prix_unitaire, montant_ht, taux_tva, montant_tva, montant_total, observations, fichier_facture, lignes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fournisseur_id, numero_facture.strip(), date_achat, produit_principal, volume_total, pu_premier, montant_ht, taux_tva, montant_tva, montant_total, observations.strip(), fichier_facture or "", lignes_json))
        
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url="/achats", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/achats/supprimer/{achat_id}")
async def action_supprimer_achat(achat_id: int):
    database.supprimer_achat(achat_id)
    return RedirectResponse(url="/achats", status_code=status.HTTP_303_SEE_OTHER)