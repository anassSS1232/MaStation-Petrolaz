# ==================================================
# FICHIER : .\main.py
# ==================================================

import os
import urllib.parse
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

from database import init_db
from security import verifier_session

BASE_DIR = Path(__file__).resolve().parent

# ================= 1. PERMISSIONS PAR RÔLE =================
# Séparation stricte : l'employé est confiné à son sous-chemin dédié /employe
PERMISSIONS = {
    "admin": ["*"],
    "administrateur": ["*"],
    "comptable": [
        "/",
        "/rapport-quart",
        "/clients",
        "/prix",
        "/notes",
        "/fournisseurs",
        "/achats",
        "/factures",
        "/encaissements",
        "/centre-rapports",
        "/api",
    ],
    "employe": ["/employe"],
}

# ================= 2. MIDDLEWARE D'AUTHENTIFICATION =================
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Routes publiques libres d'accès
        if path in ["/login", "/logout", "/favicon.ico"] or path.startswith("/static"):
            return await call_next(request)

        cookie_session = request.cookies.get("session_user")
        user = verifier_session(cookie_session)

        # Redirection si non authentifié
        if not user:
            response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
            response.delete_cookie("session_user")
            return response

        role = str(user.get("role", "employe")).lower().strip()
        request.state.user = user

        # Accès complet pour l'admin
        if role in ["admin", "administrateur"]:
            return await call_next(request)

        # Vérification des autorisations par préfixe ou route exacte
        allowed_routes = PERMISSIONS.get(role, [])
        is_allowed = any(path == r or (r != "/" and path.startswith(r)) for r in allowed_routes)

        if not is_allowed:
            # Si le rôle est employé, on le renvoie silencieusement et directement à son poste
            if role == "employe":
                return RedirectResponse(url="/employe/poste", status_code=status.HTTP_303_SEE_OTHER)

            # Écran d'interdiction pour les autres rôles
            return HTMLResponse(
                content=f"""
                <div style="text-align: center; margin-top: 100px; font-family: sans-serif;">
                    <h1 style="color: #e11d48; font-size: 2rem;">Accès Refusé (403)</h1>
                    <p style="color: #64748b;">Votre rôle <b>{role.upper()}</b> n'a pas accès à cette section.</p>
                    <a href="/" style="display: inline-block; margin-top: 15px; padding: 10px 20px; background: #0284c7; color: white; border-radius: 8px; text-decoration: none;">Retour à l'accueil</a>
                </div>
                """,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return await call_next(request)

# ================= 3. INITIALISATION DE L'APPLICATION =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    (BASE_DIR / "static" / "uploads" / "factures").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "static" / "uploads" / "clients").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "static" / "uploads" / "encaissements").mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "static" / "uploads" / "fournisseurs").mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(title="PETROLAZ - Station Service", lifespan=lifespan)
app.add_middleware(AuthMiddleware)

static_folder = BASE_DIR / "static"
static_folder.mkdir(parents=True, exist_ok=True)

# Protection Path-Traversal sur les fichiers clients
@app.get("/static/uploads/clients/{nom_fichier:path}")
async def servir_document_client(nom_fichier: str):
    nom_fichier = urllib.parse.unquote(nom_fichier)
    upload_client_dir = (BASE_DIR / "static" / "uploads" / "clients").resolve()
    target_file = (upload_client_dir / nom_fichier).resolve()

    if not str(target_file).startswith(str(upload_client_dir)):
        return HTMLResponse("Accès interdit", status_code=403)

    if target_file.is_file():
        ext = target_file.suffix.lower()
        media_types = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }
        return FileResponse(str(target_file), media_type=media_types.get(ext, "application/octet-stream"))

    return HTMLResponse("Document introuvable sur le disque", status_code=404)

app.mount("/static", StaticFiles(directory=str(static_folder)), name="static")

# ================= 4. ROUTEURS =================
from pages import home, rapport, prix, notes, login
from pages.clients import router as clients_router
from pages.utilisateurs import router as utilisateurs_router
from pages.fournisseurs import router as fournisseurs_router
from pages.achats import router as achats_router
from pages.factures import router as factures_router
from pages.encaissements import router as encaissements_router
from pages.centre_rapports import router as centre_rapports_router
from pages.rapport_ventes_pompes import router as rapport_ventes_pompes_router
from pages.rapport_encaissements import router as rapport_encaissements_router
from pages.rapport_soldes_clients import router as rapport_soldes_clients_router
from pages.rapport_dettes_fournisseurs import router as rapport_dettes_fournisseurs_router
from pages.rapport_grand_livre import router as rapport_grand_livre_router
from pages.rapport_etat_stocks import router as rapport_etat_stocks_router

# Inclusion du nouveau module dédié Pompiste
from pages.portail_employe.routes import router as employe_router

app.include_router(employe_router)

# Autres modules de l'application
app.include_router(rapport_etat_stocks_router)
app.include_router(rapport_grand_livre_router)
app.include_router(rapport_dettes_fournisseurs_router)
app.include_router(rapport_soldes_clients_router)
app.include_router(rapport_encaissements_router)
app.include_router(login.router)
app.include_router(home.router)
app.include_router(clients_router)
app.include_router(rapport.router)
app.include_router(prix.router)
app.include_router(utilisateurs_router)
app.include_router(notes.router)
app.include_router(fournisseurs_router)
app.include_router(achats_router)
app.include_router(factures_router)
app.include_router(encaissements_router)
app.include_router(centre_rapports_router)
app.include_router(rapport_ventes_pompes_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)