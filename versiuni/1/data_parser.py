# ==============================================================================
# data_parser.py (VERSIUNEA CORECTATĂ)
# ==============================================================================
import pandas as pd
import io
from logger_setup import logger

def parse_csv_data(file_content: bytes, file_name: str) -> pd.DataFrame:
    logger.info(f"Începerea parsării pentru fișierul: '{file_name}'")
    if not file_content:
        logger.error(f"Conținutul fișierului '{file_name}' este gol.")
        raise ValueError("Fișierul selectat este gol sau corupt.")

    try:
        decoded_content = file_content.decode('utf-8')
        content_stream = io.StringIO(decoded_content)
    except UnicodeDecodeError:
        logger.error(f"Eroare de decodare pentru '{file_name}'.")
        raise ValueError("Formatul fișierului este invalid (nu este UTF-8).")

    try:
        df = pd.read_csv(content_stream)
        logger.info(f"Fișierul '{file_name}' a fost încărcat. S-au găsit {len(df)} rânduri.")

        # --- Etapa de Validare și Redenumire a Coloanelor ---
        expected_romanian_columns = ['Timp', 'Nivel de oxigen', 'Puls cardiac', 'Mişcare']
        if not all(col in df.columns for col in expected_romanian_columns):
            missing = set(expected_romanian_columns) - set(df.columns)
            logger.error(f"Coloane obligatorii lipsă în '{file_name}': {missing}")
            raise ValueError(f"Structura CSV este invalidă. Coloane lipsă: {', '.join(missing)}")
        
        # Redenumim coloanele pentru a folosi un standard intern
        rename_map = {
            'Timp': 'Time',
            'Nivel de oxigen': 'SpO2',
            'Puls cardiac': 'Pulse Rate',
            'Mişcare': 'Motion'
        }
        df.rename(columns=rename_map, inplace=True)
        logger.info("Coloanele au fost redenumite la standardul intern.")

        # --- Etapa de Curățare și Conversie ---
        initial_rows = len(df)
        df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S %d/%m/%Y', errors='coerce')
        
        rows_with_bad_date = df['Time'].isna().sum()
        if rows_with_bad_date > 0:
            logger.warning(f"În '{file_name}', {rows_with_bad_date} rânduri aveau format de dată invalid și au fost eliminate.")
            df.dropna(subset=['Time'], inplace=True)

        numeric_cols = ['SpO2', 'Pulse Rate']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        rows_with_bad_numeric = df[numeric_cols].isna().any(axis=1).sum()
        if rows_with_bad_numeric > 0:
            logger.warning(f"În '{file_name}', {rows_with_bad_numeric} rânduri aveau valori non-numerice și au fost eliminate.")
            df.dropna(subset=numeric_cols, inplace=True)
        
        df[numeric_cols] = df[numeric_cols].astype(int)
        df.set_index('Time', inplace=True)
        df.sort_index(inplace=True)

        final_rows = len(df)
        if final_rows == 0:
            logger.error(f"După curățare, nu a mai rămas niciun rând valid de date în '{file_name}'.")
            raise ValueError("Fișierul nu conține date valide după procesare.")

        logger.info(f"Parsare finalizată pentru '{file_name}'. Rânduri valide: {final_rows}/{initial_rows}.")
        return df

    except Exception as e:
        logger.critical(f"A apărut o eroare neașteptată la parsarea fișierului '{file_name}': {e}", exc_info=True)
        raise ValueError(f"Un format neașteptat în fișierul CSV a cauzat o eroare: {e}")