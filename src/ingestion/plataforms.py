"""
Modulo de ingestao de dados de plataformas de petroleo via ANP (dados abertos).
Atende ao RF03 (parcial): dados antropogenicos para cruzamento na ABT.

Fonte: ANP - Dados Abertos - Unidades de Operacao Maritimas
URL: https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/
O CSV contem todas as plataformas em operacao com coordenadas reais.
"""

import pandas as pd
import numpy as np
import os
import requests


# URL do CSV oficial da ANP com plataformas em operacao
ANP_PLATFORMS_URL = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
    "arquivos/arquivos-fase-de-desenvolvimento-e-producao/lpo/"
    "dados-abertos-plataformas-operacao.csv"
)

# Diretorio de cache
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")


def fetch_platforms(use_cache: bool = True) -> pd.DataFrame:
    """
    Baixa os dados de plataformas em operacao direto do portal da ANP.
    O CSV usa encoding latin-1 e separador virgula.

    Args:
        use_cache: se True, usa arquivo local se disponivel

    Returns:
        DataFrame com dados limpos das plataformas
    """
    cache_file = os.path.join(CACHE_DIR, "anp_plataformas.csv")

    # Tenta cache
    if use_cache and os.path.exists(cache_file):
        df = pd.read_csv(cache_file)
        print(f"  Plataformas carregadas do cache: {len(df)} registros")
        return df

    print("  Baixando dados de plataformas da ANP...")

    # Faz download do CSV
    response = requests.get(ANP_PLATFORMS_URL, timeout=30)
    response.raise_for_status()

    # Salva conteudo bruto para inspecionar encoding
    raw_path = os.path.join(CACHE_DIR, "anp_plataformas_raw.csv")
    os.makedirs(CACHE_DIR, exist_ok=True)

    with open(raw_path, "wb") as f:
        f.write(response.content)

    # Tenta ler com diferentes encodings (ANP costuma usar latin-1)
    for encoding in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
        try:
            df = pd.read_csv(raw_path, encoding=encoding)
            if len(df.columns) > 3:
                print(f"  Encoding detectado: {encoding}")
                break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue

    print(f"  Colunas encontradas: {list(df.columns)}")
    print(f"  Registros brutos: {len(df)}")

    return df


def clean_platforms(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa e padroniza o DataFrame de plataformas.
    Identifica as colunas de latitude/longitude independente do nome exato
    e filtra apenas registros com coordenadas validas.

    Args:
        df: DataFrame bruto da ANP

    Returns:
        DataFrame limpo e padronizado
    """
    # Padroniza nomes de colunas (remove espacos, coloca em minusculo)
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    print(f"  Colunas padronizadas: {list(df.columns)}")

    # Identifica colunas de interesse por nome parcial
    col_map = {}
    for col in df.columns:
        col_l = col.lower()
        if "sigla" in col_l and "instal" in col_l:
            col_map["sigla"] = col
        elif "nome" in col_l and "instal" in col_l:
            col_map["name"] = col
        elif "bacia" in col_l:
            col_map["basin"] = col
        elif "operador" in col_l:
            col_map["operator"] = col
        elif "classific" in col_l:
            col_map["classification"] = col
        elif "latitude" in col_l:
            col_map["latitude"] = col
        elif "longitude" in col_l:
            col_map["longitude"] = col
        elif "campo" in col_l and "bacia" not in col_l:
            col_map["field"] = col
        elif "lâmina" in col_l or "lamina" in col_l:
            col_map["water_depth_m"] = col
        elif "ano" in col_l and "início" in col_l or "inicio" in col_l:
            col_map["start_year"] = col

    print(f"  Colunas mapeadas: {col_map}")

    # Renomeia colunas encontradas
    rename = {v: k for k, v in col_map.items()}
    df = df.rename(columns=rename)

    # Converte lat/lon para numerico
    if "latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    if "longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Filtra apenas registros com coordenadas validas
    before = len(df)
    df = df.dropna(subset=["latitude", "longitude"])
    print(f"  Removidos {before - len(df)} registros sem coordenadas")
    print(f"  Plataformas com coordenadas: {len(df)}")

    return df.reset_index(drop=True)


def calculate_distance_to_nearest(
    lat: float,
    lon: float,
    platforms_df: pd.DataFrame,
) -> float:
    """
    Calcula a distancia em km ate a plataforma mais proxima
    usando a formula de Haversine (distancia esferica).

    A formula de Haversine e mais precisa que distancia euclidiana
    para coordenadas geograficas, especialmente em distancias maiores.

    Args:
        lat: latitude do ponto de interesse
        lon: longitude do ponto de interesse
        platforms_df: DataFrame com colunas latitude e longitude

    Returns:
        distancia em km ate a plataforma mais proxima
    """
    R = 6371.0  # raio da Terra em km

    lat1 = np.radians(lat)
    lon1 = np.radians(lon)
    lat2 = np.radians(platforms_df["latitude"].values)
    lon2 = np.radians(platforms_df["longitude"].values)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    distances = R * c
    return float(distances.min())


def get_nearest_info(
    lat: float,
    lon: float,
    platforms_df: pd.DataFrame,
) -> dict:
    """
    Retorna informacoes da plataforma mais proxima.

    Args:
        lat: latitude do ponto
        lon: longitude do ponto
        platforms_df: DataFrame com plataformas

    Returns:
        dicionario com nome, bacia e distancia
    """
    R = 6371.0
    lat1 = np.radians(lat)
    lon1 = np.radians(lon)
    lat2 = np.radians(platforms_df["latitude"].values)
    lon2 = np.radians(platforms_df["longitude"].values)

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distances = R * c

    idx = distances.argmin()
    row = platforms_df.iloc[idx]

    return {
        "nearest_platform": row.get("name", row.get("sigla", "desconhecida")),
        "nearest_basin": row.get("basin", "desconhecida"),
        "distance_km": float(distances[idx]),
    }


def load_platforms(use_cache: bool = True) -> pd.DataFrame:
    """
    Funcao principal: baixa, limpa e retorna plataformas prontas para uso.
    Salva versao limpa no cache.

    Args:
        use_cache: se True, usa cache se disponivel

    Returns:
        DataFrame limpo com plataformas
    """
    clean_cache = os.path.join(CACHE_DIR, "anp_plataformas_clean.csv")

    if use_cache and os.path.exists(clean_cache):
        df = pd.read_csv(clean_cache)
        print(f"  Plataformas (limpas) do cache: {len(df)} registros")
        return df

    print("=" * 50)
    print("INGESTAO - PLATAFORMAS ANP")
    print("=" * 50)

    df_raw = fetch_platforms(use_cache=False)
    df_clean = clean_platforms(df_raw)

    # Salva versao limpa
    os.makedirs(CACHE_DIR, exist_ok=True)
    df_clean.to_csv(clean_cache, index=False)
    print(f"  Salvo em: {clean_cache}")

    return df_clean


# Teste direto
if __name__ == "__main__":
    df = load_platforms(use_cache=False)

    print(f"\nTotal de plataformas: {len(df)}")

    if "basin" in df.columns:
        print(f"Bacias: {df['basin'].nunique()}")
        print(df["basin"].value_counts().to_string())

    # Testa distancia para hotspots conhecidos de coral-sol
    hotspots = {
        "Arraial do Cabo/RJ": (-22.97, -42.03),
        "Ilha Grande/RJ": (-23.15, -44.23),
        "Maceio/AL": (-9.67, -35.70),
        "Florianopolis/SC": (-27.59, -48.55),
    }

    print(f"\n{'='*50}")
    print("DISTANCIA ATE PLATAFORMA MAIS PROXIMA")
    print(f"{'='*50}")

    for nome, (lat, lon) in hotspots.items():
        info = get_nearest_info(lat, lon, df)
        print(
            f"  {nome:25s} -> {info['distance_km']:7.1f} km "
            f"({info['nearest_platform']}, {info['nearest_basin']})"
        )