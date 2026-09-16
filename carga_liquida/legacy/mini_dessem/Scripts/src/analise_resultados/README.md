# Análise de Resultados

Scripts para analisar resultados das simulações.

## Arquivos

### `analise_simulacoes.py`
Análise completa dos resultados de simulação.

**Funcionalidades:**
- Perfis horários (eólica, solar, carga, térmica)
- Análise de curtailment
- Análise de PLD
- Gráficos e estatísticas

**Uso:**
```bash
# Analisar arquivo mais recente
python src/analise_resultados/analise_simulacoes.py --ultimo

# Analisar arquivo específico
python src/analise_resultados/analise_simulacoes.py --arquivo output/resultados/resultados_*.parquet
```

**Saída:**
- `output/resultados/analises/` (gráficos e estatísticas)

---

### `analisar_geracao_distribuida.py`
Análise das características da geração solar distribuída.

**Funcionalidades:**
- Comparação centralizada vs distribuída
- Validação de hipótese (perfis são diferentes?)
- Estatísticas por mês

**Uso:**
```bash
python src/analise_resultados/analisar_geracao_distribuida.py
```

---

### `comparar_perfis_centralizado_distribuido.py`
Gera gráficos comparativos de perfis solar.

**Funcionalidades:**
- 12 gráficos mensais (centralizada vs distribuída)
- Perfil médio anual
- Gráfico de diferenças

**Uso:**
```bash
python src/analise_resultados/comparar_perfis_centralizado_distribuido.py
```

**Saída:**
- `comparacao_perfis_solar_cent_dist.png`
- `perfil_medio_solar_comparacao.png`







