# pages/attestations/salaire.py
import html
from datetime import datetime
from utils.client_helpers import nombre_en_lettres

def generer_attestation_salaire(u: dict) -> str:
    nom_emp = html.escape(u.get("nom_complet") or "")
    cin_emp = html.escape(u.get("cin") or "")
    cnss_emp = html.escape(u.get("cnss") or "")
    
    role_emp = "Agent Pompiste" if u.get("role") == "employe" else ("Comptable" if u.get("role") == "comptable" else "Administrateur")
    
    salaire = float(u.get("salaire_base") or 0.0)
    salaire_lettres = nombre_en_lettres(salaire)
    salaire_str = f"{salaire:,.2f}" if salaire > 0 else ""
    
    date_actuelle = datetime.now().strftime("%d/%m/%Y")
    cache_buster = int(datetime.now().timestamp())

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Attestation de Salaire {f'- {nom_emp}' if nom_emp else ''}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    
    <style>
        @page {{
            size: A4 portrait;
            margin: 0;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
            color: #0F172A;
            background: #F1F5F9;
            font-size: 15px;
            line-height: 1.8;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}

        /* Bouton d'impression */
        .toolbar-top {{
            position: fixed;
            top: 20px;
            right: 25px;
            display: flex;
            gap: 12px;
            z-index: 1000;
        }}
        .btn-print {{
            background: #0F172A;
            color: #FFFFFF;
            border: none;
            padding: 11px 22px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 13.5px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.25);
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
        }}
        .btn-print:hover {{
            background: #000000;
            transform: translateY(-1px);
        }}
        .tip-banner {{
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(15, 23, 42, 0.88);
            backdrop-filter: blur(6px);
            color: white;
            padding: 9px 20px;
            border-radius: 30px;
            font-size: 12.5px;
            font-weight: 600;
            z-index: 1000;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
        }}

        /* Feuille A4 */
        .page-a4 {{
            position: relative;
            width: 210mm;
            min-height: 297mm;
            padding: 24mm 26mm 18mm 26mm;
            margin: 30px auto;
            background: #FFFFFF;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            overflow: hidden;
        }}

        /* FILIGRANE DU LOGO AU CENTRE DE LA FEUILLE */
        .page-a4::before {{
            content: "";
            position: absolute;
            top: 48%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 440px;
            height: 440px;
            background-image: url('/static/logo.png?v={cache_buster}');
            background-repeat: no-repeat;
            background-position: center center;
            background-size: contain;
            opacity: 0.06; /* Filigrane très subtil et chic */
            pointer-events: none;
            z-index: 0;
        }}

        .content-body, .footer-legal {{
            position: relative;
            z-index: 1; /* Le texte reste bien lisible par-dessus le filigrane */
        }}

        /* TITRE BIEN POSITIONNÉ ET CENTRÉ */
        .doc-title-section {{
            text-align: center;
            margin-top: 15px;
            margin-bottom: 55px;
        }}
        .titre-principal {{
            font-size: 24px;
            font-weight: 900;
            letter-spacing: 2.5px;
            color: #0F172A;
            text-transform: uppercase;
            text-decoration: underline;
            text-underline-offset: 8px;
            margin: 0;
            display: inline-block;
        }}

        /* CORPS DE L'ATTESTATION */
        .content-body {{
            flex: 1;
        }}
        .body-text {{
            font-size: 15.5px;
            line-height: 2.3;
            color: #1E293B;
            text-align: left;
        }}
        .body-text p {{
            margin-bottom: 24px;
        }}

        /* CHAMPS MODIFIABLES SANS POINTS GÊNANTS */
        .editable-field {{
            display: inline-block;
            font-weight: 800;
            color: #0F172A;
            padding: 0 4px;
            border-radius: 4px;
            outline: none;
            min-width: 30px;
            transition: background 0.15s ease;
        }}
        .editable-field:empty::before {{
            content: attr(data-placeholder);
            color: #94A3B8;
            font-weight: 400;
            letter-spacing: 1px;
        }}
        .editable-field:hover, .editable-field:focus {{
            background: #FEF3C7;
        }}

        /* SALAIRE PROPRE ET ÉPURÉ */
        .salary-line {{
            margin: 22px 0 28px 0;
            padding-left: 20px;
            border-left: 3px solid #0F172A;
            line-height: 1.9;
        }}
        .salary-amount-text {{
            font-size: 19px;
            font-weight: 900;
            color: #0F172A;
        }}
        .salary-words-text {{
            font-size: 14.5px;
            color: #475569;
            font-style: italic;
        }}

        /* SIGNATURES ET CACHET */
        .signatures-section {{
            margin-top: 55px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .cachet-box {{
            width: 280px;
            height: 135px;
            border: 1.5px dashed #94A3B8;
            border-radius: 8px;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            background: rgba(250, 250, 250, 0.8);
        }}
        .cachet-box .cachet-title {{
            font-size: 11.5px;
            font-weight: 800;
            letter-spacing: 0.8px;
            color: #64748B;
            text-transform: uppercase;
        }}
        .cachet-box .cachet-sub {{
            font-size: 11.5px;
            color: #94A3B8;
            font-style: italic;
            text-align: center;
        }}
        .signature-info {{
            font-size: 15px;
            line-height: 2.1;
            color: #0F172A;
            text-align: right;
        }}

        /* PIED DE PAGE LÉGAL (CONFORME FACTURE) */
        .footer-legal {{
            border-top: 1px solid #E2E8F0;
            padding-top: 18px;
            text-align: center;
            font-size: 10.5px;
            line-height: 1.55;
            color: #475569;
        }}
        .footer-legal .company-name {{
            color: #0F172A;
            font-weight: 900;
            font-size: 11px;
            margin-bottom: 2px;
        }}

        /* IMPRESSION PURE */
        @media print {{
            body {{
                background: #FFFFFF !important;
                padding: 0 !important;
            }}
            .toolbar-top, .tip-banner {{
                display: none !important;
            }}
            .page-a4 {{
                width: 100% !important;
                min-height: 297mm !important;
                padding: 20mm 20mm 15mm 20mm !important;
                margin: 0 !important;
                box-shadow: none !important;
            }}
            .editable-field:hover, .editable-field:focus {{
                background: transparent !important;
            }}
        }}
    </style>
</head>
<body>

    <div class="tip-banner">
        💡 <b>Astuce :</b> Vous pouvez modifier le montant en chiffres, les lettres en Dirhams s'actualisent automatiquement !
    </div>

    <div class="toolbar-top">
        <button onclick="window.print()" class="btn-print">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><path d="M6 14h12v8H6z"></path></svg>
            Imprimer l'Attestation
        </button>
    </div>

    <div class="page-a4">
        <div class="content-body">
            
            <!-- TITRE CENTRÉ ET AÉRÉ (AUCUN RISQUE DE CHEVAUCHEMENT) -->
            <div class="doc-title-section">
                <h1 class="titre-principal">ATTESTATION DE SALAIRE</h1>
            </div>

            <!-- CORPS OFFICIEL -->
            <div class="body-text">
                <p>
                    Je soussigné <span contenteditable="true" class="editable-field" data-placeholder="................................">Monsieur le Gérant</span>, 
                    Gérant de la société <span contenteditable="true" class="editable-field" data-placeholder="................................">Sté PETROLAZ SARL</span>, 
                    atteste par la présente que :
                </p>

                <p style="margin-left: 10px;">
                    Monsieur : <span contenteditable="true" class="editable-field" style="font-size: 16.5px;" data-placeholder="................................................................">{nom_emp}</span><br>
                    Titulaire de la CIN N° : <span contenteditable="true" class="editable-field" data-placeholder="........................................">{cin_emp}</span><br>
                    Immatriculé à la CNSS sous le N° : <span contenteditable="true" class="editable-field" data-placeholder="........................................">{cnss_emp}</span><br>
                    Occupant le poste de : <span contenteditable="true" class="editable-field" data-placeholder="........................................">{role_emp}</span>
                </p>

                <p>
                    Perçoit à ce titre une rémunération mensuelle nette de :
                </p>

                <!-- SECTION SALAIRE RESPONSIVE / AUTO-CALCULÉE -->
                <div class="salary-line">
                    <div class="salary-amount-text">
                        <span contenteditable="true" id="salaire_num" class="editable-field" data-placeholder="0.00">{salaire_str}</span> MAD NET / MOIS
                    </div>
                    <div class="salary-words-text">
                        Soit en toutes lettres : <span contenteditable="true" id="salaire_txt" class="editable-field" data-placeholder="................................................................">{salaire_lettres}</span>
                    </div>
                </div>

                <p style="margin-top: 35px;">
                    Cette attestation lui est délivrée à sa demande pour servir et valoir ce que de droit.
                </p>
            </div>

            <!-- CACHET ET SIGNATURES (OUJDA) -->
            <div class="signatures-section">
                <div class="cachet-box">
                    <div class="cachet-title">Cachet & Signature</div>
                    <div class="cachet-sub">Sté. PETROLAZ SARL</div>
                </div>

                <div class="signature-info">
                    <div>Fait à : <span contenteditable="true" class="editable-field" data-placeholder="............">Oujda</span></div>
                    <div>Le : <span contenteditable="true" class="editable-field" data-placeholder="... / ... / ......">{date_actuelle}</span></div>
                    <div style="margin-top: 6px;">Prénom et nom : <span contenteditable="true" class="editable-field" data-placeholder="................................">Direction Générale</span></div>
                    <div style="margin-top: 6px;">Signature et cachet</div>
                </div>
            </div>

        </div>

        <!-- PIED DE PAGE LÉGAL -->
        <div class="footer-legal">
            <div class="company-name">Sté. PETROLAZ - SARL - Société à Responsabilité Limitée</div>
            <div>Capital : 100 000,00 Dhs - Patente : 11205468 - RC : 43683 - IF : 66182311 - ICE : 003565664000057</div>
            <div>Lot Iris, rue Aouinet Serrak, Lot N° 385, Étage 1, Appt N° 2 - Oujda</div>
            <div>Tél : 0661362819 - Email : petrolaz2025@gmail.com</div>
        </div>
    </div>

    <!-- SCRIPT DE CONVERSION CHIFFRES -> LETTRES DIRHAMS RESPONSIVE -->
    <script>
        function frenchNumber(n) {{
            if (n === 0) return "zéro";
            const units = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"];
            const tens = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante", "quatre-vingt", "quatre-vingt"];

            function below100(num) {{
                if (num < 20) return units[num];
                const d = Math.floor(num / 10);
                const u = num % 10;
                if (d === 7) return u === 1 ? "soixante-et-onze" : "soixante-" + units[10 + u];
                if (d === 9) return "quatre-vingt-" + units[10 + u];
                if (d === 8 && u === 0) return "quatre-vingts";
                if (u === 1 && d < 8) return tens[d] + "-et-un";
                if (u === 0) return tens[d];
                return tens[d] + "-" + units[u];
            }}

            function below1000(num) {{
                if (num === 0) return "";
                const c = Math.floor(num / 100);
                const r = num % 100;
                let s = "";
                if (c === 1) s = "cent";
                else if (c > 1) s = units[c] + " cent" + (r === 0 ? "s" : "");
                if (r > 0) s = (s ? s + " " : "") + below100(r);
                return s;
            }}

            let parts = [];
            const millions = Math.floor(n / 1000000);
            n %= 1000000;
            const thousands = Math.floor(n / 1000);
            const rest = n % 1000;

            if (millions > 0) parts.push(millions === 1 ? "un million" : below1000(millions) + " millions");
            if (thousands > 0) parts.push(thousands === 1 ? "mille" : below1000(thousands) + " mille");
            if (rest > 0) parts.push(below1000(rest));

            return parts.join(" ");
        }}

        function convertToDirhams(val) {{
            if (isNaN(val) || val <= 0) return "Zéro dirham";
            const entier = Math.floor(val);
            const centimes = Math.round((val - entier) * 100);

            let txt = frenchNumber(entier);
            txt = txt.charAt(0).toUpperCase() + txt.slice(1);
            txt += (entier > 1 ? " dirhams" : " dirham");

            if (centimes > 0) {{
                let centTxt = frenchNumber(centimes);
                txt += " et " + centTxt + (centimes > 1 ? " centimes" : " centime");
            }}
            return txt;
        }}

        const salaireNum = document.getElementById("salaire_num");
        const salaireTxt = document.getElementById("salaire_txt");

        salaireNum.addEventListener("input", function() {{
            let clean = this.innerText.replace(/[^0-9.,]/g, "").replace(",", ".");
            let val = parseFloat(clean);
            if (!isNaN(val) && val >= 0) {{
                salaireTxt.innerText = convertToDirhams(val);
            }} else if (this.innerText.trim() === "") {{
                salaireTxt.innerText = "";
            }}
        }});
    </script>
</body>
</html>"""