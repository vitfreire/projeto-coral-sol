# Sistema de Inteligência Preditiva: Bioinvasão Marinha (Coral-Sol)

![Python](https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32.0-FF4B4B?style=for-the-badge&logo=streamlit)
![Scikit-Learn](https://img.shields.io/badge/Scikit_Learn-Machine_Learning-F7931E?style=for-the-badge&logo=scikit-learn)
![Plotly](https://img.shields.io/badge/Plotly-Data_Viz-3F4F75?style=for-the-badge&logo=plotly)
![Folium](https://img.shields.io/badge/Folium-Geospatial-77B829?style=for-the-badge)

> **Resumo Executivo:** Uma Prova de Conceito (PoC) de Data Science que transforma o monitoramento reativo de espécies marinhas invasoras numa operação preditiva. Utilizando Machine Learning, o sistema cruza vetores oceanográficos e antrópicos para prever nichos de fixação do *Tubastraea spp.* (Coral-Sol) com 30 a 90 dias de antecedência.

---

## 🎯 O Desafio e a Solução

A invasão do Coral-Sol ameaça a biodiversidade da costa brasileira. Atualmente, a gestão ambiental atua de forma **reativa** (remoção manual após deteção visual). 

Este projeto propõe uma abordagem **preditiva**. Ao analisar a temperatura da superfície do mar (SST), correntes marítimas e a distância de infraestruturas offshore (plataformas de petróleo), o algoritmo de Machine Learning mapeia zonas de alta vulnerabilidade, permitindo que a remoção ocorra fora do pico reprodutivo da espécie, evitando a dispersão larval.

## 🔬 Inovação Técnica: Mitigação de *Data Leakage*

Durante a fase de Análise Exploratória (EDA), identificou-se um vazamento de dados geográficos severo: a IA atingia acurácia quase perfeita ao apenas memorizar a diferença entre o relevo abissal (ausências aleatórias) e a costa oceânica (presença do coral).

**A Correção (Hard Negatives):**
Para garantir a validade biológica do modelo, aplicámos a técnica de *Hard Negatives*, forçando a geração de pseudo-ausências estritamente sobre a plataforma continental rasa. Isto obrigou o modelo a abandonar a batimetria profunda como "muleta" preditiva e a aprender os reais gatilhos de invasão vetorial.

### 🏆 Performance do Modelo Campeão
Após testes com múltiplos algoritmos (SVM, KNN, Logistic Regression, Gradient Boosting), o **Random Forest Classifier** foi promovido a produção:
- **ROC-AUC (Poder de Separação):** 0.893
- **Acurácia Global:** 73.33%

---

## 📊 Funcionalidades do Dashboard (Streamlit)

O painel foi desenhado para tomadores de decisão (C-Level/Gestores Ambientais) e oferece:
1. **Mapeamento Espacial de Calor:** Um mapa responsivo (Folium) que projeta o raio de impacto dinamicamente com base nas coordenadas inseridas.
2. **Motor de Explicabilidade (Waterfall):** Gráficos Plotly que abrem a "caixa preta" da IA, demonstrando visualmente qual variável (Proximidade ANP, Profundidade ou Correntes) teve mais peso para a classificação de risco atual.
3. **Métricas Executivas:** KPIs instantâneos de nível de alerta e confiabilidade.

## ⚙️ Fontes de Dados (Data Ingestion)
- **GBIF API:** Ocorrências biológicas georreferenciadas.
- **NOAA / Copernicus Marine:** Tensores oceanográficos e anomalias térmicas.
- **GEBCO:** Batimetria de alta resolução.
- **ANP:** Malha de coordenadas de infraestrutura de exploração de petróleo.

---
Projeto concebido e desenvolvido por Vitória Freire no âmbito da Pós-Graduação em IA e Ciência de Dados (2026).
