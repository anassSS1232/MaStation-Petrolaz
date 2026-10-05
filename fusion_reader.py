# fusion_reader.py
import re
import io
import pandas as pd
import xml.etree.ElementTree as ET

def nettoyer_nombre(valeur):
    """Convertit une chaîne ou valeur brute en float en ignorant dates et heures."""
    if pd.isna(valeur) or valeur is None:
        return 0.0
    val_str = str(valeur).strip().replace('\xa0', '').replace(' ', '').replace(',', '.')
    if '#' in val_str or not val_str or val_str.lower() in ['nan', 'none', 'null', '--']:
        return 0.0
    
    # Exclusion stricte des dates et heures
    if '/' in val_str or ':' in val_str:
        return 0.0
    if re.match(r'^\d{4}-\d{2}-\d{2}', val_str):
        return 0.0

    val_clean = re.sub(r'[^\d.]', '', val_str)
    try:
        return float(val_clean) if val_clean else 0.0
    except ValueError:
        return 0.0

def trouver_et_aligner_entetes(df):
    """Localise automatiquement la ligne des en-têtes réels."""
    mots_cles = ['fp', 'pump', 'pompe', 'fuel', 'grade', 'carburant', 'volume', 'sale', 'montant', 'amount', 'totalizer', 'nozzle', 'hose']
    
    matches_cols = sum(1 for c in df.columns if any(m == str(c).lower().strip() or m in str(c).lower().strip() for m in mots_cles))
    if matches_cols >= 2:
        return df

    for i in range(min(25, len(df))):
        row_vals = [str(val).lower().strip() for val in df.iloc[i].values if pd.notna(val)]
        matches = sum(1 for val in row_vals if any(m == val or m in val for m in mots_cles))
        if matches >= 2:
            new_df = df.iloc[i+1:].copy()
            new_df.columns = [str(val).strip() for val in df.iloc[i].values]
            return new_df

    return df

def extraire_donnees_dataframe(df):
    indexes = {"ESS": {}, "DIE": {}}
    volumes_vendus = {"ESS": {}, "DIE": {}}
    transactions_list = []

    if df is None or df.empty:
        return {"indexes": indexes, "volumes": volumes_vendus, "transactions": []}

    df = trouver_et_aligner_entetes(df)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Détection automatique des colonnes
    col_sale = next((c for c in df.columns if any(k in c for k in ['sale', 'trx', 'trans', 'seq', 'vente', 'ticket', 'n°'])), None)
    col_date = next((c for c in df.columns if 'date' in c), None)
    col_time = next((c for c in df.columns if any(k in c for k in ['time', 'heure'])), None)
    col_pump = next((c for c in df.columns if c in ['fp', 'pmp'] or any(k in c for k in ['pump', 'pompe', 'fueling point', 'pistolet', 'pos'])), None)
    col_fuel = next((c for c in df.columns if any(k in c for k in ['grade', 'fuel', 'carburant', 'produit', 'prod', 'article'])), None)
    
    col_vol = next((c for c in df.columns if any(k in c for k in ['volume', 'vol', 'quantit', 'litres', 'qte']) and 'tot' not in c and 'init' not in c and 'fin' not in c), None)
    col_money = next((c for c in df.columns if any(k in c for k in ['money', 'amount', 'montant', 'total', 'valeur', 'dh', 'prix']) and 'tot' not in c), None)
    
    col_initial = next((c for c in df.columns if ('date' not in c and 'time' not in c and 'heure' not in c) and any(k in c for k in ['start totalizer', 'start tot', 'initial_vol', 'vol_init', 'start_vol', 'vol initial', 'tot_init', 'vol. initial'])), None)
    col_final = next((c for c in df.columns if ('date' not in c and 'time' not in c and 'heure' not in c) and any(k in c for k in ['end totalizer', 'end tot', 'final_vol', 'vol_fin', 'end_vol', 'vol final', 'tot_vol', 'vol. final'])), None)

    cols = list(df.columns)

    if not col_fuel:
        for c in cols:
            val_exemples = " ".join(df[c].dropna().astype(str).head(20).values).upper()
            if any(k in val_exemples for k in ["SSP", "SP", "GASOIL", "DIESEL", "G10", "ESSENCE"]):
                col_fuel = c
                break

    if not col_pump:
        for c in cols:
            val_exemples = [nettoyer_nombre(v) for v in df[c].dropna().head(15).values]
            if val_exemples and all(1 <= v <= 32 for v in val_exemples if v > 0):
                col_pump = c
                break

    records = df.to_dict(orient='records')

    for row in records:
        try:
            p_val = nettoyer_nombre(row.get(col_pump))
            if p_val <= 0 or p_val > 50:
                continue
            pump_id = int(p_val)

            f_val = str(row.get(col_fuel, '')).strip().upper()
            if any(k in f_val for k in ["SSP", "SP", "ESS", "SUPER", "SANS PLOMB", "95", "98"]):
                c_type = "ESS"
                carburant_nom = "Essence (SP)"
            elif any(k in f_val for k in ["GASOIL", "G10", "DIE", "DIESEL", "GO", "G50"]):
                c_type = "DIE"
                carburant_nom = "Gasoil 10"
            else:
                continue

            vol = nettoyer_nombre(row.get(col_vol, 0.0))
            money = nettoyer_nombre(row.get(col_money, 0.0)) if col_money else 0.0
            
            raw_sale = str(row.get(col_sale, '--')).strip()
            sale_id = raw_sale[:-2] if raw_sale.endswith('.0') else raw_sale
            
            date_vente = str(row.get(col_date, '')).strip()
            if ' ' in date_vente:
                date_vente = date_vente.split(' ')[0]
            heure_vente = str(row.get(col_time, '--:--')).strip()

            init_vol = nettoyer_nombre(row.get(col_initial, 0.0)) if col_initial else 0.0
            fin_vol = nettoyer_nombre(row.get(col_final, 0.0)) if col_final else 0.0

            if init_vol > 0 and fin_vol == 0 and vol > 0:
                fin_vol = round(init_vol + vol, 2)
            elif fin_vol > 0 and init_vol == 0 and vol > 0:
                init_vol = round(fin_vol - vol, 2)

            volumes_vendus[c_type][pump_id] = volumes_vendus[c_type].get(pump_id, 0.0) + vol

            transactions_list.append({
                "sale_id": sale_id,
                "date": date_vente,
                "end_date": date_vente,
                "heure": heure_vente,
                "end_time": heure_vente,
                "pump_id": pump_id,
                "type": c_type,
                "carburant": carburant_nom,
                "volume": round(vol, 2),
                "money": round(money, 2),
                "initial_vol": round(init_vol, 2),
                "final_vol": round(fin_vol, 2)
            })

            cand_index = fin_vol if fin_vol > 0 else (init_vol + vol)
            if cand_index > 0:
                cur_max = indexes[c_type].get(pump_id, 0.0)
                if cand_index > cur_max:
                    indexes[c_type][pump_id] = round(cand_index, 2)

        except Exception:
            continue

    resultat_indexes = {"ESS": {}, "DIE": {}}
    for c_type in ["ESS", "DIE"]:
        for p_id in volumes_vendus[c_type]:
            if p_id in indexes[c_type] and indexes[c_type][p_id] > 0:
                resultat_indexes[c_type][p_id] = indexes[c_type][p_id]
            else:
                resultat_indexes[c_type][p_id] = round(volumes_vendus[c_type][p_id], 2)

    return {
        "indexes": resultat_indexes,
        "volumes": volumes_vendus,
        "transactions": transactions_list
    }

def parse_fusion_text(text: str):
    """Analyse les données textuelles (TSV / CSV / Presse-papiers)."""
    if not text or not text.strip():
        return {"indexes": {"ESS": {}, "DIE": {}}, "transactions": []}
    text = text.replace('\x00', '').strip()
    first_line = text.splitlines()[0]
    sep = '\t' if '\t' in first_line else (';' if ';' in first_line else ',')
    try:
        df = pd.read_csv(io.StringIO(text), sep=sep, header=None, engine='python', on_bad_lines='skip', dtype=str)
        return extraire_donnees_dataframe(df)
    except Exception:
        return {"indexes": {"ESS": {}, "DIE": {}}, "transactions": []}

def parse_xml_spreadsheet_2003(content: bytes):
    """Décodeur XML Spreadsheet 2003 pour Fusion."""
    try:
        root = ET.fromstring(content)
        rows_data = []
        for row in root.iter():
            if row.tag.endswith('Row'):
                row_cells = []
                for cell in row:
                    if cell.tag.endswith('Cell'):
                        data_el = next((c for c in cell if c.tag.endswith('Data')), None)
                        val = data_el.text if data_el is not None and data_el.text else ""
                        row_cells.append(val)
                if row_cells and any(row_cells):
                    rows_data.append(row_cells)
        if rows_data:
            df = pd.DataFrame(rows_data)
            return extraire_donnees_dataframe(df)
    except Exception:
        pass
    return None

def parse_fusion_transactions(file_content: bytes):
    """Analyse tous les formats de fichiers Fusion (XML, XLS, XLSX, HTML, CSV)."""
    res_xml = parse_xml_spreadsheet_2003(file_content)
    if res_xml and res_xml["transactions"]:
        return res_xml

    try:
        excel_file = pd.ExcelFile(io.BytesIO(file_content))
        for sheet_name in excel_file.sheet_names:
            df = excel_file.parse(sheet_name, header=None, dtype=str)
            res = extraire_donnees_dataframe(df)
            if res["transactions"]:
                return res
    except Exception:
        pass

    try:
        tables = pd.read_html(io.BytesIO(file_content), header=None)
        if tables:
            for t in tables:
                res = extraire_donnees_dataframe(t.astype(str))
                if res["transactions"]:
                    return res
    except Exception:
        pass

    text = None
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            text = file_content.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = file_content.decode('latin-1', errors='ignore')

    return parse_fusion_text(text)