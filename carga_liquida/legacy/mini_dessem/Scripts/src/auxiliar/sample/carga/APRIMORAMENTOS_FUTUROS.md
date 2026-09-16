# APRIMORAMENTOS FUTUROS - MODELO DE CARGA V6

## Data: Novembro 2025

---

## 1. AJUSTE PARA EXTREMOS DE TEMPERATURA

### Problema Identificado
O modelo V6 apresenta subestimação em dias com temperatura anormalmente alta (>1σ acima da média mensal).

**Exemplo:**
- Período 21-24 Janeiro 2025
- Temperatura: 27°C (média janeiro: 23°C, +4°C, +1.4σ)
- MAPE do período: 6.56% (vs 4.98% do mês completo)
- Erro médio: -6,000 MW (subestimação)

### Hipótese
- Relação **não-linear** entre temperatura e carga em extremos
- Efeito multiplicativo de ar-condicionado em dias muito quentes
- Modelo atual usa relação **linear** (slope × temperatura)

### Proposta de Aprimoramento

#### Opção A: Termo Quadrático para Extremos
```python
# Identificar quando temperatura está em extremo (>P75 ou <P25)
if temp > temp_p75:
    boost_calor = k_calor × (temp - temp_p75)²
elif temp < temp_p25:
    boost_frio = k_frio × (temp_p25 - temp)²

carga_normalizada += boost
```

#### Opção B: Regressão Não-Linear
- Treinar modelo com termos quadráticos ou cúbicos
- Foco em capturar comportamento nos percentis 10 e 90

#### Opção C: Modelo Segmentado (Piecewise)
- Diferentes coeficientes para faixas de temperatura:
  - Frio: temp < P25
  - Normal: P25 ≤ temp ≤ P75
  - Quente: temp > P75

### Impacto Esperado
- Redução de MAPE em dias extremos de 6.5% para ~4.5%
- Melhoria do erro P90 de -1.70% para ~-1.0%

### Trade-offs
- Maior complexidade do modelo
- Risco de overfitting nos extremos
- Pode desestabilizar performance em dias normais

---

## 2. OUTROS APRIMORAMENTOS POTENCIAIS

### 2.1. Incorporar Variáveis Macroeconômicas
- PIB mensal
- Índice de atividade industrial
- Ajustar carga mensal por crescimento econômico

### 2.2. Considerar Eventos Especiais
- Jogos de futebol (Copa, Olimpíadas)
- Greves ou paralisações
- Blackouts ou restrições

### 2.3. Sazonalidade Intra-Mês
- Diferença entre início/meio/fim de mês
- Dias de pagamento (aumenta consumo)

### 2.4. Umidade Relativa
- Adicionar umidade como variável explicativa
- Interação temperatura × umidade (sensação térmica)

### 2.5. Modelo Ensemble
- Combinar V6 (determinístico) com modelo estocástico
- Gerar cenários com variabilidade calibrada

---

## 3. PERFORMANCE ATUAL DO MODELO V6

### Métricas Globais (Mai/2023 - Out/2025)
- **MAPE**: 3.75%
- **MAE**: 2,839 MW
- **RMSE**: 3,920 MW
- **Bias**: -0.01% (praticamente zero!)
- **R²**: 0.8491

### Erro por Quantil
- **P50**: +0.18%
- **P75**: +0.44%
- **P90**: -1.70%
- **P95**: -2.39%
- **P99**: -1.78%

### Principais Características
✅ Regressões separadas DU vs FDS
✅ Sensibilidade à temperatura por (mês, hora, tipo_dia)
✅ Constraint matemático (soma = 24)
✅ Ajuste fino de viés aplicado
✅ Preserva física do modelo (slopes intactos)

---

## 4. QUANDO IMPLEMENTAR

### Prioridade BAIXA
O modelo atual já tem performance excelente (MAPE 3.75%).

### Gatilhos para Implementação
1. Se erro P90 se tornar crítico (>3%)
2. Se houver aumento de dias extremos (mudança climática)
3. Se surgir necessidade de prever cenários de stress térmico
4. Se dados de treinamento forem expandidos (mais histórico)

---

## 5. REFERÊNCIAS

- Backtest completo: `output/sample/carga_v6_com_constraint/`
- Análise de dias extremos: `output/analise_historica/carga/51_investigacao_21_24_jan_2025.png`
- Parâmetros do modelo: `output/sample/carga_v6/regressoes_v6.parquet`

---

**Autor**: Sistema de IA de Desenvolvimento
**Última atualização**: Novembro 2025





