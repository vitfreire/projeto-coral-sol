import os
import pandas as pd
import xarray as xr
import copernicusmarine

# Configuração de caminhos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJETO_RAIZ = os.path.dirname(os.path.dirname(BASE_DIR))
CACHE_DIR = os.path.join(PROJETO_RAIZ, "data", "cache")

def download_brazil_currents(start_date: str, end_date: str):
    """
    Baixa os dados de correntes (NetCDF) para a costa do Brasil via Copernicus.
    Utiliza o produto de Reanálise Global Física (diário).
    """
    print(f"Iniciando download de correntes ({start_date} a {end_date})...")
    os.makedirs(CACHE_DIR, exist_ok=True)
    output_filename = "copernicus_currents_br.nc"
    output_path = os.path.join(CACHE_DIR, output_filename)

    # Limites geográficos aproximados da costa brasileira (Bacia de Campos até o Nordeste)
    lon_min, lon_max = -50.0, -30.0
    lat_min, lat_max = -30.0, 5.0

    try:
        # Chama a API oficial do Copernicus
        # O produto GLORYS12V1 (GLOBAL_MULTIYEAR_PHY_001_030) é o padrão ouro para dados históricos
        copernicusmarine.subset(
            dataset_id="cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m", # <-- Adicione o '-cur' no nome
            variables=["uo", "vo"], 
            start_datetime=f"{start_date}T00:00:00",
            end_datetime=f"{end_date}T00:00:00",
            minimum_longitude=lon_min,
            maximum_longitude=lon_max,
            minimum_latitude=lat_min,
            maximum_latitude=lat_max,
            minimum_depth=0, 
            maximum_depth=1,
            output_directory=CACHE_DIR,
            output_filename=output_filename,
            overwrite=True
        )
        print(f"  [OK] Arquivo NetCDF salvo em: {output_path}")
        return output_path
    
    except Exception as e:
        print(f"  [ERRO] Falha no download do Copernicus: {e}")
        return None

def extract_current_for_point(nc_path: str, lat: float, lon: float, date: str) -> dict:
    """
    Lê o arquivo NetCDF cacheado e extrai a corrente para um ponto específico.
    Esta função será usada pelo construir_abt.py durante o cruzamento.
    """
    if not os.path.exists(nc_path):
        print("Arquivo NetCDF não encontrado no cache.")
        return None

    try:
        # Abre o dataset usando xarray
        ds = xr.open_dataset(nc_path)
        
        # Seleciona o ponto mais próximo no espaço e no tempo
        point_data = ds.sel(
            time=date,
            latitude=lat,
            longitude=lon,
            method="nearest"
        )
        
        uo_val = float(point_data["uo"].values.item())
        vo_val = float(point_data["vo"].values.item())
        
        # Calcula a velocidade absoluta da corrente (Teorema de Pitágoras)
        velocity = (uo_val**2 + vo_val**2)**0.5
        
        return {
            "uo": uo_val,
            "vo": vo_val,
            "current_velocity": velocity
        }
    except Exception as e:
        print(f"Erro ao extrair dado do NetCDF: {e}")
        return None

# --- BLOCO DE TESTE ---
if __name__ == "__main__":
    print(f"{'='*60}\nTESTE DE INGESTAO - CORRENTES (COPERNICUS)\n{'='*60}")
    
    # ATENÇÃO: Para este teste rodar, você deve primeiro fazer login no terminal usando:
    # copernicusmarine login
    
    # testa o download de um único dia recente para ser rápido
    data_teste = "2023-01-01"
    
    nc_file = download_brazil_currents(start_date=data_teste, end_date=data_teste)
    
    if nc_file:
        print("\nTestando extração para Arraial do Cabo/RJ...")
        resultado = extract_current_for_point(
            nc_path=nc_file,
            lat=-22.97,
            lon=-42.03,
            date=data_teste
        )
        
        if resultado:
            print(f"  -> uo (Leste/Oeste): {resultado['uo']:.3f} m/s")
            print(f"  -> vo (Norte/Sul): {resultado['vo']:.3f} m/s")
            print(f"  -> Velocidade Absoluta: {resultado['current_velocity']:.3f} m/s")