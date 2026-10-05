import html
import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Request, Form, UploadFile, File, status
from fastapi.responses import HTMLResponse, RedirectResponse

import database
from ui_utils import layout

router = APIRouter()

UPLOAD_DIR = "static/uploads/fournisseurs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def format_curr(val: float) -> str:
    try:
        val_float = float(val or 0.0)
        return f"{val_float:,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return "0,00"

def get_initials(name: str) -> str:
    parts = (name or "").strip().split()
    if len(parts) >= 2:
        return (parts[0][:1] + parts[1][:1]).upper()
    elif len(parts) == 1 and parts[0]:
        return parts[0][:2].upper()
    return "FR"

def get_avatar_bg(name: str) -> str:
    colors = [
        "bg-blue-600/20 text-blue-400 border-blue-500/30",
        "bg-teal-600/20 text-teal-400 border-teal-500/30",
        "bg-purple-600/20 text-purple-400 border-purple-500/30",
        "bg-amber-600/20 text-amber-400 border-amber-500/30",
        "bg-rose-600/20 text-rose-400 border-rose-500/30",
        "bg-cyan-600/20 text-cyan-400 border-cyan-500/30",
    ]
    return colors[hash(name or "") % len(colors)]


@router.get("/fournisseurs", response_class=HTMLResponse)
async def page_fournisseurs(request: Request, id: int = None):
    list_fournisseurs = database.get_fournisseurs()
    next_code = database.generer_prochain_code_fournisseur()
    today = datetime.today().strftime("%Y-%m-%d")

    # =========================================================================
    # MODALE : NOUVEAU FOURNISSEUR
    # =========================================================================
    modal_nouveau_html = f"""
    <div id="modal-nouveau-f" class="hidden fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4">
        <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-2xl w-full max-w-2xl max-h-[92vh] overflow-y-auto shadow-2xl flex flex-col">
            <div class="px-5 py-3.5 border-b border-slate-200 dark:border-[#183042] flex items-center justify-between sticky top-0 bg-white dark:bg-[#0E1B26] z-10">
                <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-lg bg-[#FF6A00]/15 text-[#FF6A00] flex items-center justify-center font-black">
                        <i data-lucide="plus-circle" class="w-4 h-4"></i>
                    </div>
                    <h2 class="text-sm font-black text-slate-900 dark:text-white tracking-tight">Nouveau Fournisseur</h2>
                </div>
                <button type="button" onclick="document.getElementById('modal-nouveau-f').classList.add('hidden')" class="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            </div>

            <form method="POST" action="/fournisseurs/nouveau" enctype="multipart/form-data" class="p-5 space-y-3.5 text-xs">
                <div class="grid grid-cols-1 sm:grid-cols-12 gap-3">
                    <div class="sm:col-span-3">
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Code *</label>
                        <input type="text" name="code" value="{next_code}" required class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 font-mono font-bold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#FF6A00]/40">
                    </div>
                    <div class="sm:col-span-5">
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Nom / Société *</label>
                        <input type="text" name="nom" required class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#FF6A00]/40">
                    </div>
                    <div class="sm:col-span-4">
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Catégorie *</label>
                        <select name="type_fournisseur" required class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white font-medium focus:outline-none">
                            <option value="Carburant" selected>Carburant</option>
                            <option value="Lubrifiant">Lubrifiant</option>
                            <option value="Services">Services</option>
                            <option value="Équipements">Équipements</option>
                            <option value="Grossiste">Grossiste</option>
                            <option value="Autre">Autre</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Contact</label>
                        <input type="text" name="contact_nom" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Téléphone</label>
                        <input type="text" name="telephone" placeholder="06... / 05..." class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Email</label>
                        <input type="email" name="email" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white focus:outline-none">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Adresse</label>
                        <input type="text" name="adresse" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Conditions de Paiement</label>
                        <input type="text" name="conditions_paiement" placeholder="ex: Comptant / 30 jours" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white focus:outline-none">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 border-t border-slate-100 dark:border-[#183042]/70">
                    <div>
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">
                            Solde Initial (MAD) <span class="font-normal text-[10px] text-slate-400">(- dette, + crédit)</span>
                        </label>
                        <input type="number" step="0.01" name="solde_initial" value="0" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 font-mono font-bold text-slate-900 dark:text-white focus:outline-none">
                    </div>
                    <div>
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Montant Fidélité Initiale</label>
                        <input type="number" step="0.01" name="montant_fidelite" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 font-mono text-slate-900 dark:text-white focus:outline-none">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 pt-1 border-t border-slate-100 dark:border-[#183042]/70">
                    <div class="sm:col-span-5">
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Document (RC / Contrat)</label>
                        <input type="file" name="fichier_doc" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2 py-1 text-[11px] text-slate-900 dark:text-white file:mr-2 file:py-0.5 file:px-2 file:rounded-md file:border-0 file:text-[10px] file:font-semibold file:bg-slate-200 dark:file:bg-[#1e3c54] file:text-slate-800 dark:file:text-white cursor-pointer focus:outline-none">
                    </div>
                    <div class="sm:col-span-3">
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Catégorie Doc</label>
                        <select name="doc_categorie" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white focus:outline-none">
                            <option value="RC" selected>RC</option>
                            <option value="Statuts">Statuts</option>
                            <option value="Contrat">Contrat</option>
                            <option value="RIB">RIB</option>
                            <option value="Autre">Autre</option>
                        </select>
                    </div>
                    <div class="sm:col-span-4">
                        <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Description doc</label>
                        <input type="text" name="doc_description" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white focus:outline-none">
                    </div>
                </div>

                <div>
                    <label class="block text-[11px] font-bold text-slate-700 dark:text-slate-200 mb-1">Notes / Observations</label>
                    <textarea name="notes" rows="2" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl p-2.5 text-slate-900 dark:text-white focus:outline-none"></textarea>
                </div>

                <div class="flex items-center justify-end pt-2 border-t border-slate-200 dark:border-[#183042]">
                    <button type="submit" class="h-8 px-5 rounded-xl bg-[#0070F3] hover:bg-[#005cd6] text-white font-bold text-xs inline-flex items-center gap-1.5 shadow-md active:scale-95 transition">
                        <span>Enregistrer</span>
                    </button>
                </div>
            </form>
        </div>
    </div>
    """

    # =========================================================================
    # MODALES COMMUNES (ACTION RAPIDE : MODIFIER, SUPPRIMER, ACHAT, PAIEMENT)
    # =========================================================================
    modales_rapides_html = f"""
    <!-- MODALE MODIFIER -->
    <div id="modal-modifier-f" class="hidden fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-3">
        <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-2xl w-full max-w-lg p-4 shadow-2xl space-y-3">
            <div class="flex items-center justify-between border-b border-slate-200 dark:border-[#183042] pb-2">
                <h3 class="text-xs sm:text-sm font-black text-slate-900 dark:text-white flex items-center gap-1.5 uppercase">
                    <i data-lucide="edit-3" class="w-4 h-4 text-[#FF6A00]"></i> Modifier Fournisseur
                </h3>
                <button onclick="document.getElementById('modal-modifier-f').classList.add('hidden')" class="text-slate-400 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
            </div>
            <form method="POST" action="/fournisseurs/modifier" class="space-y-2.5 text-xs">
                <input type="hidden" name="fournisseur_id" id="mod-id">
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Code *</label>
                        <input type="text" name="code" id="mod-code" required class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white font-mono uppercase">
                    </div>
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Nom *</label>
                        <input type="text" name="nom" id="mod-nom" required class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Type</label>
                        <select name="type_fournisseur" id="mod-type" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                            <option value="Carburant">Carburant</option>
                            <option value="Lubrifiant">Lubrifiant</option>
                            <option value="Services">Services</option>
                            <option value="Équipements">Équipements</option>
                            <option value="Grossiste">Grossiste</option>
                            <option value="Autre">Autre</option>
                        </select>
                    </div>
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Statut</label>
                        <select name="statut" id="mod-statut" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                            <option value="Actif">Actif</option>
                            <option value="Inactif">Inactif</option>
                        </select>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Téléphone</label>
                        <input type="text" name="telephone" id="mod-tel" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                    </div>
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Email</label>
                        <input type="email" name="email" id="mod-email" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                    </div>
                </div>
                <div class="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-[#183042]">
                    <button type="button" onclick="document.getElementById('modal-modifier-f').classList.add('hidden')" class="px-3 py-1.5 text-slate-400 hover:text-white font-bold">Annuler</button>
                    <button type="submit" class="h-8 px-4 rounded-xl bg-[#0070F3] hover:bg-[#005cd6] text-white font-bold">Enregistrer</button>
                </div>
            </form>
        </div>
    </div>

    <!-- MODALE SUPPRIMER -->
    <div id="modal-supprimer-f" class="hidden fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-3">
        <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-2xl w-full max-w-sm p-4 shadow-2xl text-center space-y-2.5">
            <div class="w-10 h-10 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center mx-auto">
                <i data-lucide="alert-triangle" class="w-5 h-5"></i>
            </div>
            <h3 class="text-sm font-bold text-slate-900 dark:text-white">Supprimer ce fournisseur ?</h3>
            <p class="text-xs text-slate-400" id="sup-nom-text">Cette action supprimera également tous ses BL et paiements associés.</p>
            <form method="POST" action="/fournisseurs/supprimer" class="pt-2 flex items-center justify-center gap-2">
                <input type="hidden" name="fournisseur_id" id="sup-id">
                <button type="button" onclick="document.getElementById('modal-supprimer-f').classList.add('hidden')" class="px-3 py-1.5 text-xs font-bold text-slate-400 hover:text-white">Annuler</button>
                <button type="submit" class="h-8 px-4 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-black text-xs shadow-xs transition">Confirmer</button>
            </form>
        </div>
    </div>

    <!-- MODALE ACHAT BL -->
    <div id="modal-achat" class="hidden fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-3">
        <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-2xl w-full max-w-md p-4 shadow-2xl space-y-2.5">
            <div class="flex items-center justify-between border-b border-slate-200 dark:border-[#183042] pb-2">
                <h3 class="text-xs sm:text-sm font-black text-slate-900 dark:text-white flex items-center gap-1.5 uppercase">
                    <i data-lucide="fuel" class="w-4 h-4 text-[#FF6A00]"></i> Nouvel Achat BL (<span id="achat-f-nom" class="text-white"></span>)
                </h3>
                <button onclick="document.getElementById('modal-achat').classList.add('hidden')" class="text-slate-400 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
            </div>
            <form method="POST" action="/fournisseurs/achat" class="space-y-2 text-xs">
                <input type="hidden" name="fournisseur_id" id="achat-f-id">
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Date *</label>
                        <input type="date" name="date" value="{today}" required class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                    </div>
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Réf BL *</label>
                        <input type="text" name="reference_bl" placeholder="ex: BL-2026-..." required class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                    </div>
                </div>
                <div>
                    <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Produit *</label>
                    <select name="produit" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                        <option value="Diesel (Gasoil 10ppm)">Diesel (Gasoil 10ppm)</option>
                        <option value="Super Sans Plomb (SSP)">Super Sans Plomb (SSP)</option>
                        <option value="Lubrifiants & Huiles">Lubrifiants & Huiles</option>
                        <option value="Autre Prestation">Autre Prestation</option>
                    </select>
                </div>
                <div class="grid grid-cols-3 gap-2">
                    <div>
                        <label class="block text-[10px] font-bold text-slate-400 mb-0.5">Volume (L)</label>
                        <input type="number" step="0.01" id="achat-vol" name="volume" oninput="calcAchatTotal()" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2 py-1.5 text-slate-900 dark:text-white font-mono">
                    </div>
                    <div>
                        <label class="block text-[10px] font-bold text-slate-400 mb-0.5">Prix Unit.</label>
                        <input type="number" step="0.001" id="achat-pu" name="prix_unitaire" oninput="calcAchatTotal()" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2 py-1.5 text-slate-900 dark:text-white font-mono">
                    </div>
                    <div>
                        <label class="block text-[10px] font-bold text-[#FF6A00] mb-0.5">Total TTC *</label>
                        <input type="number" step="0.01" id="achat-total" name="montant_total" required class="w-full bg-[#FF6A00]/10 border border-[#FF6A00]/40 rounded-xl px-2 py-1.5 text-[#FF6A00] font-black font-mono">
                    </div>
                </div>
                <div class="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-[#183042]">
                    <button type="button" onclick="document.getElementById('modal-achat').classList.add('hidden')" class="px-3 py-1.5 text-slate-400 hover:text-white font-bold">Annuler</button>
                    <button type="submit" class="h-8 px-4 rounded-xl bg-[#FF6A00] hover:bg-[#e55f00] text-white font-black">Valider BL</button>
                </div>
            </form>
        </div>
    </div>

    <!-- MODALE PAIEMENT RAPIDE -->
    <div id="modal-reglement" class="hidden fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-3">
        <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-2xl w-full max-w-md p-4 shadow-2xl space-y-2.5">
            <div class="flex items-center justify-between border-b border-slate-200 dark:border-[#183042] pb-2">
                <h3 class="text-xs sm:text-sm font-black text-slate-900 dark:text-white flex items-center gap-1.5 uppercase">
                    <i data-lucide="wallet" class="w-4 h-4 text-emerald-500"></i> Paiement (<span id="pay-f-nom" class="text-white"></span>)
                </h3>
                <button onclick="document.getElementById('modal-reglement').classList.add('hidden')" class="text-slate-400 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
            </div>
            <div class="flex items-center justify-between p-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs">
                <span class="font-bold text-rose-400">Dette Restante :</span>
                <span class="font-black font-mono text-rose-400" id="pay-f-dette">0,00 MAD</span>
            </div>
            <form method="POST" action="/fournisseurs/reglement" class="space-y-2 text-xs">
                <input type="hidden" name="fournisseur_id" id="pay-f-id">
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Mode *</label>
                        <select name="mode_paiement" class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white font-bold">
                            <option value="Chèque">Chèque</option>
                            <option value="Virement Bancaire">Virement Bancaire</option>
                            <option value="Espèces">Espèces</option>
                            <option value="Effet / Traite">Effet / Traite</option>
                        </select>
                    </div>
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Date *</label>
                        <input type="date" name="date" value="{today}" required class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                    </div>
                </div>
                <div>
                    <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Montant Réglé (MAD) *</label>
                    <input type="number" step="0.01" name="montant" required class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-emerald-400 font-black font-mono">
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Réf / N° Paiement *</label>
                        <input type="text" name="reference_paiement" required class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                    </div>
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-0.5">Banque</label>
                        <input type="text" name="banque" placeholder="BP, Attijari..." class="w-full bg-slate-50 dark:bg-[#132738] border border-slate-300 dark:border-[#1b3b54] rounded-xl px-2.5 py-1.5 text-slate-900 dark:text-white">
                    </div>
                </div>
                <div class="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-[#183042]">
                    <button type="button" onclick="document.getElementById('modal-reglement').classList.add('hidden')" class="px-3 py-1.5 text-slate-400 hover:text-white font-bold">Annuler</button>
                    <button type="submit" class="h-8 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-black">Encaisser / Décaisser</button>
                </div>
            </form>
        </div>
    </div>
    """

    # =========================================================================
    # CAS 1 : VUE DOSSIER DÉTAILLÉ (si un fournisseur spécifique est ouvert)
    # =========================================================================
    if id is not None:
        data = database.get_fournisseur_complet(id)
        if not data:
            return RedirectResponse("/fournisseurs", status_code=status.HTTP_303_SEE_OTHER)

        f = data["fournisseur"]
        operations = data.get("operations", [])
        nom_display = html.escape(f['nom'])

        rows_html = ""
        for op in operations:
            is_achat = op.get("type_op") == "ACHAT"
            ref_safe = html.escape(str(op.get('ref') or '-'))
            details_safe = html.escape(str(op.get('details') or '-'))
            badge = '<span class="px-2 py-0.5 rounded-full text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/25 font-bold">BL Achat</span>' if is_achat else '<span class="px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 font-bold">Règlement</span>'
            achat_val = f"<span class='text-white font-bold font-mono'>{format_curr(op['montant_achat'])}</span>" if is_achat else "<span class='text-slate-600'>-</span>"
            paye_val = f"<span class='text-emerald-400 font-bold font-mono'>+{format_curr(op['montant_paye'])}</span>" if not is_achat else "<span class='text-slate-600'>-</span>"

            rows_html += f"""
            <tr class="hover:bg-white/[0.02] border-b border-[#183042]/50 text-xs">
                <td class="px-3 py-2 font-mono font-bold text-white">{op['date']} <span class="text-[10px] text-[#FF6A00] block">{ref_safe}</span></td>
                <td class="px-3 py-2">{badge}</td>
                <td class="px-3 py-2 text-slate-300">{details_safe}</td>
                <td class="px-3 py-2 text-right">{achat_val}</td>
                <td class="px-3 py-2 text-right">{paye_val}</td>
            </tr>
            """

        detail_content = f"""
        <div class="space-y-3">
            <div class="flex items-center justify-between">
                <a href="/fournisseurs" class="inline-flex items-center gap-1.5 text-xs font-bold text-slate-400 hover:text-white bg-[#0E1B26] border border-[#183042] px-3 py-1.5 rounded-xl transition">
                    <i data-lucide="arrow-left" class="w-4 h-4"></i>
                    <span>Retour aux dossiers fournisseurs</span>
                </a>
                <div class="flex gap-1.5">
                    <button onclick="ouvrirAchatDirect('{f['id']}', '{html.escape(f['nom'], quote=True)}')" class="h-8 px-3.5 rounded-xl bg-[#FF6A00] hover:bg-[#e55f00] text-white font-bold text-xs inline-flex items-center gap-1.5 shadow-sm">
                        <i data-lucide="fuel" class="w-3.5 h-3.5"></i> Achat BL
                    </button>
                    <button onclick="ouvrirPaiementDirect('{f['id']}', '{html.escape(f['nom'], quote=True)}', '{data['dette']}')" class="h-8 px-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs inline-flex items-center gap-1.5 shadow-sm">
                        <i data-lucide="wallet" class="w-3.5 h-3.5"></i> Paiement
                    </button>
                </div>
            </div>

            <!-- EN-TETE DOSSIER -->
            <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-xs">
                <div class="flex items-center gap-3">
                    <div class="w-12 h-12 rounded-2xl {get_avatar_bg(f['nom'])} border flex items-center justify-center font-black text-sm">
                        {get_initials(f['nom'])}
                    </div>
                    <div>
                        <h1 class="text-base font-black text-slate-900 dark:text-white flex items-center gap-2">
                            <span>{nom_display}</span>
                            <span class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-[#FF6A00]/15 text-[#FF6A00] border border-[#FF6A00]/30">{f['code']}</span>
                        </h1>
                        <p class="text-xs text-slate-400 mt-0.5">{f.get('type_fournisseur') or 'Fournisseur'} • {f.get('telephone') or 'Sans téléphone'} • {f.get('email') or 'Sans email'}</p>
                    </div>
                </div>

                <div class="flex gap-2">
                    <div class="px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-[#132738] border border-slate-200 dark:border-[#183042] text-right">
                        <span class="text-[9px] uppercase font-bold text-slate-400 block">Total Achats</span>
                        <span class="text-xs font-black font-mono text-cyan-400">{format_curr(data['total_achats'])} MAD</span>
                    </div>
                    <div class="px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-[#132738] border border-slate-200 dark:border-[#183042] text-right">
                        <span class="text-[9px] uppercase font-bold text-slate-400 block">Total Réglé</span>
                        <span class="text-xs font-black font-mono text-emerald-400">{format_curr(data['total_paye'])} MAD</span>
                    </div>
                    <div class="px-3 py-1.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-right">
                        <span class="text-[9px] uppercase font-bold text-rose-400 block">Solde Dû</span>
                        <span class="text-xs font-black font-mono text-rose-500">{format_curr(data['dette'])} MAD</span>
                    </div>
                </div>
            </div>

            <!-- TABLEAU DES TRANSACTIONS DU DOSSIER -->
            <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-2xl overflow-hidden shadow-xs">
                <div class="px-4 py-2.5 border-b border-slate-200 dark:border-[#183042] font-black text-xs text-white uppercase tracking-wider flex items-center gap-2">
                    <i data-lucide="history" class="w-4 h-4 text-[#FF6A00]"></i>
                    <span>Toutes les transactions & BL du dossier</span>
                </div>
                <div class="overflow-x-auto max-h-[480px]">
                    <table class="w-full text-left">
                        <thead class="bg-slate-50 dark:bg-[#132738] text-[10px] font-black uppercase text-slate-400 border-b border-slate-200 dark:border-[#183042] sticky top-0">
                            <tr>
                                <th class="px-3 py-2">Date & Réf</th>
                                <th class="px-3 py-2">Type</th>
                                <th class="px-3 py-2">Détails</th>
                                <th class="px-3 py-2 text-right">Achat (MAD)</th>
                                <th class="px-3 py-2 text-right">Réglé (MAD)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html if rows_html else '<tr><td colspan="5" class="text-center py-8 text-xs text-slate-500 italic">Aucune transaction</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {modal_nouveau_html}
        {modales_rapides_html}

        <script>
            function calcAchatTotal() {{
                const vol = parseFloat(document.getElementById('achat-vol').value) || 0;
                const pu = parseFloat(document.getElementById('achat-pu').value) || 0;
                if (vol > 0 && pu > 0) {{
                    document.getElementById('achat-total').value = (vol * pu).toFixed(2);
                }}
            }}
            function ouvrirAchatDirect(id, nom) {{
                document.getElementById('achat-f-id').value = id;
                document.getElementById('achat-f-nom').innerText = nom;
                document.getElementById('modal-achat').classList.remove('hidden');
            }}
            function ouvrirPaiementDirect(id, nom, dette) {{
                document.getElementById('pay-f-id').value = id;
                document.getElementById('pay-f-nom').innerText = nom;
                document.getElementById('pay-f-dette').innerText = (parseFloat(dette) || 0).toLocaleString('fr-FR', {{minimumFractionDigits: 2}}) + ' MAD';
                document.getElementById('modal-reglement').classList.remove('hidden');
            }}
        </script>
        """
        return HTMLResponse(layout(detail_content, active_tab="fournisseurs", request=request))

    # =========================================================================
    # CAS 2 : VUE PAR DÉFAUT -> GRILLE DES DOSSIERS FOURNISSEURS (IMAGE 2 & 3)
    # =========================================================================
    cards_html = ""
    for f in list_fournisseurs:
        f_id = f["id"]
        # Récupération rapide dette / données complètes
        data_f = database.get_fournisseur_complet(f_id)
        dette_val = data_f.get("dette", 0.0) if data_f else 0.0

        nom_esc = html.escape(f.get("nom", ""))
        code_esc = html.escape(f.get("code", ""))
        tel_esc = html.escape(f.get("telephone") or "+212 600 000 000")
        type_esc = html.escape(f.get("type_fournisseur") or "Entreprise")
        statut_esc = f.get("statut") or "Actif"
        is_actif = statut_esc.lower() == "actif"
        
        statut_badge = '<span class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Actif</span>' if is_actif else '<span class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-slate-500/10 text-slate-400 border border-slate-500/20">Inactif</span>'

        solde_color = "text-rose-500 font-black" if dette_val > 0.01 else "text-emerald-400 font-bold"

        doc_html = '<span class="text-[10px] italic text-slate-500">Aucun document</span>'
        if f.get("document"):
            doc_cat = html.escape(f.get("doc_categorie") or "RC")
            doc_html = f'<a href="{f["document"]}" target="_blank" class="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold inline-flex items-center gap-0.5"><i data-lucide="file" class="w-2.5 h-2.5"></i> {doc_cat}</a>'

        cards_html += f"""
        <div class="supplier-card bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] hover:border-[#1e3e57] rounded-2xl p-3.5 flex flex-col justify-between shadow-xs transition hover:shadow-lg relative group"
             data-name="{nom_esc.lower()}"
             data-code="{code_esc.lower()}"
             data-type="{type_esc}">
            
            <div>
                <!-- HAUT DE CARTE : AVATAR, INFOS, STATUT & BOUTON VOIR -->
                <div class="flex items-start justify-between gap-2 mb-3">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <div class="w-10 h-10 rounded-xl {get_avatar_bg(f['nom'])} border flex items-center justify-center font-black text-xs shrink-0 shadow-xs">
                            {get_initials(f['nom'])}
                        </div>
                        <div class="min-w-0">
                            <h3 class="font-bold text-xs text-slate-900 dark:text-white truncate leading-tight hover:text-[#FF6A00] transition" title="{nom_esc}">
                                <a href="/fournisseurs?id={f_id}">{nom_esc}</a>
                            </h3>
                            <div class="flex items-center gap-1.5 mt-1">
                                <span class="text-[10px] text-slate-400 truncate">{type_esc}</span>
                                {statut_badge}
                            </div>
                        </div>
                    </div>
                    <a href="/fournisseurs?id={f_id}" class="w-7 h-7 rounded-lg bg-slate-100 dark:bg-[#132738] hover:bg-slate-200 dark:hover:bg-[#1b384f] text-slate-400 hover:text-white flex items-center justify-center shrink-0 transition" title="Ouvrir dossier">
                        <i data-lucide="chevron-right" class="w-4 h-4"></i>
                    </a>
                </div>

                <!-- CORPS DE CARTE : TEL, CODE, SOLDE DÛ, DOCS -->
                <div class="space-y-1.5 text-[11px] pt-1 border-t border-slate-100 dark:border-[#183042]/60">
                    <div class="flex items-center gap-2 text-slate-400">
                        <i data-lucide="phone" class="w-3.5 h-3.5 text-slate-500"></i>
                        <span class="text-slate-300 font-mono text-[10.5px]">{tel_esc}</span>
                    </div>
                    <div class="flex items-center gap-2 text-slate-400">
                        <i data-lucide="credit-card" class="w-3.5 h-3.5 text-slate-500"></i>
                        <span class="text-slate-300 font-mono text-[10.5px]">{code_esc}</span>
                    </div>
                    <div class="flex items-center justify-between pt-1">
                        <span class="text-slate-400 font-bold text-[10.5px]">Solde Dû :</span>
                        <span class="{solde_color} font-mono text-xs">{format_curr(dette_val)} DH</span>
                    </div>
                    <div class="flex items-center justify-between pt-1 text-[10px]">
                        <span class="text-slate-400 font-bold uppercase tracking-wider text-[9.5px]">DOCUMENTS :</span>
                        <div>{doc_html}</div>
                    </div>
                </div>
            </div>

            <!-- BAS DE CARTE : BOUTON DOSSIER + MENU 3 POINTS (IMAGE 3) -->
            <div class="pt-3 mt-3 border-t border-slate-100 dark:border-[#183042]/60 flex items-center gap-1.5">
                <a href="/fournisseurs?id={f_id}" class="flex-1 h-8 rounded-xl bg-slate-100 dark:bg-[#132738] hover:bg-slate-200 dark:hover:bg-[#1b384f] text-slate-800 dark:text-slate-200 font-bold text-xs inline-flex items-center justify-center gap-1.5 transition">
                    <i data-lucide="sliders-horizontal" class="w-3.5 h-3.5"></i>
                    <span>Dossier</span>
                </a>

                <!-- BOUTON 3 POINTS & DROPDOWN -->
                <div class="relative">
                    <button type="button" onclick="toggleMenu('menu-{f_id}', event)" class="w-8 h-8 rounded-xl bg-slate-100 dark:bg-[#132738] hover:bg-slate-200 dark:hover:bg-[#1b384f] text-slate-400 hover:text-white flex items-center justify-center transition">
                        <i data-lucide="more-vertical" class="w-4 h-4"></i>
                    </button>

                    <div id="menu-{f_id}" class="card-dropdown hidden absolute right-0 bottom-full mb-1 w-44 bg-[#0E1B26] border border-[#183042] rounded-2xl shadow-2xl p-1.5 z-40 space-y-0.5">
                        <a href="/fournisseurs?id={f_id}" class="flex items-center gap-2 px-2.5 py-1.5 text-xs text-slate-200 hover:text-white hover:bg-white/5 rounded-xl transition">
                            <i data-lucide="folder-open" class="w-3.5 h-3.5 text-cyan-400"></i>
                            <span>Ouvrir Dossier</span>
                        </a>
                        <button type="button" onclick="ouvrirModifierDirect('{f_id}', '{code_esc}', '{nom_esc}', '{type_esc}', '{statut_esc}', '{tel_esc}', '{f.get('email') or ''}')" class="w-full text-left flex items-center gap-2 px-2.5 py-1.5 text-xs text-slate-200 hover:text-white hover:bg-white/5 rounded-xl transition">
                            <i data-lucide="edit-3" class="w-3.5 h-3.5 text-amber-400"></i>
                            <span>Modifier</span>
                        </button>
                        <button type="button" onclick="ouvrirAchatDirect('{f_id}', '{nom_esc}')" class="w-full text-left flex items-center gap-2 px-2.5 py-1.5 text-xs text-slate-200 hover:text-white hover:bg-white/5 rounded-xl transition">
                            <i data-lucide="fuel" class="w-3.5 h-3.5 text-[#FF6A00]"></i>
                            <span>Achat BL</span>
                        </button>
                        <button type="button" onclick="ouvrirPaiementDirect('{f_id}', '{nom_esc}', '{dette_val}')" class="w-full text-left flex items-center gap-2 px-2.5 py-1.5 text-xs text-slate-200 hover:text-white hover:bg-white/5 rounded-xl transition">
                            <i data-lucide="wallet" class="w-3.5 h-3.5 text-emerald-400"></i>
                            <span>Paiement</span>
                        </button>
                        <div class="my-1 border-t border-[#183042]"></div>
                        <button type="button" onclick="ouvrirSupprimerDirect('{f_id}', '{nom_esc}')" class="w-full text-left flex items-center gap-2 px-2.5 py-1.5 text-xs text-rose-500 hover:bg-rose-500/10 rounded-xl transition font-bold">
                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            <span>Supprimer</span>
                        </button>
                    </div>
                </div>
            </div>

        </div>
        """

    # =========================================================================
    # ASSEMBLAGE DE L'INTERFACE PRINCIPALE
    # =========================================================================
    content = f"""
    <div class="space-y-3.5">

        <!-- BARRE DE GESTION FOURNISSEURS (IMAGE 2) -->
        <div class="bg-white dark:bg-[#0E1B26] border border-slate-200 dark:border-[#183042] rounded-2xl p-2.5 flex flex-wrap items-center justify-between gap-2.5 shadow-xs">
            
            <div class="flex items-center gap-2.5">
                <div class="w-9 h-9 rounded-xl bg-blue-600/15 text-blue-500 border border-blue-500/20 flex items-center justify-center shrink-0">
                    <i data-lucide="building-2" class="w-5 h-5"></i>
                </div>
                <div>
                    <h1 class="text-sm font-black text-slate-900 dark:text-white tracking-tight">Gestion Fournisseurs</h1>
                    <p class="text-[10.5px] text-slate-400">Dossiers & suivi des comptes fournisseurs</p>
                </div>
            </div>

            <!-- BARRE DE RECHERCHE, FILTRES & BOUTON NOUVEAU -->
            <div class="flex flex-wrap items-center gap-2">
                <!-- RECHERCHE -->
                <div class="relative">
                    <i data-lucide="search" class="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"></i>
                    <input type="text" id="searchInput" oninput="filtrerFournisseurs()" placeholder="Recherche..." class="h-8 pl-8 pr-3 w-36 sm:w-48 bg-slate-50 dark:bg-[#09151F] border border-slate-300 dark:border-[#1e384d] rounded-full text-xs text-slate-900 dark:text-white focus:outline-none focus:border-[#FF6A00]">
                </div>

                <!-- FILTRE TYPE -->
                <div class="relative">
                    <select id="typeFilter" onchange="filtrerFournisseurs()" class="h-8 pl-2.5 pr-7 bg-slate-50 dark:bg-[#09151F] border border-slate-300 dark:border-[#1e384d] rounded-full text-xs font-bold text-slate-800 dark:text-slate-200 focus:outline-none appearance-none cursor-pointer">
                        <option value="TOUS">Tous</option>
                        <option value="Carburant">Carburant</option>
                        <option value="Lubrifiant">Lubrifiant</option>
                        <option value="Services">Services</option>
                        <option value="Grossiste">Grossiste</option>
                    </select>
                    <i data-lucide="chevron-down" class="w-3 h-3 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none"></i>
                </div>

                <!-- TRI -->
                <div class="relative">
                    <select id="sortFilter" onchange="trierFournisseurs()" class="h-8 pl-2.5 pr-7 bg-slate-50 dark:bg-[#09151F] border border-slate-300 dark:border-[#1e384d] rounded-full text-xs font-bold text-slate-800 dark:text-slate-200 focus:outline-none appearance-none cursor-pointer">
                        <option value="nom-asc">Nom (A-Z)</option>
                        <option value="nom-desc">Nom (Z-A)</option>
                    </select>
                    <i data-lucide="chevron-down" class="w-3 h-3 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none"></i>
                </div>

                <!-- BOUTON NOUVEAU ORANGE -->
                <button onclick="document.getElementById('modal-nouveau-f').classList.remove('hidden')" class="h-8 px-4 rounded-full bg-[#FF6A00] hover:bg-[#e55f00] text-white font-black text-xs inline-flex items-center gap-1.5 shadow-md active:scale-95 transition">
                    <i data-lucide="plus" class="w-3.5 h-3.5 stroke-[3]"></i>
                    <span>NOUVEAU</span>
                </button>
            </div>

        </div>

        <!-- GRILLE DES DOSSIERS FOURNISSEURS -->
        <div id="suppliersGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {cards_html if cards_html else '<div class="col-span-full text-center py-12 text-slate-500 italic">Aucun fournisseur enregistré.</div>'}
        </div>

    </div>

    {modal_nouveau_html}
    {modales_rapides_html}

    <!-- SCRIPTS INTERACTIFS -->
    <script>
        function toggleMenu(menuId, event) {{
            event.stopPropagation();
            const targetMenu = document.getElementById(menuId);
            const isHidden = targetMenu.classList.contains('hidden');
            document.querySelectorAll('.card-dropdown').forEach(m => m.classList.add('hidden'));
            if (isHidden) {{
                targetMenu.classList.remove('hidden');
            }}
        }}

        document.addEventListener('click', function(e) {{
            if (!e.target.closest('.card-dropdown')) {{
                document.querySelectorAll('.card-dropdown').forEach(m => m.classList.add('hidden'));
            }}
        }});

        function filtrerFournisseurs() {{
            const search = document.getElementById('searchInput').value.toLowerCase();
            const filterType = document.getElementById('typeFilter').value;
            const cards = document.querySelectorAll('.supplier-card');

            cards.forEach(card => {{
                const name = card.getAttribute('data-name');
                const code = card.getAttribute('data-code');
                const type = card.getAttribute('data-type');

                const matchSearch = name.includes(search) || code.includes(search);
                const matchType = (filterType === 'TOUS' || type === filterType);

                if (matchSearch && matchType) {{
                    card.style.display = '';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        function trierFournisseurs() {{
            const sort = document.getElementById('sortFilter').value;
            const grid = document.getElementById('suppliersGrid');
            const cards = Array.from(grid.querySelectorAll('.supplier-card'));

            cards.sort((a, b) => {{
                const nameA = a.getAttribute('data-name');
                const nameB = b.getAttribute('data-name');
                if (sort === 'nom-asc') return nameA.localeCompare(nameB);
                return nameB.localeCompare(nameA);
            }});

            cards.forEach(card => grid.appendChild(card));
        }}

        function calcAchatTotal() {{
            const vol = parseFloat(document.getElementById('achat-vol').value) || 0;
            const pu = parseFloat(document.getElementById('achat-pu').value) || 0;
            if (vol > 0 && pu > 0) {{
                document.getElementById('achat-total').value = (vol * pu).toFixed(2);
            }}
        }}

        function ouvrirAchatDirect(id, nom) {{
            document.getElementById('achat-f-id').value = id;
            document.getElementById('achat-f-nom').innerText = nom;
            document.getElementById('modal-achat').classList.remove('hidden');
        }}

        function ouvrirPaiementDirect(id, nom, dette) {{
            document.getElementById('pay-f-id').value = id;
            document.getElementById('pay-f-nom').innerText = nom;
            document.getElementById('pay-f-dette').innerText = (parseFloat(dette) || 0).toLocaleString('fr-FR', {{minimumFractionDigits: 2}}) + ' MAD';
            document.getElementById('modal-reglement').classList.remove('hidden');
        }}

        function ouvrirModifierDirect(id, code, nom, type, statut, tel, email) {{
            document.getElementById('mod-id').value = id;
            document.getElementById('mod-code').value = code;
            document.getElementById('mod-nom').value = nom;
            document.getElementById('mod-type').value = type;
            document.getElementById('mod-statut').value = statut;
            document.getElementById('mod-tel').value = tel;
            document.getElementById('mod-email').value = email;
            document.getElementById('modal-modifier-f').classList.remove('hidden');
        }}

        function ouvrirSupprimerDirect(id, nom) {{
            document.getElementById('sup-id').value = id;
            document.getElementById('sup-nom-text').innerText = 'Fournisseur : ' + nom;
            document.getElementById('modal-supprimer-f').classList.remove('hidden');
        }}
    </script>
    """
    return HTMLResponse(layout(content, active_tab="fournisseurs", request=request))

# =============================================================================
# ROUTES POST (Inchangées et 100% compatibles)
# =============================================================================
@router.post("/fournisseurs/nouveau")
async def action_nouveau_fournisseur(
    code: str = Form(None),
    nom: str = Form(...),
    type_fournisseur: str = Form("Carburant"),
    contact_nom: str = Form(""),
    telephone: str = Form(""),
    email: str = Form(""),
    adresse: str = Form(""),
    conditions_paiement: str = Form(""),
    solde_initial: float = Form(0.0),
    montant_fidelite: float = Form(0.0),
    doc_categorie: str = Form("RC"),
    doc_description: str = Form(""),
    notes: str = Form(""),
    fichier_doc: UploadFile = File(None)
):
    clean_code = (code or "").strip().upper()
    if not clean_code:
        clean_code = database.generer_prochain_code_fournisseur()

    doc_filename = ""
    if fichier_doc and fichier_doc.filename:
        safe_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{fichier_doc.filename.replace(' ', '_')}"
        dest_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(fichier_doc.file, buffer)
        doc_filename = f"/static/uploads/fournisseurs/{safe_name}"

    new_id = database.ajouter_fournisseur(
        code=clean_code,
        nom=nom.strip(),
        type_f=type_fournisseur,
        contact=contact_nom.strip(),
        tel=telephone.strip(),
        email=email.strip(),
        adresse=adresse.strip(),
        cond=conditions_paiement.strip(),
        solde_init=solde_initial,
        montant_fidelite=montant_fidelite or 0.0,
        document=doc_filename,
        doc_categorie=doc_categorie,
        doc_description=doc_description.strip(),
        notes=notes.strip(),
        statut="Actif"
    )
    return RedirectResponse("/fournisseurs", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/fournisseurs/modifier")
async def action_modifier_fournisseur(
    fournisseur_id: int = Form(...),
    code: str = Form(...),
    nom: str = Form(...),
    type_fournisseur: str = Form("Carburant"),
    contact_nom: str = Form(""),
    telephone: str = Form(""),
    email: str = Form(""),
    adresse: str = Form(""),
    conditions_paiement: str = Form(""),
    solde_initial: float = Form(0.0),
    statut: str = Form("Actif")
):
    database.modifier_fournisseur(
        f_id=fournisseur_id,
        code=code.strip().upper(),
        nom=nom.strip(),
        type_f=type_fournisseur,
        contact=contact_nom.strip(),
        tel=telephone.strip(),
        email=email.strip(),
        adresse=adresse.strip(),
        cond=conditions_paiement.strip(),
        solde_init=solde_initial,
        statut=statut
    )
    return RedirectResponse("/fournisseurs", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/fournisseurs/supprimer")
async def action_supprimer_fournisseur(fournisseur_id: int = Form(...)):
    database.supprimer_fournisseur(fournisseur_id)
    return RedirectResponse("/fournisseurs", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/fournisseurs/achat")
async def action_ajout_achat(
    fournisseur_id: int = Form(...),
    date: str = Form(...),
    reference_bl: str = Form(...),
    produit: str = Form("Diesel (Gasoil 10ppm)"),
    volume: float = Form(0.0),
    prix_unitaire: float = Form(0.0),
    montant_total: float = Form(...),
    observations: str = Form("")
):
    database.ajouter_achat(
        fournisseur_id=fournisseur_id,
        date=date,
        montant_total=montant_total,
        reference_bl=reference_bl.strip(),
        produit=produit,
        volume_litres=volume,
        prix_unitaire=prix_unitaire,
        observations=observations.strip()
    )
    return RedirectResponse(f"/fournisseurs?id={fournisseur_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/fournisseurs/reglement")
async def action_ajout_reglement(
    fournisseur_id: int = Form(...),
    date: str = Form(...),
    reference_paiement: str = Form(...),
    mode_paiement: str = Form(...),
    montant: float = Form(...),
    banque: str = Form(""),
    observations: str = Form("")
):
    database.ajouter_reglement_fournisseur(
        fournisseur_id=fournisseur_id,
        date=date,
        reference=reference_paiement.strip(),
        mode=mode_paiement,
        montant=montant,
        banque=banque.strip(),
        obs=observations.strip()
    )
    return RedirectResponse(f"/fournisseurs?id={fournisseur_id}", status_code=status.HTTP_303_SEE_OTHER)