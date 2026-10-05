# utils/client_helpers.py
import re
from database import get_db_connection

def nombre_en_lettres(n: float) -> str:
    unites = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
              "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
    dizaines = ["", "dix", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante-dix", "quatre-vingt", "quatre-vingt-dix"]
    
    def conv_inf_1000(num):
        if num == 0: return ""
        if num < 20: return unites[num]
        if num < 100:
            d, u = num // 10, num % 10
            if d in (7, 9):
                d_base = 6 if d == 7 else 8
                sep = " et " if (d == 7 and u == 1) else "-"
                return dizaines[d_base] + sep + conv_inf_1000(u + 10)
            sep = " et un" if (u == 1 and d != 8) else (f"-{unites[u]}" if u > 0 else "")
            return dizaines[d] + sep
        c, r = num // 100, num % 100
        prefix = "cent" if c == 1 else f"{unites[c]} cent"
        if c > 1 and r == 0: prefix += "s"
        return f"{prefix} {conv_inf_1000(r)}".strip()

    def conv(num):
        if num == 0: return "zéro"
        m_millions, m_mille, reste = num // 1_000_000, (num % 1_000_000) // 1_000, num % 1_000
        parts = []
        if m_millions > 0: parts.append("un million" if m_millions == 1 else f"{conv_inf_1000(m_millions)} millions")
        if m_mille > 0: parts.append("mille" if m_mille == 1 else f"{conv_inf_1000(m_mille)} mille")
        if reste > 0: parts.append(conv_inf_1000(reste))
        return " ".join(parts).strip()

    try:
        n_pos = abs(float(n))
        entier, centimes = int(n_pos), int(round((n_pos - int(n_pos)) * 100))
        res = f"{conv(entier)} dirham{'s' if entier > 1 else ''}"
        if centimes > 0: res += f" et {conv(centimes)} centime{'s' if centimes > 1 else ''}"
        return res.capitalize()
    except Exception:
        return "Zéro dirham"

def generate_next_client_code():
    conn = get_db_connection()
    rows = conn.execute("SELECT code FROM clients ORDER BY id DESC").fetchall()
    conn.close()
    max_num = 0
    for r in rows:
        digits = re.findall(r'\d+', r['code'] or "")
        if digits and int(digits[-1]) > max_num:
            max_num = int(digits[-1])
    return f"CL-{max_num + 1:03d}"

def generate_next_facture_number():
    conn = get_db_connection()
    row = conn.execute("SELECT numero_facture FROM factures_clients ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if not row or not row['numero_facture']:
        return "0001"
    digits = re.findall(r'\d+', str(row['numero_facture']))
    if digits:
        return f"{int(digits[-1]) + 1:04d}"
    return "0001"