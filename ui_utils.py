# ==============================================================================
# FICHIER : .\ui_utils.py (COMPLET)
# ==============================================================================

import html
from fastapi import Request


# ==============================================================================
# 1. LOGO DE L'APPLICATION : "/static/logo_app.png" (FIXE & FLUIDE)
# ==============================================================================
def get_mastation_logo(height: int = 40) -> str:
    """
    Retourne le logo officiel de l'application PetroLaz depuis /static/logo_app.png.
    Taille fixe, optimisée pour le menu haut sans débordement ni ralentissement.
    """
    return f"""<img src="/static/logo_app.png" id="main-petrolaz-logo" alt="PetroLaz" class="select-none inline-block object-contain" style="height: {height}px; max-height: {height}px; width: auto;" />"""


# ==============================================================================
# 2. INTERFACE DE CONNEXION / LOGIN
# ==============================================================================
def login_page(error: str = None) -> str:
    error_banner = f"""
    <div class="mb-4 p-3 rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-600 dark:text-rose-200 text-xs font-semibold text-center animate-fadeIn">
        {html.escape(error)}
    </div>
    """ if error else ""

    return f"""<!DOCTYPE html>
<html lang="fr" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Connexion - PetroLaz</title>
    
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect x='2' y='2' width='60' height='60' rx='16' fill='%23082232' stroke='%23C08B3E' stroke-width='2.5'/%3E%3Ctext x='32' y='44' text-anchor='middle' font-family='Arial, Helvetica, sans-serif' font-weight='900' font-size='30' letter-spacing='-1'%3E%3Ctspan fill='%23E5A842'%3EP%3C/tspan%3E%3Ctspan fill='%23FFFFFF'%3EL%3C/tspan%3E%3C/text%3E%3C/svg%3E">

    <script>
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {{
            document.documentElement.classList.add('dark');
        }} else {{
            document.documentElement.classList.remove('dark');
        }}
    </script>

    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        brand: {{
                            gold: '#E5A842',
                            'gold-hover': '#f5b752',
                            dark: '#070E15',
                            petrol: '#184E68',
                            bg: '#EEF2F6',
                            'bg-dark': '#060C12'
                        }}
                    }},
                    keyframes: {{
                        fadeIn: {{
                            '0%': {{ opacity: '0', transform: 'translateY(-4px)' }},
                            '100%': {{ opacity: '1', transform: 'translateY(0)' }},
                        }}
                    }},
                    animation: {{
                        fadeIn: 'fadeIn 0.15s ease-out forwards',
                    }}
                }}
            }}
        }}
    </script>
    
    <script src="https://unpkg.com/lucide@latest"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    
    <style>
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: #EEF2F6;
            background-image: linear-gradient(180deg, rgba(238, 242, 246, 0.40) 0%, rgba(203, 213, 225, 0.60) 100%), 
                              url('/static/station_bg_Claire.jpg');
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            transition: background 0.3s ease-in-out;
        }}

        html.dark body {{
            background-color: #060C12;
            background-image: linear-gradient(180deg, rgba(6, 12, 18, 0.65) 0%, rgba(3, 7, 12, 0.85) 100%), 
                              url('/static/station_bg_sombre.png');
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
    </style>
</head>
<body class="h-full flex flex-col justify-center items-center p-4 relative text-slate-800 dark:text-white select-none">

    <div class="absolute top-5 right-5 z-50">
        <button type="button" onclick="toggleTheme()" class="px-2.5 py-2 rounded-xl bg-white/75 dark:bg-[#102434]/65 backdrop-blur-xl text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-[#18354c] border border-slate-200/80 dark:border-white/10 transition shadow-lg flex items-center gap-2 cursor-pointer" title="Changer de thème">
            <i data-lucide="sun" class="w-4 h-4 hidden dark:block text-amber-400"></i>
            <i data-lucide="moon" class="w-4 h-4 block dark:hidden text-slate-700"></i>
            <span class="text-xs font-bold hidden sm:inline text-slate-800 dark:text-slate-200">Mode</span>
        </button>
    </div>

    <div class="w-full max-w-[420px] p-6 sm:p-8 rounded-3xl bg-white/85 dark:bg-[#0A1622]/80 backdrop-blur-2xl border border-white/80 dark:border-white/10 shadow-2xl transition-all duration-200">
        
        <div class="flex justify-center mb-6">
            {get_mastation_logo(height=80)}
        </div>

        {error_banner}

        <form action="/login" method="POST" class="space-y-4">
            <div class="space-y-1.5">
                <div class="relative flex items-center">
                    <i data-lucide="user" class="absolute left-3.5 w-4 h-4 text-slate-400"></i>
                    <input type="text" name="username" required placeholder="admin" autocomplete="username"
                           class="w-full pl-10 pr-4 py-3 text-xs sm:text-sm font-semibold rounded-xl bg-blue-50/70 dark:bg-[#132332]/90 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#E5A842] transition shadow-inner">
                </div>
            </div>

            <div class="space-y-1.5">
                <div class="relative flex items-center">
                    <i data-lucide="lock" class="absolute left-3.5 w-4 h-4 text-slate-400"></i>
                    <input type="password" id="passwordField" name="password" required placeholder="••••••••" autocomplete="current-password"
                           class="w-full pl-10 pr-10 py-3 text-xs sm:text-sm font-semibold rounded-xl bg-blue-50/70 dark:bg-[#132332]/90 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#E5A842] transition shadow-inner">
                    <button type="button" onclick="togglePasswordVisibility()" class="absolute right-3.5 text-slate-400 hover:text-slate-600 dark:hover:text-white transition" title="Afficher/Masquer le mot de passe">
                        <i data-lucide="eye" id="eyeIcon" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <button type="submit" class="w-full mt-2 py-3 rounded-xl bg-gradient-to-r from-[#0284C7] to-[#0369A1] dark:from-[#EA580C] dark:to-[#F59E0B] text-white font-black uppercase tracking-wider text-xs shadow-lg shadow-sky-500/25 dark:shadow-orange-500/25 transition flex items-center justify-center gap-2 active:scale-95 cursor-pointer">
                <span>Se connecter</span>
                <i data-lucide="arrow-right" class="w-4 h-4"></i>
            </button>
        </form>
    </div>

    <script>
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

        function togglePasswordVisibility() {{
            const input = document.getElementById('passwordField');
            const icon = document.getElementById('eyeIcon');
            if (input.type === 'password') {{
                input.type = 'text';
                icon.setAttribute('data-lucide', 'eye-off');
            }} else {{
                input.type = 'password';
                icon.setAttribute('data-lucide', 'eye');
            }}
            lucide.createIcons();
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }});
        if (typeof lucide !== 'undefined') lucide.createIcons();
    </script>
</body>
</html>"""


# ==============================================================================
# 3. LAYOUT PRINCIPAL (LOGO FIXE, SANS LAG, COULEUR HARMONISÉE)
# ==============================================================================
def layout(content: str, active_tab: str = "supervision", request: Request = None):
    user = getattr(request.state, "user", None) if request else None

    role = (user.get("role", "employe") if user else "employe").upper()
    is_admin_or_cpt = role.lower() in ["admin", "administrateur", "comptable", "gerant"]

    # ------------------ TOP NAV ITEMS ------------------
    top_nav_items = ""
    is_calcul_active = active_tab in ['rapport', 'rapport-quart', 'supervision', 'compteurs', 'historique']
    
    if is_admin_or_cpt:
        top_nav_items += f"""
        <div class="relative group h-full flex items-center">
            <a href="/rapport-quart" class="nav-top-link {'active' if is_calcul_active else ''}">
                <i data-lucide="calculator" class="w-4 h-4"></i>
                <span>Calcul du Jour</span>
            </a>
            
            <div class="absolute top-full left-0 w-60 pt-2 hidden group-hover:block z-50 animate-fadeIn">
                <div class="nav-dropdown-menu rounded-2xl p-2.5 space-y-1">
                    <a href="/rapport-quart" class="nav-sub-link {'active' if active_tab in ['supervision', 'rapport', 'rapport-quart'] else ''}">
                        <i data-lucide="shield-check" class="w-4 h-4"></i>
                        <span>Contrôle & Écarts</span>
                    </a>
                    <a href="/rapport-quart/compteurs" class="nav-sub-link {'active' if active_tab == 'compteurs' else ''}">
                        <i data-lucide="gauge" class="w-4 h-4"></i>
                        <span>Compteurs</span>
                    </a>
                    <a href="/rapport-quart/historique" class="nav-sub-link {'active' if active_tab == 'historique' else ''}">
                        <i data-lucide="history" class="w-4 h-4"></i>
                        <span>Historique des Quarts</span>
                    </a>
                </div>
            </div>
        </div>
        """
    else:
        top_nav_items += f"""
        <a href="/rapport-quart" class="nav-top-link {'active' if is_calcul_active else ''}">
            <i data-lucide="calculator" class="w-4 h-4"></i>
            <span>Calcul du Jour</span>
        </a>
        """

    if is_admin_or_cpt:
        is_client_active = active_tab in ["clients", "factures", "encaissements"]
        top_nav_items += f"""
        <div class="relative group h-full flex items-center">
            <a href="/clients" class="nav-top-link {'active' if is_client_active else ''}">
                <i data-lucide="users" class="w-4 h-4"></i>
                <span>Clients</span>
            </a>
            
            <div class="absolute top-full left-0 w-56 pt-2 hidden group-hover:block z-50 animate-fadeIn">
                <div class="nav-dropdown-menu rounded-2xl p-2.5 space-y-1">
                    <a href="/factures" class="nav-sub-link {'active' if active_tab == 'factures' else ''}">
                        <i data-lucide="file-text" class="w-4 h-4"></i>
                        <span>Factures</span>
                    </a>
                    <a href="/encaissements" class="nav-sub-link {'active' if active_tab == 'encaissements' else ''}">
                        <i data-lucide="wallet" class="w-4 h-4"></i>
                        <span>Encaissements</span>
                    </a>
                </div>
            </div>
        </div>
        """

    if is_admin_or_cpt:
        is_achats_active = active_tab == 'achats'
        top_nav_items += f"""
        <a href="/achats" class="nav-top-link {'active' if is_achats_active else ''}">
            <i data-lucide="shopping-cart" class="w-4 h-4"></i>
            <span>Achats</span>
        </a>
        """

    # ------------------ MOBILE BOTTOM NAV ------------------
    mobile_menu_items = f"""
    <a href="/rapport-quart" class="flex flex-col items-center justify-center flex-1 py-1 {'text-[#EA580C] font-bold' if is_calcul_active else 'text-slate-400'}">
        <i data-lucide="calculator" class="w-4 h-4"></i>
        <span class="text-[10px] mt-0.5 whitespace-nowrap">Calcul</span>
    </a>
    <a href="/clients" class="flex flex-col items-center justify-center flex-1 py-1 {'text-[#EA580C] font-bold' if active_tab == 'clients' else 'text-slate-400'}">
        <i data-lucide="users" class="w-4 h-4"></i>
        <span class="text-[10px] mt-0.5 whitespace-nowrap">Clients</span>
    </a>
    <a href="/factures" class="flex flex-col items-center justify-center flex-1 py-1 {'text-[#EA580C] font-bold' if active_tab == 'factures' else 'text-slate-400'}">
        <i data-lucide="file-text" class="w-4 h-4"></i>
        <span class="text-[10px] mt-0.5 whitespace-nowrap">Factures</span>
    </a>
    <a href="/encaissements" class="flex flex-col items-center justify-center flex-1 py-1 {'text-[#EA580C] font-bold' if active_tab == 'encaissements' else 'text-slate-400'}">
        <i data-lucide="wallet" class="w-4 h-4"></i>
        <span class="text-[10px] mt-0.5 whitespace-nowrap">Encaissements</span>
    </a>
    <a href="/achats" class="flex flex-col items-center justify-center flex-1 py-1 {'text-[#EA580C] font-bold' if active_tab == 'achats' else 'text-slate-400'}">
        <i data-lucide="shopping-cart" class="w-4 h-4"></i>
        <span class="text-[10px] mt-0.5 whitespace-nowrap">Achats</span>
    </a>
    """

    # ------------------ SIDEBAR DYNAMIQUE COMPACTE ------------------
    sidebar_html = f"""
    <div id="sidebar-trigger-wrapper" class="group/sidebar shrink-0 flex h-full z-30 pt-16">
        <div class="w-3.5 h-full group-hover/sidebar:w-0 transition-all duration-200 flex items-center justify-center cursor-pointer">
            <div class="w-1.5 h-16 bg-[#E5A842]/60 group-hover/sidebar:opacity-0 rounded-full transition-opacity"></div>
        </div>

        <aside id="sidebar-menu" class="w-0 opacity-0 group-hover/sidebar:w-64 group-hover/sidebar:opacity-100 transition-all duration-200 ease-in-out overflow-hidden flex flex-col bg-[#070E15] border-r border-[#142636] p-0 group-hover/sidebar:p-5 shadow-2xl">
            <div class="w-56 flex flex-col h-full pt-4">
                
                <nav class="flex flex-col gap-3 flex-1 overflow-y-auto pr-1" id="sidebar-links">
                    <a href="/fournisseurs" class="sidebar-item {'is-active' if active_tab == 'fournisseurs' else ''}">
                        <i data-lucide="factory" class="w-5 h-5 shrink-0"></i>
                        <span>Fournisseurs</span>
                    </a>
                    
                    <a href="/achats" class="sidebar-item {'is-active' if active_tab == 'achats' else ''}">
                        <i data-lucide="shopping-cart" class="w-5 h-5 shrink-0"></i>
                        <span>Achats & BL</span>
                    </a>
                    
                    <a href="/prix" class="sidebar-item {'is-active' if active_tab == 'prix' else ''}">
                        <i data-lucide="tag" class="w-5 h-5 shrink-0"></i>
                        <span>Prix & Tarifs</span>
                    </a>
                    
                   <a href="/centre-rapports" class="sidebar-item {'is-active' if active_tab == 'centre_rapports' else ''}">
                        <i data-lucide="bar-chart-3" class="w-5 h-5 shrink-0"></i>
                        <span>Rapports</span>
                    </a>
                    
                    <a href="/notes" class="sidebar-item {'is-active' if active_tab == 'notes' else ''}">
                        <i data-lucide="sticky-note" class="w-5 h-5 shrink-0"></i>
                        <span>Notes & Mémos</span>
                    </a>
                    
                    <a href="/utilisateurs" class="sidebar-item {'is-active' if active_tab == 'utilisateurs' else ''}">
                        <i data-lucide="shield-check" class="w-5 h-5 shrink-0"></i>
                        <span>Gestion Employés</span>
                    </a>
                </nav>

                <div class="pt-4 mt-auto flex items-center justify-between text-[11px] text-slate-400 font-bold shrink-0">
                    <span>PetroLaz</span>
                    <span class="text-[#E5A842]">v2.5</span>
                </div>
            </div>
        </aside>
    </div>
    """

    # LOGO STRICTEMENT ENCADRÉ ET FIXE
    nav_logo_html = f"""
    <a href="/" id="navbar-brand-logo" class="flex items-center shrink-0 py-1 transition-opacity hover:opacity-90" title="PetroLaz - Accueil">
        {get_mastation_logo(height=42)}
    </a>
    """

    return f"""<!DOCTYPE html>
<html lang="fr" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>PetroLaz</title>
    
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect x='2' y='2' width='60' height='60' rx='16' fill='%23082232' stroke='%23C08B3E' stroke-width='2.5'/%3E%3Ctext x='32' y='44' text-anchor='middle' font-family='Arial, Helvetica, sans-serif' font-weight='900' font-size='30' letter-spacing='-1'%3E%3Ctspan fill='%23E5A842'%3EP%3C/tspan%3E%3Ctspan fill='%23FFFFFF'%3EL%3C/tspan%3E%3C/text%3E%3C/svg%3E">
    
    <script>
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {{
            document.documentElement.classList.add('dark');
        }} else {{
            document.documentElement.classList.remove('dark');
        }}
    </script>

    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        brand: {{
                            gold: '#E5A842',
                            'gold-hover': '#f5b752',
                            dark: '#070E15',
                            petrol: '#184E68',
                            bg: '#EEF2F6',
                            'bg-dark': '#060C12'
                        }}
                    }},
                    keyframes: {{
                        fadeIn: {{
                            '0%': {{ opacity: '0', transform: 'translateY(-4px)' }},
                            '100%': {{ opacity: '1', transform: 'translateY(0)' }},
                        }}
                    }},
                    animation: {{
                        fadeIn: 'fadeIn 0.15s ease-out forwards',
                    }}
                }}
            }}
        }}
    </script>
    
    <script src="https://unpkg.com/lucide@latest"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    
    <style>
        html, body, main, div, nav, aside, * {{
            scrollbar-width: none !important;
            -ms-overflow-style: none !important;
        }}
        *::-webkit-scrollbar {{
            display: none !important;
            width: 0 !important;
            height: 0 !important;
        }}

        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            letter-spacing: -0.01em;
            background-color: #eef2f6 !important;
            background-image: linear-gradient(180deg, rgba(240, 244, 248, 0.20) 0%, rgba(226, 232, 240, 0.40) 100%), 
                              url('/static/station_bg_Claire.jpg') !important;
            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
            transition: background 0.3s ease-in-out;
            -webkit-font-smoothing: antialiased;
        }}

        html.dark body {{
            background-color: #060c12 !important;
            background-image: linear-gradient(180deg, rgba(6, 12, 18, 0.45) 0%, rgba(3, 7, 12, 0.65) 100%), 
                              url('/static/station_bg_sombre.png') !important;
            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}

        input[type="date"] {{
            color-scheme: light;
        }}
        input[type="date"]::-webkit-calendar-picker-indicator {{
            cursor: pointer;
            filter: invert(0) !important;
            opacity: 0.75;
            transition: all 0.15s ease;
        }}
        input[type="date"]::-webkit-calendar-picker-indicator:hover {{
            opacity: 1;
        }}

        html.dark input[type="date"],
        .dark input[type="date"] {{
            color-scheme: dark !important;
        }}
        html.dark input[type="date"]::-webkit-calendar-picker-indicator,
        .dark input[type="date"]::-webkit-calendar-picker-indicator {{
            filter: invert(1) brightness(1.8) contrast(1.2) !important;
            opacity: 1 !important;
        }}

        /* ========================================================
           BARRE DU HAUT : COULEUR DU LOGO ET ZÉRO TRANSFORMATION
        ======================================================== */
        #main-navbar {{
            background-color: #070e15 !important;
            border-bottom: 1px solid #142636 !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
            transition: transform 0.25s ease !important;
        }}
        .navbar-hidden {{
            transform: translateY(-100%) !important;
            pointer-events: none !important;
        }}

        #sidebar-menu {{
            border-right: 1px solid #142636 !important;
        }}

        /* Logo toujours net, fixe, sans changement au survol */
        #main-petrolaz-logo {{
            height: 42px !important;
            max-height: 42px !important;
            width: auto !important;
            object-fit: contain !important;
            transform: none !important;
        }}

        .nav-top-link {{
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.55rem 0.95rem;
            font-size: 0.9rem;
            font-weight: 700;
            color: #e2e8f0 !important;
            background: transparent !important;
            border: none !important;
            outline: none !important;
            transition: color 0.15s ease;
            white-space: nowrap;
            border-radius: 0.65rem;
        }}
        .nav-top-link i, .nav-top-link svg {{
            color: #94a3b8;
            stroke: #94a3b8;
            transition: color 0.15s ease, stroke 0.15s ease;
        }}

        .nav-top-link:hover,
        .nav-top-link:hover *,
        .nav-top-link.active,
        .nav-top-link.active * {{
            color: #E5A842 !important;
            stroke: #E5A842 !important;
        }}

        .nav-dropdown-menu {{
            background-color: #070e15 !important;
            border: 1px solid #142636 !important;
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.7) !important;
        }}

        .nav-sub-link {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.6rem 0.85rem;
            font-size: 0.85rem;
            font-weight: 700;
            color: #cbd5e1 !important;
            border-radius: 0.5rem;
            transition: color 0.15s ease;
        }}
        .nav-sub-link i, .nav-sub-link svg {{ 
            color: #94a3b8; 
            stroke: #94a3b8; 
        }}

        .nav-sub-link:hover,
        .nav-sub-link:hover *,
        .nav-sub-link.active,
        .nav-sub-link.active * {{
            color: #E5A842 !important;
            stroke: #E5A842 !important;
        }}

        .nav-logout-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.45rem 0.8rem;
            font-size: 0.85rem;
            font-weight: 700;
            color: #cbd5e1;
            transition: color 0.15s ease;
        }}
        .nav-logout-btn:hover {{ color: #f43f5e !important; }}
        .nav-logout-btn:hover i {{ color: #f43f5e !important; stroke: #f43f5e !important; }}

        .sidebar-item {{
            display: flex;
            align-items: center;
            gap: 0.85rem;
            padding: 0.6rem 0.5rem;
            color: #f1f5f9;
            font-weight: 700;
            font-size: 0.9rem;
            border-radius: 0.5rem;
            transition: color 0.15s ease;
            white-space: nowrap;
        }}
        .sidebar-item i, .sidebar-item svg {{
            color: #94a3b8;
            stroke: #94a3b8;
        }}
        .sidebar-item:hover,
        .sidebar-item.is-active {{
            color: #E5A842 !important;
        }}
        .sidebar-item:hover i, .sidebar-item:hover svg,
        .sidebar-item.is-active i, .sidebar-item.is-active svg {{
            color: #E5A842 !important;
            stroke: #E5A842 !important;
        }}

        /* ========================================================
           BOUTONS DE L'APPLICATION
        ======================================================== */
        button[type="submit"]:not(.client-dropdown-menu *),
        button[onclick*="ouvrirModal"]:not(.client-dropdown-menu *),
        button[onclick*="toggleModal"]:not([onclick*="false"]):not([onclick*="fermer"]):not(.client-dropdown-menu *),
        button[onclick*="document.getElementById('modal-"]:not([onclick*="add('hidden')"]):not(.client-dropdown-menu *),
        button[onclick*="openAddModal"],
        button[onclick*="traiterZoneColler"],
        button[onclick*="uploadFusionFile"],
        button[onclick*="document.getElementById('fusionFileInput')"],
        a.btn-primary,
        button.btn-primary,
        button[class*="bg-[#E5A842]"]:not(.client-dropdown-menu *),
        button[class*="bg-emerald-600"]:not(.client-dropdown-menu *),
        button[class*="bg-sky-600"]:not(.client-dropdown-menu *),
        button[class*="bg-amber-500"]:not(.client-dropdown-menu *),
        button[class*="bg-[#184E68]"]:not(.sidebar-item):not(.nav-top-link):not(.client-dropdown-menu *),
        button[class*="bg-[#00F5A0]"] {{
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 0.5rem !important;
            height: 40px !important;
            min-height: 40px !important;
            padding: 0.55rem 1.35rem !important;
            border-radius: 0.75rem !important;
            font-size: 0.875rem !important;
            font-weight: 800 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            cursor: pointer !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            border: 1px solid transparent !important;
            white-space: nowrap !important;
            background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
            color: #FFFFFF !important;
            box-shadow: 0 4px 12px -2px rgba(2, 132, 199, 0.35) !important;
        }}

        button[type="submit"]:not(.client-dropdown-menu *) *,
        button[onclick*="ouvrirModal"]:not(.client-dropdown-menu *) *,
        button[onclick*="toggleModal"]:not([onclick*="false"]):not([onclick*="fermer"]):not(.client-dropdown-menu *) *,
        button[onclick*="document.getElementById('modal-"]:not([onclick*="add('hidden')"]):not(.client-dropdown-menu *) *,
        button[onclick*="openAddModal"] *,
        button[class*="bg-[#E5A842]"]:not(.client-dropdown-menu *) *,
        button[class*="bg-emerald-600"]:not(.client-dropdown-menu *) *,
        button[class*="bg-sky-600"]:not(.client-dropdown-menu *) *,
        button[class*="bg-amber-500"]:not(.client-dropdown-menu *) *,
        button[class*="bg-[#184E68]"]:not(.client-dropdown-menu *) *,
        button[class*="bg-[#00F5A0]"] * {{
            color: #FFFFFF !important;
            stroke: #FFFFFF !important;
        }}

        button[type="submit"]:not(.client-dropdown-menu *):hover,
        button[onclick*="ouvrirModal"]:not(.client-dropdown-menu *):hover,
        button[onclick*="toggleModal"]:not([onclick*="false"]):not([onclick*="fermer"]):not(.client-dropdown-menu *):hover,
        button[class*="bg-[#E5A842]"]:not(.client-dropdown-menu *):hover,
        button[class*="bg-emerald-600"]:not(.client-dropdown-menu *):hover,
        button[class*="bg-sky-600"]:not(.client-dropdown-menu *):hover,
        button[class*="bg-amber-500"]:not(.client-dropdown-menu *):hover,
        button[class*="bg-[#184E68]"]:not(.client-dropdown-menu *):hover {{
            background: linear-gradient(135deg, #0369A1 0%, #075985 100%) !important;
            box-shadow: 0 6px 16px -2px rgba(2, 132, 199, 0.48) !important;
            transform: translateY(-1px) !important;
        }}

        html.dark button[type="submit"]:not(.client-dropdown-menu *),
        html.dark button[onclick*="ouvrirModal"]:not(.client-dropdown-menu *),
        html.dark button[onclick*="toggleModal"]:not([onclick*="false"]):not([onclick*="fermer"]):not(.client-dropdown-menu *),
        html.dark button[onclick*="document.getElementById('modal-"]:not([onclick*="add('hidden')"]):not(.client-dropdown-menu *),
        html.dark button[onclick*="openAddModal"],
        html.dark button[onclick*="traiterZoneColler"],
        html.dark button[onclick*="uploadFusionFile"],
        html.dark button[onclick*="document.getElementById('fusionFileInput')"],
        html.dark a.btn-primary,
        html.dark button.btn-primary,
        html.dark button[class*="bg-[#E5A842]"]:not(.client-dropdown-menu *),
        html.dark button[class*="bg-emerald-600"]:not(.client-dropdown-menu *),
        html.dark button[class*="bg-sky-600"]:not(.client-dropdown-menu *),
        html.dark button[class*="bg-amber-500"]:not(.client-dropdown-menu *),
        html.dark button[class*="bg-[#184E68]"]:not(.sidebar-item):not(.nav-top-link):not(.client-dropdown-menu *),
        html.dark button[class*="bg-[#00F5A0]"] {{
            background: linear-gradient(135deg, #EA580C 0%, #F59E0B 100%) !important;
            color: #FFFFFF !important;
            box-shadow: 0 4px 14px -2px rgba(234, 88, 12, 0.40) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
        }}

        html.dark button[type="submit"]:not(.client-dropdown-menu *):hover,
        html.dark button[onclick*="ouvrirModal"]:not(.client-dropdown-menu *):hover,
        html.dark button[onclick*="toggleModal"]:not([onclick*="false"]):not([onclick*="fermer"]):not(.client-dropdown-menu *):hover,
        html.dark button[class*="bg-[#E5A842]"]:not(.client-dropdown-menu *):hover,
        html.dark button[class*="bg-emerald-600"]:not(.client-dropdown-menu *):hover,
        html.dark button[class*="bg-sky-600"]:not(.client-dropdown-menu *):hover,
        html.dark button[class*="bg-amber-500"]:not(.client-dropdown-menu *):hover,
        html.dark button[class*="bg-[#184E68]"]:not(.client-dropdown-menu *):hover {{
            background: linear-gradient(135deg, #C2410C 0%, #D97706 100%) !important;
            box-shadow: 0 6px 20px -2px rgba(245, 158, 11, 0.55) !important;
            transform: translateY(-1px) !important;
        }}

        .client-dropdown-menu button,
        .client-dropdown-menu a {{
            height: auto !important;
            min-height: unset !important;
            background: transparent !important;
            box-shadow: none !important;
            border: none !important;
            text-transform: none !important;
            letter-spacing: normal !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            border-radius: 8px !important;
            padding: 8px 12px !important;
            transform: none !important;
        }}

        .client-dropdown-menu button:hover,
        .client-dropdown-menu a:hover {{
            background-color: rgba(100, 116, 139, 0.08) !important;
        }}
        html.dark .client-dropdown-menu button:hover,
        html.dark .client-dropdown-menu a:hover {{
            background-color: rgba(255, 255, 255, 0.06) !important;
        }}

        .client-dropdown-menu button.text-rose-600,
        .client-dropdown-menu a.text-rose-600 {{
            color: #e11d48 !important;
        }}
        .client-dropdown-menu button.text-rose-600:hover,
        .client-dropdown-menu a.text-rose-600:hover {{
            background-color: rgba(225, 29, 72, 0.08) !important;
            color: #e11d48 !important;
        }}
        html.dark .client-dropdown-menu button.text-rose-400,
        html.dark .client-dropdown-menu a.text-rose-400 {{
            color: #fb7185 !important;
        }}
        html.dark .client-dropdown-menu button.text-rose-400:hover,
        html.dark .client-dropdown-menu a.text-rose-400:hover {{
            background-color: rgba(251, 113, 133, 0.12) !important;
            color: #fb7185 !important;
        }}

        button[onclick*="fermer"],
        button[onclick*="close"],
        button[onclick*="toggleModal(false)"],
        button[onclick*="add('hidden')"],
        button:not([type="submit"]):not([class*="bg-"]):not([class*="text-rose-"]):not([class*="text-sky-"]):not(.sidebar-item):not(.nav-top-link):not(.nav-sub-link):not(.client-dropdown-menu *) {{
            border-radius: 0.75rem !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            transition: all 0.15s ease !important;
        }}

        button[class*="bg-rose-"]:not(.client-dropdown-menu *),
        button[class*="text-rose-"]:not(.client-dropdown-menu *),
        form[action*="delete"]:not(.client-dropdown-menu *) button,
        form[action*="supprimer"]:not(.client-dropdown-menu *) button {{
            background: rgba(244, 63, 94, 0.12) !important;
            color: #F43F5E !important;
            border: 1px solid rgba(244, 63, 94, 0.25) !important;
            box-shadow: none !important;
        }}

        button[class*="bg-rose-"]:not(.client-dropdown-menu *):hover,
        button[class*="text-rose-"]:not(.client-dropdown-menu *):hover,
        form[action*="delete"]:not(.client-dropdown-menu *) button:hover,
        form[action*="supprimer"]:not(.client-dropdown-menu *) button:hover {{
            background: #E11D48 !important;
            color: #FFFFFF !important;
            border-color: #E11D48 !important;
            box-shadow: 0 4px 12px rgba(225, 29, 72, 0.35) !important;
        }}

        button.w-7.h-7,
        a.w-7.h-7,
        button.w-8.h-8,
        a.w-8.h-8 {{
            height: 30px !important;
            width: 30px !important;
            min-height: 30px !important;
            min-width: 30px !important;
            padding: 0 !important;
            border-radius: 0.6rem !important;
        }}
    </style>
</head>
<body class="h-full flex flex-col overflow-hidden text-slate-900 dark:text-slate-100 transition-colors duration-200 text-xs">
    
    <!-- 1. NAVBAR FIXE, HARMONISÉE AVEC LE LOGO -->
    <nav id="main-navbar" class="fixed top-0 left-0 right-0 w-full z-40 h-16 shrink-0">
        <div class="max-w-[1920px] mx-auto px-5 sm:px-8 h-full flex items-center justify-between">
            
            {nav_logo_html}

            <div class="hidden lg:flex items-center justify-center gap-10 h-full">
                {top_nav_items}
            </div>
            
            <div class="flex items-center gap-4 shrink-0">
                <button type="button" onclick="toggleTheme()" class="px-3 py-2.5 rounded-xl bg-white/10 text-slate-300 hover:bg-white/20 border border-white/10 transition shadow-xs cursor-pointer" title="Changer de thème">
                    <i data-lucide="sun" class="w-4 h-4 hidden dark:block text-amber-400"></i>
                    <i data-lucide="moon" class="w-4 h-4 block dark:hidden text-slate-700"></i>
                </button>

                <a href="/logout" class="nav-logout-btn" title="Se déconnecter">
                    <i data-lucide="log-out" class="w-4 h-4"></i>
                    <span class="hidden sm:inline">Déconnexion</span>
                </a>
            </div>
        </div>
    </nav>

    <!-- 2. CONTENEUR CONTENU ADAPTATIF -->
    <div class="flex-1 flex overflow-hidden w-full relative h-full">
        {sidebar_html}

        <main id="main-content-scroll" class="flex-1 min-w-0 overflow-y-auto px-3 sm:px-6 md:px-8 pt-[72px] pb-10">
            <div class="max-w-[1700px] mx-auto min-h-[calc(100vh-95px)] flex flex-col justify-center w-full py-2">
                {content}
            </div>
        </main>
    </div>

    <nav class="lg:hidden fixed bottom-0 left-0 right-0 bg-[#070E15] border-t border-[#142636] px-2 py-1 flex items-center justify-around z-50 shadow-2xl">
        {mobile_menu_items}
    </nav>

    <script>
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
        
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                document.querySelectorAll('[id^="modal"]').forEach(m => m.classList.add('hidden'));
            }}
        }});

        document.addEventListener('DOMContentLoaded', () => {{
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }});

        if (typeof lucide !== 'undefined') lucide.createIcons();
    </script>
</body>
</html>"""