import html
import json

def vue_saisie_poste_employe(
    nom_operateur: str, 
    heure_debut_iso: str, 
    total_theorique: float, 
    clients_data: list, 
    prix_ssp: float,
    prix_go: float,
    message_alerte: str = ""
) -> str:
    
    # Ordre des 9 coupures
    coupures = [
        {"v": 200, "label": "200 DH"},
        {"v": 100, "label": "100 DH"},
        {"v": 50,  "label": "50 DH"},
        {"v": 20,  "label": "20 DH"},
        {"v": 10,  "label": "10 DH"},
        {"v": 5,   "label": "5 DH"},
        {"v": 2,   "label": "2 DH"},
        {"v": 1,   "label": "1 DH"},
        {"v": 0.5, "label": "0.50 DH"}
    ]

    coupures_html = "".join([f"""
    <div class="glass-input-card rounded-2xl p-2.5 flex flex-col justify-between transition-all duration-200">
        <div class="flex justify-between items-center mb-1">
            <span class="text-xs font-black text-white tracking-wide">{c['label']}</span>
            <span class="text-[11px] font-mono font-bold text-[#8A9AA8]" id="sub_c_{str(c['v']).replace('.','_')}">0.00 DH</span>
        </div>
        <input type="number" min="0" placeholder="0" data-val="{c['v']}" name="qte_{str(c['v']).replace('.','_')}" 
               oninput="calculerCaisseAgent()" 
               class="agent-input w-full text-center bg-black/40 border border-white/15 focus:border-[#FF951A] rounded-xl py-1.5 font-mono font-black text-lg text-white outline-none transition">
    </div>
    """ for c in coupures])

    clients_data_json = json.dumps(clients_data)

    return f"""<!DOCTYPE html>
<html lang="fr" class="dark h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>PetroLaz - Caisse Pompiste</title>
    
    <script>
        if (localStorage.theme === 'light') {{
            document.documentElement.classList.remove('dark');
        }} else {{
            document.documentElement.classList.add('dark');
        }}
    </script>

    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@600;700;800;900&display=swap" rel="stylesheet">
    
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #04080e;
            /* Arrière-plan transparent laissant la station parfaitement visible */
            background-image: 
                linear-gradient(180deg, rgba(4, 8, 14, 0.25) 0%, rgba(4, 8, 14, 0.40) 100%),
                url('/static/station_bg_sombre.png');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            color: #ffffff;
        }}
        html:not(.dark) body {{
            background-color: #f1f5f9;
            background-image: linear-gradient(180deg, rgba(240, 244, 248, 0.4) 0%, rgba(226, 232, 240, 0.7) 100%), url('/static/station_bg_Claire.jpg');
            color: #0f172a;
        }}
        .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
        input[type="number"]::-webkit-inner-spin-button, 
        input[type="number"]::-webkit-outer-spin-button {{ -webkit-appearance: none; margin: 0; }}
        input[type="number"] {{ -moz-appearance: textfield; }}
        
        /* Ultra-transparence verre dépoli */
        .glass-card {{
            background: rgba(8, 16, 26, 0.28);
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
            border: 1px solid rgba(255, 255, 255, 0.14);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.25);
        }}

        .glass-input-card {{
            background: rgba(6, 12, 20, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }}
        .glass-input-card:hover {{
            border-color: rgba(255, 149, 26, 0.6);
        }}

        .total-neon {{
            color: #00E5FF;
            text-shadow: 0 0 14px rgba(0, 229, 255, 0.75), 0 0 28px rgba(0, 229, 255, 0.35);
        }}

        .total-green-neon {{
            color: #00E676;
            text-shadow: 0 0 12px rgba(0, 230, 118, 0.75);
        }}

        ::-webkit-scrollbar {{
            width: 4px;
        }}
        ::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
        }}
    </style>
</head>
<body class="min-h-full flex flex-col select-none antialiased">

    <!-- ========================================================= -->
    <!-- 1. BARRE DE NAVIGATION (HEADER PRO SEPARÉ) -->
    <!-- ========================================================= -->
    <header class="w-full bg-[#050c14]/75 border-b border-white/10 px-4 sm:px-6 py-2.5 backdrop-blur-md sticky top-0 z-40">
        <div class="w-full max-w-[98%] mx-auto flex flex-wrap items-center justify-between gap-3">
            
            <!-- Logo & Opérateur -->
            <div class="flex items-center gap-3">
                <div class="flex items-center gap-2 pr-3 border-r border-white/10">
                    <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#FF951A] to-amber-400 flex items-center justify-center shadow-[0_0_12px_rgba(255,149,26,0.4)]">
                        <i data-lucide="fuel" class="w-4 h-4 text-slate-950 stroke-[2.5]"></i>
                    </div>
                    <span class="font-black text-sm tracking-wider text-white">PETRO<span class="text-[#FF951A]">LAZ</span></span>
                </div>

                <!-- Badge Agent actif -->
                <div class="flex items-center gap-2 bg-black/40 border border-white/10 px-3 py-1 rounded-xl">
                    <span class="w-6 h-6 rounded-lg bg-[#FF951A] text-slate-950 text-[10px] font-black flex items-center justify-center">
                        {nom_operateur[:2]}
                    </span>
                    <span class="text-xs font-black tracking-wider text-white uppercase">{nom_operateur}</span>
                    <span class="w-2 h-2 rounded-full bg-[#00E676] shadow-[0_0_8px_#00E676] ml-0.5"></span>
                </div>
            </div>

            <!-- Prix des Carburants -->
            <div class="flex items-center gap-2.5">
                <div class="flex items-center gap-2 bg-black/40 border border-white/10 px-3 py-1 rounded-xl font-mono text-xs">
                    <span class="w-2.5 h-2.5 rounded-full bg-[#FF951A] shadow-[0_0_8px_#FF951A]"></span>
                    <span class="text-white font-bold text-[11px] uppercase tracking-wide">GAZOIL 10 :</span>
                    <span class="font-black text-[#FF951A] bg-black/50 px-2 py-0.5 rounded border border-white/10">{prix_go:.2f} DH</span>
                </div>

                <div class="flex items-center gap-2 bg-black/40 border border-white/10 px-3 py-1 rounded-xl font-mono text-xs">
                    <span class="w-2.5 h-2.5 rounded-full bg-[#00E676] shadow-[0_0_8px_#00E676]"></span>
                    <span class="text-white font-bold text-[11px] uppercase tracking-wide">SSP :</span>
                    <span class="font-black text-[#00E676] bg-black/50 px-2 py-0.5 rounded border border-white/10">{prix_ssp:.2f} DH</span>
                </div>
            </div>

            <!-- Horloge + Bouton Mode Sombre/Clair + Déconnexion ROUGE -->
            <div class="flex items-center gap-3">
                <div class="hidden lg:flex items-center gap-2 text-xs font-mono bg-black/40 border border-white/10 px-3 py-1.5 rounded-xl">
                    <i data-lucide="clock" class="w-3.5 h-3.5 text-[#00E5FF]"></i>
                    <span id="live_date_str" class="text-white font-bold">--/--/----</span>
                    <span class="text-white/30">•</span>
                    <span id="live_clock_str" class="text-white font-black tracking-wider">00:00:00</span>
                </div>

                <!-- Bouton Thème Sombre / Clair -->
                <button type="button" onclick="toggleTheme()" class="w-9 h-9 rounded-xl bg-black/40 border border-white/15 hover:border-white/30 text-slate-200 flex items-center justify-center transition cursor-pointer" title="Basculer thème">
                    <i data-lucide="sun" class="w-4 h-4 hidden dark:block text-amber-400"></i>
                    <i data-lucide="moon" class="w-4 h-4 block dark:hidden text-cyan-400"></i>
                </button>

                <!-- Bouton Déconnexion Rouge Plein -->
                <a href="/logout" class="bg-[#FF1744] hover:bg-[#d50000] active:scale-95 text-white font-black px-4 py-1.5 rounded-xl text-xs uppercase tracking-wider transition flex items-center gap-1.5 shadow-[0_0_15px_rgba(255,23,68,0.4)]">
                    <i data-lucide="log-out" class="w-3.5 h-3.5"></i>
                    <span>DÉCONNEXION</span>
                </a>
            </div>
        </div>
    </header>

    <!-- ========================================================= -->
    <!-- 2. CORPS PRINCIPAL LARGE (FULL WIDTH ÉLARGIE) -->
    <!-- ========================================================= -->
    <main class="flex-1 w-full max-w-[98%] mx-auto p-3 sm:p-4 flex flex-col justify-between">
        
        {message_alerte}

        <form action="/employe/cloturer" method="post" onsubmit="return validerAvantSoumission();" class="flex-1 flex flex-col justify-between space-y-3">
            <input type="hidden" name="operateur" value="{nom_operateur}">
            <input type="hidden" name="fusion" value="{total_theorique}">
            <input type="hidden" id="credits_agent_json" name="credits_json" value="[]">
            <input type="hidden" id="charges_agent_json" name="charges_json" value="[]">
            <input type="hidden" id="mode_especes" name="mode_especes" value="detaille">

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-3.5 flex-1 items-stretch">
                
                <!-- ============================================== -->
                <!-- COLONNE GAUCHE (6 COLS) : ESPÈCES & TPE EN BAS -->
                <!-- ============================================== -->
                <div class="lg:col-span-6 glass-card rounded-2xl p-4 flex flex-col justify-between">
                    <div>
                        <!-- Header Espèces -->
                        <div class="flex justify-between items-center pb-2.5 border-b border-white/10 mb-3">
                            <div class="flex items-center gap-2">
                                <span class="text-xs font-black uppercase tracking-wider text-white">ESPÈCES</span>
                                <div class="inline-flex items-center bg-black/40 border border-white/10 p-0.5 rounded-lg text-[10px] font-black">
                                    <button type="button" id="btn_mode_detaille" onclick="basculerModeEspeces('detaille')" class="px-2.5 py-0.5 rounded bg-white/20 text-white">COUPURES</button>
                                    <button type="button" id="btn_mode_direct" onclick="basculerModeEspeces('direct')" class="px-2.5 py-0.5 rounded text-[#8A9AA8] hover:text-white">DIRECT</button>
                                </div>
                            </div>
                            <span class="text-xs font-mono font-black text-[#00E676] bg-[#00E676]/10 border border-[#00E676]/30 px-2.5 py-0.5 rounded-lg" id="txt_total_especes_sub">0.00 DH</span>
                        </div>

                        <!-- Mode Direct -->
                        <div id="zone_especes_directe" class="hidden mb-3 p-4 rounded-xl bg-black/40 border border-white/10 text-center">
                            <label class="block text-[11px] font-black text-white uppercase mb-1.5 tracking-wider">TOTAL ESPÈCES (DH)</label>
                            <input type="number" step="0.01" id="especes_saisie_directe" name="especes_saisie_directe" placeholder="0" oninput="calculerCaisseAgent()" onblur="formaterChampDecimale(this)"
                                   class="w-full max-w-xs text-center px-3 py-2 bg-black/60 border border-white/20 focus:border-[#00E676] rounded-xl font-mono font-black text-2xl text-[#00E676] outline-none">
                        </div>

                        <!-- Grille Coupures 3x3 -->
                        <div id="zone_especes_detaille" class="grid grid-cols-3 gap-2.5">
                            {coupures_html}
                        </div>

                        <!-- BLOC TPE POSITIONNÉ EN BAS DU BLOC ESPÈCES -->
                        <div class="mt-4 pt-3 border-t border-white/10">
                            <div class="flex items-center justify-between mb-1.5">
                                <span class="text-xs font-black uppercase text-white tracking-wider flex items-center gap-1.5">
                                    <i data-lucide="credit-card" class="w-3.5 h-3.5 text-[#00E5FF]"></i>
                                    <span>TPE (CARTE BANCAIRE)</span>
                                </span>
                            </div>
                            <div class="flex items-center gap-2 bg-black/40 border border-white/10 focus-within:border-[#00E5FF] rounded-xl px-3 py-1.5 transition">
                                <span class="text-xs text-[#8A9AA8] font-bold flex-1">Empreinte TPE</span>
                                <input type="number" step="0.01" id="agent_tpe" name="tpe" placeholder="0" oninput="calculerCaisseAgent()" onblur="formaterChampDecimale(this)"
                                       class="w-32 text-right bg-transparent font-mono font-black text-base text-white outline-none">
                                <span class="text-xs font-mono font-black text-white">DH</span>
                            </div>
                        </div>
                    </div>

                    <!-- Pied Total Espèces -->
                    <div class="mt-4 pt-3 border-t border-white/10 flex items-center justify-between">
                        <span class="text-xs font-black uppercase text-white tracking-wider">TOTAL ESPÈCES</span>
                        <span class="text-xl font-mono font-black total-green-neon" id="txt_total_especes">0.00 DH</span>
                    </div>
                </div>

                <!-- ============================================== -->
                <!-- COLONNE DROITE (6 COLS) : BONS & DÉPENSES -->
                <!-- ============================================== -->
                <div class="lg:col-span-6 flex flex-col justify-between gap-3">
                    
                    <!-- 1. BONS CRÉDITS (HAUT) -->
                    <div class="glass-card rounded-2xl p-4 flex flex-col justify-between flex-1">
                        <div>
                            <div class="flex justify-between items-center pb-2.5 border-b border-white/10 mb-2.5">
                                <span class="text-xs font-black uppercase tracking-wider text-white">CRÉDITS & BONS</span>
                                <button type="button" onclick="ouvrirModalCredit()" class="px-3.5 py-1.5 rounded-xl bg-[#FF1744] hover:brightness-110 active:scale-95 transition text-white font-black text-xs uppercase tracking-wider shadow-md">
                                    AJOUTER BON
                                </button>
                            </div>

                            <div id="liste_credits_agent" class="space-y-1.5 overflow-y-auto max-h-[145px] pr-1">
                                <div class="text-center py-6 text-xs text-[#8A9AA8] italic">Aucun crédit ajouté.</div>
                            </div>
                        </div>

                        <div class="mt-2.5 pt-2 border-t border-white/10 flex items-center justify-between text-xs font-bold text-white">
                            <span>TOTAL CRÉDITS :</span>
                            <span class="font-mono text-[#FF1744] text-sm font-black" id="txt_total_credits">0.00 DH</span>
                        </div>
                    </div>

                    <!-- 2. DÉPENSES (BAS) -->
                    <div class="glass-card rounded-2xl p-4 flex flex-col justify-between flex-1">
                        <div>
                            <div class="flex justify-between items-center pb-2.5 border-b border-white/10 mb-2.5">
                                <span class="text-xs font-black uppercase tracking-wider text-white">DÉPENSES</span>
                                <button type="button" onclick="ouvrirModalCharge()" class="px-3.5 py-1.5 rounded-xl bg-[#FF951A] hover:brightness-110 active:scale-95 transition text-slate-950 font-black text-xs uppercase tracking-wider shadow-md">
                                    AJOUTER DÉPENSE
                                </button>
                            </div>

                            <div id="liste_charges_agent" class="space-y-1.5 overflow-y-auto max-h-[130px] pr-1">
                                <div class="text-center py-5 text-xs text-[#8A9AA8] italic">Aucune dépense ajoutée.</div>
                            </div>
                        </div>

                        <div class="mt-2.5 pt-2 border-t border-white/10 flex items-center justify-between text-xs font-bold text-white">
                            <span>TOTAL DÉPENSES :</span>
                            <span class="font-mono text-[#FF951A] text-sm font-black" id="txt_total_charges">0.00 DH</span>
                        </div>
                    </div>

                    <!-- 3. RÉCAPITULATIF TOTAL DÉCLARÉ (CYAN + BOUTON ORANGE) -->
                    <div class="glass-card rounded-2xl p-4 flex items-center justify-between gap-4 border border-white/15">
                        <div>
                            <div class="text-xs font-black uppercase tracking-wider text-white">TOTAL DÉCLARÉ</div>
                            <div class="text-[10px] text-[#8A9AA8] font-mono tracking-tight">(CASH + TPE + BONS - DÉPENSES)</div>
                            <div class="total-neon font-mono font-black text-2xl sm:text-3xl mt-0.5" id="txt_total_agent">
                                0.00 DH
                            </div>
                        </div>

                        <button type="submit" class="px-8 py-3.5 rounded-xl bg-[#FF951A] hover:brightness-110 active:scale-95 transition text-slate-950 font-black text-xs uppercase tracking-wider shadow-[0_4px_20px_rgba(255,149,26,0.4)] flex items-center gap-2">
                            <span>VALIDER CLÔTURE</span>
                            <i data-lucide="check" class="w-4 h-4 stroke-[3]"></i>
                        </button>
                    </div>

                </div>
            </div>
        </form>
    </main>

    <!-- ========================================================= -->
    <!-- MODALE 1 : BON DE CRÉDIT -->
    <!-- ========================================================= -->
    <div id="modal_credit" class="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-3 hidden">
        <div class="glass-card w-full max-w-sm p-5 rounded-2xl shadow-2xl space-y-3.5 border border-white/20 bg-[#070e17]/90">
            
            <div class="flex items-center justify-between pb-2 border-b border-white/10">
                <h3 class="text-xs font-black text-white uppercase tracking-wider">BON DE CRÉDIT</h3>
                <button type="button" onclick="fermerModalCredit()" class="text-white/60 hover:text-white font-bold text-lg leading-none">✕</button>
            </div>

            <!-- Type Enregistré / Particulier -->
            <div class="flex items-center gap-1.5 bg-black/50 p-1 rounded-xl border border-white/10">
                <button type="button" id="btn_modal_type_enreg" onclick="basculerTypeClientModal(false)" class="flex-1 py-1.5 rounded-lg text-xs font-black bg-white/20 text-white">ENREGISTRÉ</button>
                <button type="button" id="btn_modal_type_part" onclick="basculerTypeClientModal(true)" class="flex-1 py-1.5 rounded-lg text-xs font-black text-[#8A9AA8] hover:text-white">PARTICULIER</button>
            </div>

            <div id="bloc_client_select">
                <label class="block text-[11px] font-black text-white uppercase mb-1">CLIENT</label>
                <select id="mc_client_id" onchange="surChangementClientModal()" class="w-full bg-black/60 border border-white/20 rounded-xl px-3 py-2 text-xs font-bold text-white outline-none focus:border-[#00E5FF]">
                    <option value="">-- CHOISIR CLIENT --</option>
                </select>
            </div>

            <div id="bloc_client_nom_libre" class="hidden">
                <label class="block text-[11px] font-black text-white uppercase mb-1">NOM CLIENT</label>
                <input type="text" id="mc_nom_libre" placeholder="Nom complet..." class="w-full bg-black/60 border border-white/20 rounded-xl px-3 py-2 text-xs font-bold text-white outline-none focus:border-[#00E5FF]">
            </div>

            <div>
                <label class="block text-[11px] font-black text-white uppercase mb-1">MATRICULE</label>
                <input type="text" id="mc_matricule" placeholder="12345-A-50" class="w-full bg-black/60 border border-white/20 rounded-xl px-3 py-1.5 text-xs font-mono font-bold uppercase text-white outline-none focus:border-[#00E5FF]">
            </div>

            <div>
                <label class="block text-[11px] font-black text-white uppercase mb-1">PRODUIT</label>
                <select id="mc_carb" onchange="recalculerCreditAuto('litres')" class="w-full bg-black/60 border border-white/20 rounded-xl px-3 py-1.5 text-xs font-bold text-white outline-none focus:border-[#00E5FF]">
                    <option value="GAZOIL 10" data-prix="{prix_go}">GAZOIL 10 ({prix_go:.2f} DH)</option>
                    <option value="SSP" data-prix="{prix_ssp}">SSP ({prix_ssp:.2f} DH)</option>
                </select>
            </div>

            <div class="grid grid-cols-2 gap-2 bg-black/50 p-2.5 rounded-xl border border-white/10">
                <div>
                    <label class="block text-[10px] font-black text-[#00E5FF] uppercase mb-1">LITRES</label>
                    <input type="number" step="0.01" id="mc_litres" placeholder="0" oninput="recalculerCreditAuto('litres')" onblur="formaterChampDecimale(this)"
                           class="w-full text-center bg-black/70 border border-white/20 focus:border-[#00E5FF] rounded-lg py-1.5 font-mono font-black text-sm text-[#00E5FF] outline-none">
                </div>
                <div>
                    <label class="block text-[10px] font-black text-[#FF1744] uppercase mb-1">MONTANT (DH)</label>
                    <input type="number" step="0.01" id="mc_montant" placeholder="0" oninput="recalculerCreditAuto('montant')" onblur="formaterChampDecimale(this)"
                           class="w-full text-center bg-black/70 border border-white/20 focus:border-[#FF1744] rounded-lg py-1.5 font-mono font-black text-sm text-[#FF1744] outline-none">
                </div>
            </div>

            <div class="pt-2 flex justify-end gap-2.5">
                <button type="button" onclick="fermerModalCredit()" class="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-bold">ANNULER</button>
                <button type="button" onclick="validerAjoutCreditModal()" class="px-6 py-2 rounded-xl bg-[#FF1744] hover:brightness-110 text-white font-black text-xs uppercase tracking-wider shadow-md">
                    VALIDER
                </button>
            </div>
        </div>
    </div>

    <!-- ========================================================= -->
    <!-- MODALE 2 : NOUVELLE DÉPENSE -->
    <!-- ========================================================= -->
    <div id="modal_charge" class="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-3 hidden">
        <div class="glass-card w-full max-w-sm p-5 rounded-2xl shadow-2xl space-y-3.5 border border-white/20 bg-[#070e17]/90">
            
            <div class="flex items-center justify-between pb-2 border-b border-white/10">
                <h3 class="text-xs font-black text-white uppercase tracking-wider">NOUVELLE DÉPENSE</h3>
                <button type="button" onclick="fermerModalCharge()" class="text-white/60 hover:text-white font-bold text-lg leading-none">✕</button>
            </div>

            <div>
                <label class="block text-[11px] font-black text-white uppercase mb-1">BÉNÉFICIAIRE</label>
                <input type="text" id="mch_beneficiaire" placeholder="Nom ou entité..." class="w-full bg-black/60 border border-white/20 rounded-xl px-3 py-2 text-xs font-bold text-white outline-none focus:border-[#FF951A]">
            </div>

            <div>
                <label class="block text-[11px] font-black text-white uppercase mb-1">MOTIF</label>
                <input type="text" id="mch_motif" placeholder="Justificatif..." class="w-full bg-black/60 border border-white/20 rounded-xl px-3 py-2 text-xs font-bold text-white outline-none focus:border-[#FF951A]">
            </div>

            <div>
                <label class="block text-[11px] font-black text-[#FF951A] uppercase mb-1">MONTANT (DH)</label>
                <input type="number" step="0.01" id="mch_montant" placeholder="0" onblur="formaterChampDecimale(this)"
                       class="w-full text-right bg-black/60 border border-white/20 focus:border-[#FF951A] rounded-xl px-3 py-2 font-mono font-black text-lg text-[#FF951A] outline-none">
            </div>

            <div class="pt-2 flex justify-end gap-2.5">
                <button type="button" onclick="fermerModalCharge()" class="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-bold">ANNULER</button>
                <button type="button" onclick="validerAjoutChargeModal()" class="px-6 py-2 rounded-xl bg-[#FF951A] hover:brightness-110 text-slate-950 font-black text-xs uppercase tracking-wider shadow-md">
                    VALIDER
                </button>
            </div>
        </div>
    </div>

    <!-- JAVASCRIPT COMPLET & CALCULS TEMPS RÉEL -->
    <script>
        const CLIENTS_LISTE = {clients_data_json};
        const PRIX_SSP = {prix_ssp};
        const PRIX_GO = {prix_go};

        let creditsAgent = [];
        let chargesAgent = [];
        let modeEspecesActuel = 'detaille';
        let modalCreditIsParticulier = false;

        function updateClock() {{
            const now = new Date();
            const dateOptions = {{ weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' }};
            const dateStr = now.toLocaleDateString('fr-FR', dateOptions);

            const hrs = String(now.getHours()).padStart(2, '0');
            const mins = String(now.getMinutes()).padStart(2, '0');
            const secs = String(now.getSeconds()).padStart(2, '0');
            const timeStr = `${{hrs}}:${{mins}}:${{secs}}`;

            if (document.getElementById('live_date_str')) document.getElementById('live_date_str').innerText = dateStr;
            if (document.getElementById('live_clock_str')) document.getElementById('live_clock_str').innerText = timeStr;
        }}
        setInterval(updateClock, 1000);
        updateClock();

        function toggleTheme() {{
            const isDark = document.documentElement.classList.contains('dark');
            if (isDark) {{
                document.documentElement.classList.remove('dark');
                localStorage.setItem('theme', 'light');
            }} else {{
                document.documentElement.classList.add('dark');
                localStorage.setItem('theme', 'dark');
            }}
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }}

        function basculerModeEspeces(mode) {{
            modeEspecesActuel = mode;
            document.getElementById('mode_especes').value = mode;

            const btnDet = document.getElementById('btn_mode_detaille');
            const btnDir = document.getElementById('btn_mode_direct');
            const zoneDet = document.getElementById('zone_especes_detaille');
            const zoneDir = document.getElementById('zone_especes_directe');

            if (mode === 'direct') {{
                btnDir.className = "px-2.5 py-0.5 rounded bg-white/20 text-white font-bold";
                btnDet.className = "px-2.5 py-0.5 rounded text-[#8A9AA8] hover:text-white font-bold";
                zoneDir.classList.remove('hidden');
                zoneDet.classList.add('hidden');
            }} else {{
                btnDet.className = "px-2.5 py-0.5 rounded bg-white/20 text-white font-bold";
                btnDir.className = "px-2.5 py-0.5 rounded text-[#8A9AA8] hover:text-white font-bold";
                zoneDet.classList.remove('hidden');
                zoneDir.classList.add('hidden');
            }}
            calculerCaisseAgent();
        }}

        function formaterChampDecimale(inp) {{
            if (!inp || !inp.value || inp.value.trim() === '') return;
            const val = parseFloat(inp.value);
            if (!isNaN(val)) {{
                inp.value = val.toFixed(2);
            }}
            calculerCaisseAgent();
        }}

        function initialiserSelectClients() {{
            const sel = document.getElementById('mc_client_id');
            sel.innerHTML = '<option value="">-- CHOISIR CLIENT --</option>';
            CLIENTS_LISTE.forEach(c => {{
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.text = `${{c.nom}} (${{c.code}})`;
                sel.appendChild(opt);
            }});
        }}

        function ouvrirModalCredit() {{
            initialiserSelectClients();
            modalCreditIsParticulier = false;
            basculerTypeClientModal(false);
            document.getElementById('mc_matricule').value = '';
            document.getElementById('mc_litres').value = '';
            document.getElementById('mc_montant').value = '';
            document.getElementById('modal_credit').classList.remove('hidden');
        }}

        function fermerModalCredit() {{
            document.getElementById('modal_credit').classList.add('hidden');
        }}

        function basculerTypeClientModal(isPart) {{
            modalCreditIsParticulier = isPart;
            const btnEnreg = document.getElementById('btn_modal_type_enreg');
            const btnPart = document.getElementById('btn_modal_type_part');
            const blocSel = document.getElementById('bloc_client_select');
            const blocNom = document.getElementById('bloc_client_nom_libre');

            if (isPart) {{
                btnPart.className = "flex-1 py-1.5 rounded-lg text-xs font-bold bg-[#FF951A] text-slate-950";
                btnEnreg.className = "flex-1 py-1.5 rounded-lg text-xs font-bold text-[#8A9AA8] hover:text-white";
                blocNom.classList.remove('hidden');
                blocSel.classList.add('hidden');
                document.getElementById('mc_matricule').value = '';
            }} else {{
                btnEnreg.className = "flex-1 py-1.5 rounded-lg text-xs font-bold bg-white/20 text-white";
                btnPart.className = "flex-1 py-1.5 rounded-lg text-xs font-bold text-[#8A9AA8] hover:text-white";
                blocSel.classList.remove('hidden');
                blocNom.classList.add('hidden');
                surChangementClientModal();
            }}
        }}

        function surChangementClientModal() {{
            const cid = document.getElementById('mc_client_id').value;
            if (!cid) return;
            const c = CLIENTS_LISTE.find(x => String(x.id) === String(cid));
            if (c && c.matricule) {{
                document.getElementById('mc_matricule').value = c.matricule;
            }}
        }}

        function recalculerCreditAuto(source) {{
            const carbSel = document.getElementById('mc_carb');
            const opt = carbSel.options[carbSel.selectedIndex];
            const prix = parseFloat(opt.getAttribute('data-prix')) || (carbSel.value === 'SSP' ? PRIX_SSP : PRIX_GO);

            const inpLitres = document.getElementById('mc_litres');
            const inpMontant = document.getElementById('mc_montant');

            if (source === 'litres') {{
                const lit = parseFloat(inpLitres.value) || 0;
                if (lit > 0) {{
                    inpMontant.value = (lit * prix).toFixed(2);
                }} else {{
                    inpMontant.value = '';
                }}
            }} else if (source === 'montant') {{
                const mnt = parseFloat(inpMontant.value) || 0;
                if (mnt > 0) {{
                    inpLitres.value = (mnt / prix).toFixed(2);
                }} else {{
                    inpLitres.value = '';
                }}
            }}
        }}

        function validerAjoutCreditModal() {{
            let nomFinal = "";
            let cid = null;

            if (modalCreditIsParticulier) {{
                nomFinal = document.getElementById('mc_nom_libre').value.trim();
                if (!nomFinal) return alert("Saisir nom.");
            }} else {{
                const cSelect = document.getElementById('mc_client_id');
                cid = cSelect.value;
                if (!cid) return alert("Sélectionner un client.");
                nomFinal = cSelect.options[cSelect.selectedIndex].text;
            }}

            const matricule = document.getElementById('mc_matricule').value.trim();
            const carb = document.getElementById('mc_carb').value;
            const litres = parseFloat(document.getElementById('mc_litres').value) || 0;
            const montant = parseFloat(document.getElementById('mc_montant').value) || 0;

            if (montant <= 0) return alert("Montant invalide.");

            creditsAgent.push({{
                id: Date.now(),
                is_particulier: modalCreditIsParticulier,
                client_id: cid,
                nom: nomFinal,
                matricule: matricule,
                carburant: carb,
                litrage: litres,
                montant: montant
            }});

            fermerModalCredit();
            renderCredits();
            calculerCaisseAgent();
        }}

        function supprimerCredit(id) {{
            creditsAgent = creditsAgent.filter(c => c.id !== id);
            renderCredits();
            calculerCaisseAgent();
        }}

        function renderCredits() {{
            const cont = document.getElementById('liste_credits_agent');
            if (creditsAgent.length === 0) {{
                cont.innerHTML = '<div class="text-center py-6 text-xs text-[#8A9AA8] italic">Aucun crédit ajouté.</div>';
                return;
            }}

            let h = '';
            creditsAgent.forEach(c => {{
                h += `
                <div class="bg-black/40 border border-white/10 p-2 rounded-xl flex items-center justify-between text-xs gap-2">
                    <div class="min-w-0 flex-1">
                        <div class="font-bold text-white truncate text-[12px]">${{c.nom}}</div>
                        <div class="text-[10px] text-white/70 font-mono">
                            <span class="text-[#FF951A] font-bold">${{c.carburant}}</span> ${{c.litrage > 0 ? '• ' + c.litrage.toFixed(2) + ' L' : ''}} ${{c.matricule ? '• [' + c.matricule + ']' : ''}}
                        </div>
                    </div>
                    <div class="text-right">
                        <div class="font-mono font-black text-[#FF1744]">${{c.montant.toFixed(2)}} DH</div>
                    </div>
                    <button type="button" onclick="supprimerCredit(${{c.id}})" class="text-[#FF1744] hover:text-white px-1.5 font-bold">✕</button>
                </div>`;
            }});
            cont.innerHTML = h;
        }}

        function ouvrirModalCharge() {{
            document.getElementById('mch_beneficiaire').value = '';
            document.getElementById('mch_motif').value = '';
            document.getElementById('mch_montant').value = '';
            document.getElementById('modal_charge').classList.remove('hidden');
        }}

        function fermerModalCharge() {{
            document.getElementById('modal_charge').classList.add('hidden');
        }}

        function validerAjoutChargeModal() {{
            const benef = document.getElementById('mch_beneficiaire').value.trim();
            const motif = document.getElementById('mch_motif').value.trim();
            const montant = parseFloat(document.getElementById('mch_montant').value) || 0;

            if (!motif && !benef) return alert("Saisir motif ou bénéficiaire.");
            if (montant <= 0) return alert("Montant invalide.");

            chargesAgent.push({{
                id: Date.now(),
                beneficiaire: benef,
                motif: motif,
                montant: montant
            }});

            fermerModalCharge();
            renderCharges();
            calculerCaisseAgent();
        }}

        function supprimerCharge(id) {{
            chargesAgent = chargesAgent.filter(x => x.id !== id);
            renderCharges();
            calculerCaisseAgent();
        }}

        function renderCharges() {{
            const cont = document.getElementById('liste_charges_agent');
            if (chargesAgent.length === 0) {{
                cont.innerHTML = '<div class="text-center py-5 text-xs text-[#8A9AA8] italic">Aucune dépense ajoutée.</div>';
                return;
            }}

            let h = '';
            chargesAgent.forEach(ch => {{
                h += `
                <div class="bg-black/40 border border-white/10 p-2 rounded-xl flex items-center justify-between text-xs gap-2">
                    <div class="min-w-0 flex-1">
                        <div class="font-bold text-white truncate text-[12px]">${{ch.motif || 'Dépense'}}</div>
                        <div class="text-[10px] text-white/70 font-mono">
                            Par : <span class="text-[#FF951A] font-bold">${{ch.beneficiaire || '—'}}</span>
                        </div>
                    </div>
                    <div class="text-right">
                        <div class="font-mono font-black text-[#FF951A]">${{ch.montant.toFixed(2)}} DH</div>
                    </div>
                    <button type="button" onclick="supprimerCharge(${{ch.id}})" class="text-[#FF1744] hover:text-white px-1.5 font-bold">✕</button>
                </div>`;
            }});
            cont.innerHTML = h;
        }}

        function calculerCaisseAgent() {{
            let esp = 0;

            if (modeEspecesActuel === 'direct') {{
                const inpDirect = document.getElementById('especes_saisie_directe');
                esp = parseFloat(inpDirect.value) || 0;
            }} else {{
                document.querySelectorAll('.agent-input').forEach(inp => {{
                    const val = parseFloat(inp.getAttribute('data-val')) || 0;
                    const qte = parseInt(inp.value) || 0;
                    const sub = val * qte;
                    esp += sub;

                    const cId = 'sub_c_' + String(val).replace('.', '_');
                    const targetSub = document.getElementById(cId);
                    if (targetSub) targetSub.innerText = sub.toFixed(2) + ' DH';
                }});
            }}

            const tpeInp = document.getElementById('agent_tpe');
            const tpe = parseFloat(tpeInp.value) || 0;

            const cred = creditsAgent.reduce((acc, c) => acc + (parseFloat(c.montant) || 0), 0);
            const charg = chargesAgent.reduce((acc, ch) => acc + (parseFloat(ch.montant) || 0), 0);

            // Total Déclaré = Espèces + TPE + Bons de Crédits - Dépenses
            const total = (esp + tpe + cred) - charg;

            document.getElementById('txt_total_especes').innerText = esp.toFixed(2) + ' DH';
            if (document.getElementById('txt_total_especes_sub')) {{
                document.getElementById('txt_total_especes_sub').innerText = esp.toFixed(2) + ' DH';
            }}
            document.getElementById('txt_total_credits').innerText = cred.toFixed(2) + ' DH';
            document.getElementById('txt_total_charges').innerText = charg.toFixed(2) + ' DH';
            document.getElementById('txt_total_agent').innerText = total.toFixed(2) + ' DH';

            document.getElementById('credits_agent_json').value = JSON.stringify(creditsAgent);
            document.getElementById('charges_agent_json').value = JSON.stringify(chargesAgent);
        }}

        function validerAvantSoumission() {{
            calculerCaisseAgent();
            return confirm("Confirmer la clôture de la caisse ?");
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            if (typeof lucide !== 'undefined') lucide.createIcons();
            calculerCaisseAgent();
        }});
    </script>
</body>
</html>"""