# Análise Histórico

Scripts para processar e analisar dados históricos.

## Arquivos

### `run_historical_analysis.py`
Executa análise histórica dos dados em `Data/raw_data/`.

**Uso:**
```bash
python src/analise_historico/run_historical_analysis.py
```

**Saída:**
- Gráficos e análises em `output/analise_historica/`

---

### `calcular_geracao_distribuida_solar.py`
Calcula separação de geração solar em centralizada e distribuída.

**Processo:**
1. Lê dados de `BALANCO_ENERGIA_SUBSISTEMA_*.xlsx`
2. Lê dados de curtailment (centralizada)
3. Calcula: Distribuída = Total - Centralizada
4. Gera perfis horários para cada componente

**Uso:**
```bash
python src/analise_historico/calcular_geracao_distribuida_solar.py
```

**Saída:**
- `output/sample/solar_distribuida/` (4 arquivos)

**Período:** 2024-04 a 2025-10







