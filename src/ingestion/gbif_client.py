"""
Modulo de ingestao de dados de ocorrencia do coral-sol via GBIF API.
Atende ao RF01: Coletar dados historicos de ocorrencia por localizacao e data.
"""

import requests
import pandas as pd
import os
import json
from time import sleep


# URL base da API do GBIF (v1)
GBIF_BASE_URL = "https://api.gbif.org/v1"

# Diretorio para cache local dos dados brutos
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")


def search_species_key(species_name: str) -> int:
    """
    Busca o taxonKey de uma especie pelo nome cientifico.
    O taxonKey e o identificador interno do GBIF para cada especie.
    Precisamos dele para filtrar as ocorrencias.

    Args:
        species_name: nome cientifico (ex: "Tubastraea coccinea")

    Returns:
        taxonKey (int) da especie no GBIF
    """
    url = f"{GBIF_BASE_URL}/species/match"
    params = {"name": species_name}

    response = requests.get(url, params=params)
    response.raise_for_status()  # levanta erro se HTTP != 200

    data = response.json()

    if "usageKey" not in data:
        raise ValueError(f"Especie '{species_name}' nao encontrada no GBIF.")

    print(f"  Especie: {data.get('scientificName', species_name)}")
    print(f"  taxonKey: {data['usageKey']}")
    print(f"  Status: {data.get('status', 'desconhecido')}")

    return data["usageKey"]


def fetch_occurrences(
    taxon_key: int,
    country: str = "BR",
    limit: int = 300,
    has_coordinate: bool = True,
    has_geospatial_issue: bool = False,
) -> list:
    """
    Busca registros de ocorrencia de uma especie no GBIF.
    A API retorna no maximo 300 registros por pagina,
    entao fazemos paginacao automatica.

    Args:
        taxon_key: identificador da especie no GBIF
        country: codigo ISO do pais (BR = Brasil)
        limit: registros por pagina (max 300)
        has_coordinate: filtra apenas registros com coordenadas
        has_geospatial_issue: False = exclui registros com problemas de geolocalizacao

    Returns:
        lista de dicionarios com os registros
    """
    all_records = []
    offset = 0

    while True:
        params = {
            "taxonKey": taxon_key,
            "country": country,
            "limit": limit,
            "offset": offset,
            "hasCoordinate": has_coordinate,
            "hasGeospatialIssue": has_geospatial_issue,
        }

        response = requests.get(f"{GBIF_BASE_URL}/occurrence/search", params=params)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            break

        all_records.extend(results)
        print(f"  Coletados: {len(all_records)} / {data.get('count', '?')} registros")

        # Se ja pegou todos, para
        if data.get("endOfRecords", True):
            break

        offset += limit
        sleep(0.5)  # pausa para nao sobrecarregar a API

    return all_records


def parse_occurrences(raw_records: list) -> pd.DataFrame:
    """
    Transforma a lista de registros brutos do GBIF em um DataFrame limpo.
    Seleciona apenas as colunas relevantes para o projeto.

    Args:
        raw_records: lista de dicionarios retornados pela API

    Returns:
        DataFrame com colunas padronizadas
    """
    rows = []

    for record in raw_records:
        # Extrai apenas os campos que precisamos
        row = {
            "gbif_id": record.get("key"),
            "species": record.get("species"),
            "latitude": record.get("decimalLatitude"),
            "longitude": record.get("decimalLongitude"),
            "date": record.get("eventDate"),
            "year": record.get("year"),
            "month": record.get("month"),
            "depth": record.get("depth"),
            "state_province": record.get("stateProvince"),
            "locality": record.get("locality"),
            "institution": record.get("institutionCode"),
            "basis_of_record": record.get("basisOfRecord"),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Remove registros sem coordenada ou data
    initial_count = len(df)
    df = df.dropna(subset=["latitude", "longitude"])
    dropped = initial_count - len(df)
    if dropped > 0:
        print(f"  Removidos {dropped} registros sem coordenadas.")

    # Converte coluna de data
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Marca presenca (todas estas sao observacoes positivas)
    df["presence"] = 1

    return df.reset_index(drop=True)


def save_to_cache(df: pd.DataFrame, filename: str) -> str:
    """
    Salva DataFrame no diretorio de cache como CSV.
    Garante que o diretorio existe antes de salvar.

    Args:
        df: DataFrame a salvar
        filename: nome do arquivo (ex: "gbif_tubastraea.csv")

    Returns:
        caminho completo do arquivo salvo
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    filepath = os.path.join(CACHE_DIR, filename)
    df.to_csv(filepath, index=False)
    print(f"  Salvo em: {filepath}")
    return filepath


def load_from_cache(filename: str) -> pd.DataFrame:
    """
    Carrega DataFrame do cache se existir.
    Evita chamadas repetidas a API durante desenvolvimento.

    Args:
        filename: nome do arquivo

    Returns:
        DataFrame ou None se nao existir
    """
    filepath = os.path.join(CACHE_DIR, filename)
    if os.path.exists(filepath):
        df = pd.read_csv(filepath, parse_dates=["date"])
        print(f"  Carregado do cache: {filepath} ({len(df)} registros)")
        return df
    return None


def collect_tubastraea_data(use_cache: bool = True) -> pd.DataFrame:
    """
    Funcao principal que orquestra toda a coleta de dados de Tubastraea.
    Busca as duas especies invasoras no Brasil: T. coccinea e T. tagusensis.

    Args:
        use_cache: se True, tenta carregar do cache antes de chamar a API

    Returns:
        DataFrame consolidado com todas as ocorrencias
    """
    cache_file = "gbif_tubastraea_br.csv"

    # Tenta cache primeiro
    if use_cache:
        cached = load_from_cache(cache_file)
        if cached is not None:
            return cached

    print("=" * 50)
    print("COLETA DE DADOS - GBIF API")
    print("=" * 50)

    species_list = ["Tubastraea coccinea", "Tubastraea tagusensis"]
    all_dfs = []

    for species in species_list:
        print(f"\nBuscando: {species}")
        print("-" * 30)

        # Passo 1: encontrar o taxonKey
        taxon_key = search_species_key(species)

        # Passo 2: buscar ocorrencias
        raw = fetch_occurrences(taxon_key)

        # Passo 3: transformar em DataFrame
        df = parse_occurrences(raw)
        print(f"  Registros validos: {len(df)}")

        all_dfs.append(df)

    # Consolida tudo em um unico DataFrame
    df_final = pd.concat(all_dfs, ignore_index=True)

    # Remove duplicatas pelo gbif_id
    before = len(df_final)
    df_final = df_final.drop_duplicates(subset=["gbif_id"])
    dupes = before - len(df_final)
    if dupes > 0:
        print(f"\nRemovidas {dupes} duplicatas.")

    print(f"\nTotal final: {len(df_final)} registros")
    print(f"Especies: {df_final['species'].value_counts().to_dict()}")
    print(f"Periodo: {df_final['year'].min()} a {df_final['year'].max()}")

    # Salva no cache
    save_to_cache(df_final, cache_file)

    return df_final


# Permite rodar o modulo diretamente para teste
if __name__ == "__main__":
    df = collect_tubastraea_data(use_cache=False)
    print("\nAmostra dos dados:")
    print(df.head(10).to_string())
    print(f"\nColunas: {list(df.columns)}")