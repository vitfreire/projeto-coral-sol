import requests
import pandas as pd
import os

# Configuração de caminhos baseada no seu Plano de Projeto v2.0
# Estrutura: coral-sol-predicao/data/cache
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ajuste o caminho para subir até a pasta data/cache a partir de scripts/ingestao/
PROJETO_RAIZ = os.path.dirname(os.path.dirname(BASE_DIR))
CACHE_DIR = os.path.join(PROJETO_RAIZ, "data", "cache")

def fetch_depth(lat: float, lon: float) -> float:
    """
    Busca a profundidade (m) para uma coordenada via API OpenTopography.
    O coral-sol coloniza diferentes profundidades, mas prefere substratos duros.
    """
    # API gratuita de elevação/batimetria (GEBCO 2020) [cite: 234]
    url = f"https://api.opentopodata.org/v1/gebco2020?locations={lat},{lon}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data['status'] == 'OK':
            # Elevação negativa indica profundidade marinha (abaixo do nível do mar) [cite: 250]
            return float(data['results'][0]['elevation'])
        return None
    except Exception as e:
        print(f"Erro ao buscar profundidade para ({lat}, {lon}): {e}")
        return None

def save_depth_cache(df: pd.DataFrame):
    """Salva dados de batimetria no cache conforme o RNF02 (execução local). [cite: 158, 219]"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    
    path = os.path.join(CACHE_DIR, "ambient_bathymetry.csv")
    df.to_csv(path, index=False)
    print(f"  [OK] Cache de batimetria salvo em: {path}")

# --- BLOCO DE TESTE ADICIONADO ---
if __name__ == "__main__":
    print(f"{'='*60}\nTESTE DE INGESTAO - BATIMETRIA (GEBCO)\n{'='*60}")
    
    # Coordenadas de teste baseadas em pontos críticos do seu projeto [cite: 250]
    pontos_teste = {
        "Arraial do Cabo/RJ (Raso)": (-22.97, -42.02),
        "Bacia de Campos (Plataformas)": (-22.50, -40.50),
        "Ponto Terrestre (Controle)": (-22.90, -43.17)
    }

    resultados = []

    for local, (lat, lon) in pontos_teste.items():
        print(f"Consultando profundidade para {local}...")
        depth = fetch_depth(lat, lon)
        
        if depth is not None:
            status = "MARINHO (OK)" if depth < 0 else "TERRESTRE/COSTA"
            print(f"  -> Resultado: {depth} metros ({status})")
            resultados.append({
                "local": local, 
                "latitude": lat, 
                "longitude": lon, 
                "depth_m": depth
            })
        else:
            print(f"  [!] Falha ao obter dados para {local}")

    # Salva o teste no cache se houver resultados
    if resultados:
        df_teste = pd.DataFrame(resultados)
        save_depth_cache(df_teste)
        print(f"\nTeste concluído. {len(resultados)} registros processados.")