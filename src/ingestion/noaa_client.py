"""
Modulo de ingestao de dados de SST via NOAA Coral Reef Watch ERDDAP.
Atende ao RF02: Coletar dados de variaveis ambientais (SST, anomalia).
"""

import pandas as pd
import numpy as np
import os
from time import sleep
import urllib.request
import urllib.error
from io import StringIO

# ERDDAP base URL e Dataset ID conforme especificacao tecnica 
ERDDAP_BASE = "https://oceanwatch.pifsc.noaa.gov/erddap/griddap/"
SST_DATASET = "CRW_sst_v3_1_monthly"

# Diretorio de cache alinhado ao Plano de Projeto [cite: 172]
# Estrutura: coral-sol-predicao/data/cache
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")


def fetch_sst_for_point(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Busca SST mensal para um ponto especifico via ERDDAP[cite: 282, 283]."""
    lon_360 = longitude % 360

    url = (
        f"{ERDDAP_BASE}{SST_DATASET}.csv?"
        f"sea_surface_temperature"
        f"[({start_date}T12:00:00Z):1:({end_date}T12:00:00Z)]"
        f"[({latitude}):1:({latitude})]"
        f"[({lon_360}):1:({lon_360})]"
    )

    try:
        response = urllib.request.urlopen(url, timeout=30)
        content = response.read().decode("utf-8")

        lines = content.strip().split("\n")
        header = lines[0]
        data_lines = lines[2:]  # pula header + linha de unidades 

        clean_csv = header + "\n" + "\n".join(data_lines)
        df = pd.read_csv(StringIO(clean_csv))

        # Rename para o padrao da Analytical Base Table (ABT) 
        rename_map = {
            'time': 'date',
            'latitude': 'latitude',
            'longitude': 'longitude',
            'sea_surface_temperature': 'sst'
        }
        
        # Mapeamento flexivel para diferentes versoes da API
        current_map = {col: rename_map[col.split(' ')[0].lower()] 
                       for col in df.columns if col.split(' ')[0].lower() in rename_map}
        
        df = df.rename(columns=current_map)

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        if "longitude" in df.columns:
            df["longitude"] = df["longitude"].apply(lambda x: x - 360 if x > 180 else x)

        return df

    except Exception as e:
        print(f"  Erro ao acessar NOAA para ({latitude}, {longitude}): {e}")
        return pd.DataFrame()

def save_sst_cache(df: pd.DataFrame, filename: str = "noaa_tubastrae_br.csv") -> str:
    """Salva dados de SST no cache conforme o Plano de Governança[cite: 120, 172]."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
        
    filepath = os.path.join(CACHE_DIR, filename)
    
    # Se ja existir, concatena para nao perder dados anteriores (incremental)
    if os.path.exists(filepath):
        existing_df = pd.read_csv(filepath)
        df = pd.concat([existing_df, df]).drop_duplicates().reset_index(drop=True)
    
    df.to_csv(filepath, index=False)
    print(f"  [OK] Dados persistidos em: {filepath}")
    return filepath

if __name__ == "__main__":
    print(f"{'='*60}\nINGESTAO NOAA - POC CORAL-SOL (RF02)\n{'='*60}")
    
    # Coordenadas piloto: Arraial do Cabo - RJ [cite: 150]
    lat_piloto, lon_piloto = -22.97, -42.03
    
    print(f"Consumindo dados para regiao piloto: {lat_piloto}, {lon_piloto}...")
    
    # Busca dados de 2023 para validar sinal preditivo [cite: 259]
    df_noaa = fetch_sst_for_point(
        latitude=lat_piloto,
        longitude=lon_piloto,
        start_date="2023-01-01",
        end_date="2023-12-01"
    )

    if not df_noaa.empty:
        # Adiciona colunas derivadas da ABT para teste 
        df_noaa['sst_anomaly'] = df_noaa['sst'] - df_noaa['sst'].mean()
        df_noaa['above_repro_threshold'] = (df_noaa['sst'] >= 24.5).astype(int)
        
        # Persistencia no cache solicitado
        save_sst_cache(df_noaa)
        
        print(f"\nResumo dos dados coletados:")
        print(f"- Registros: {len(df_noaa)}")
        print(f"- SST Media: {df_noaa['sst'].mean():.2f}°C")
        print(f"- Meses acima do limiar (24.5°C): {df_noaa['above_repro_threshold'].sum()}")
    else:
        print("Falha na ingestao. Verifique a conexao com coastwatch.pfeg.noaa.gov.")