# ==================================================
# FICHIER : pages/login.py (COMPLET)
# ==================================================

import html
from fastapi import APIRouter, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse

from database import verifier_utilisateur
from security import signer_session, SESSION_DURATION_SECONDS
from ui_utils import get_mastation_logo

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(error: str = None):
    escaped_error = html.escape(error) if error else ""
    error_banner = (
        f"""
    <div class="mb-5 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-semibold flex items-center justify-center gap-2 backdrop-blur-md animate-pulse">
        <i data-lucide="alert-circle" class="w-4 h-4 shrink-0"></i>
        <span>{escaped_error}</span>
    </div>
    """
        if error
        else ""
    )

    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html lang="fr" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Connexion - PetroLaz</title>
    
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect x='2' y='2' width='60' height='60' rx='16' fill='%23082232' stroke='%23C08B3E' stroke-width='2.5'/%3E%3Ctext x='32' y='44' text-anchor='middle' font-family='Arial, Helvetica, sans-serif' font-weight='900' font-size='30' letter-spacing='-1'%3E%3Ctspan fill='%23E5A842'%3EP%3C/tspan%3E%3Ctspan fill='%23FFFFFF'%3EL%3C/tspan%3E%3C/text%3E%3C/svg%3E">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    
    <style>
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: #060B12;
            background-image: linear-gradient(180deg, rgba(6, 11, 18, 0.45) 0%, rgba(3, 7, 12, 0.70) 100%), 
                              url('/static/station_bg_sombre.png');
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        .login-card {{
            background: rgba(11, 21, 34, 0.90);
            backdrop-filter: blur(28px);
            -webkit-backdrop-filter: blur(28px);
            border: 1.5px solid rgba(229, 168, 66, 0.50);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 35px rgba(229, 168, 66, 0.15);
        }}

        .custom-input {{
            background-color: #eaf1fb;
            border: 1.5px solid transparent;
            color: #0F172A;
            transition: all 0.25s ease;
        }}
        .custom-input:focus {{
            background-color: #FFFFFF;
            border-color: #9333ea;
            box-shadow: 0 0 0 4px rgba(147, 51, 234, 0.25);
        }}
        .custom-input::placeholder {{
            color: #64748b;
            font-weight: 500;
        }}

        .btn-okay {{
            background: linear-gradient(135deg, #a824cc 0%, #7e199d 50%, #580d70 100%);
            border: 1px solid rgba(255, 255, 255, 0.25);
            box-shadow: 0 8px 25px -4px rgba(168, 36, 204, 0.55);
            transition: all 0.25s ease;
        }}
        .btn-okay:hover {{
            background: linear-gradient(135deg, #b833de 0%, #8e21b0 50%, #681284 100%);
            box-shadow: 0 12px 30px -2px rgba(168, 36, 204, 0.75);
            transform: translateY(-1.5px);
        }}
        .btn-okay:active {{
            transform: translateY(0);
        }}
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4 relative select-none overflow-hidden">

    <!-- 1. LOGO EN HAUT À GAUCHE (AGRANDI ET TRÈS VISIBLE) -->
    <header class="absolute top-4 left-4 sm:top-6 sm:left-8 z-20">
        <a href="/" class="block hover:scale-105 transition-transform duration-200">
            {get_mastation_logo(height=80)}
        </a>
    </header>

    <!-- 2. CADRE DE CONNEXION AU CENTRE -->
    <main class="w-full max-w-[440px] relative z-10 my-auto">
        <div class="login-card p-7 sm:p-9 rounded-3xl">

            <!-- LOGO CENTRAL GRAND ET VISIBLE AU-DESSUS DE "SE CONNECTER" -->
            <div class="flex justify-center mb-5">
                {get_mastation_logo(height=110)}
            </div>

            <!-- Titre "Se connecter" -->
            <div class="text-center mb-6">
                <h1 class="text-2xl font-black text-white tracking-wide">Se connecter</h1>
                <p class="text-xs text-slate-400 mt-1">Accédez à votre espace de gestion</p>
            </div>

            {error_banner}

            <form action="/login" method="POST" class="space-y-4">
                
                <!-- Champ Identifiant -->
                <div class="relative flex items-center">
                    <i data-lucide="user" class="absolute left-4 w-5 h-5 text-slate-500 pointer-events-none"></i>
                    <input type="text" 
                           name="username" 
                           placeholder="Identifiant" 
                           required 
                           autocapitalize="none" 
                           class="custom-input w-full pl-12 pr-4 py-3.5 rounded-xl text-sm font-semibold outline-none">
                </div>

                <!-- Champ Mot de passe -->
                <div class="relative flex items-center">
                    <i data-lucide="lock" class="absolute left-4 w-5 h-5 text-slate-500 pointer-events-none"></i>
                    <input type="password" 
                           id="passwordInput" 
                           name="password" 
                           placeholder="Mot de passe" 
                           required 
                           class="custom-input w-full pl-12 pr-11 py-3.5 rounded-xl text-sm font-semibold outline-none">
                    <button type="button" onclick="togglePassword()" class="absolute right-3.5 text-slate-400 hover:text-purple-600 p-1 transition-colors">
                        <i id="eyeIcon" data-lucide="eye" class="w-4 h-4"></i>
                    </button>
                </div>

                <!-- Bouton Connexion -->
                <div class="pt-3">
                    <button type="submit" class="btn-okay w-full py-3.5 px-4 text-white font-extrabold text-sm tracking-wide rounded-xl flex items-center justify-center gap-2 cursor-pointer active:scale-[0.98]">
                        <span>Se connecter</span>
                        <i data-lucide="arrow-right" class="w-4 h-4 stroke-[2.5]"></i>
                    </button>
                </div>
            </form>
        </div>
    </main>

    <script>
        function togglePassword() {{
            const passInput = document.getElementById('passwordInput');
            const eyeBtn = document.getElementById('eyeIcon');
            if (passInput.type === 'password') {{
                passInput.type = 'text';
                eyeBtn.setAttribute('data-lucide', 'eye-off');
            }} else {{
                passInput.type = 'password';
                eyeBtn.setAttribute('data-lucide', 'eye');
            }}
            lucide.createIcons();
        }}
        document.addEventListener('DOMContentLoaded', () => {{ lucide.createIcons(); }});
    </script>
</body>
</html>
"""
    )


@router.post("/login")
async def login_post(username: str = Form(...), password: str = Form(...)):
    raw_user = username.strip()
    raw_pass = password.strip()

    user = verifier_utilisateur(raw_user.lower(), raw_pass) or verifier_utilisateur(
        raw_user, raw_pass
    )
    if not user:
        return RedirectResponse(
            url="/login?error=Identifiant+ou+mot+de+passe+incorrect",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    role = str(user.get("role", "employe")).lower().strip()
    # Redirection vers son espace dédié isolé :
    redirect_target = "/employe/poste" if role == "employe" else "/"

    response = RedirectResponse(
        url=redirect_target, status_code=status.HTTP_303_SEE_OTHER
    )
    signed_cookie = signer_session(user)
    response.set_cookie(
        key="session_user",
        value=signed_cookie,
        httponly=True,
        samesite="lax",
        max_age=SESSION_DURATION_SECONDS,
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session_user")
    return response