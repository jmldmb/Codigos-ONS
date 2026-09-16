# Gerador Estocástico de Perfis Horários Eólicos (AR(1))

## 📋 Descrição

Modelo **estocástico** para gerar perfis horários de geração eólica baseado em:
- **Perfil horário médio** por mês (determinístico)
- **Processo AR(1)** para variabilidade estocástica (literatura)

**Input**: Mês + Potência Média Mensal (MWmédios)  
**Output**: Array com **24 valores estocásticos** (perfil de UM dia)

## 🔬 Modelo Matemático

```
Y_h = μ_h * (1 + Z_h)
```

Onde:
- `Y_h` = Geração na hora h (MWh)
- `μ_h` = Perfil horário médio (MWh)
- `Z_h` = Processo AR(1): `Z_h = φ * Z_{h-1} + ε_h`, com `ε_h ~ N(0, σ²_ε)`

### Parâmetros Estimados

| Parâmetro | Valor Médio | Descrição |
|-----------|-------------|-----------|
| **φ** (phi) | 0.974 | Autocorrelação (persistência temporal) |
| **σ_ε** | 0.048 | Desvio padrão do ruído branco |

**φ = 0.974** indica **alta autocorrelação**: geração de uma hora influencia fortemente a próxima.

## 📊 Performance do Modelo (Backtest)

| Métrica | Valor | Interpretação |
|---------|-------|---------------|
| **MAPE** | **3.34%** | ⭐ EXCELENTE |
| **Cobertura IC95** | **99.23%** | ⭐ PERFEITA (esperado: 95%) |
| **Correlação** | **0.974** | Alta aderência |
| **Autocorr. Resíduos** | 0.889 | ⚠️ Ainda correlacionados |

### Interpretação:
- ✅ **MAPE < 5%**: Perfil médio muito preciso
- ✅ **Cobertura ~95%**: Incerteza bem calibrada
- ⚠️ **Resíduos correlacionados**: AR(1) captura bem, mas poderia melhorar com ARMA

## 🚀 Como Usar

### 1. Processar Perfis Históricos (Executar uma vez)

```bash
python processar_perfis_eolicos.py
```

Gera:
- `output/sample/eolica/perfis_horarios.json` - Perfis μ_h
- `output/sample/eolica/parametros_ar1.json` - Parâmetros φ, σ_ε

### 2. Gerar Perfil Estocástico

```python
from eolica_sampler import EolicaSampler

sampler = EolicaSampler()

# Gerar UM dia com variabilidade estocástica
# Setembro: 300.000 MWh / 720 horas = 416,67 MWmédios
perfil_dia = sampler.gerar_perfil_dia(
    mes=9,              # Setembro
    mw_medios=416.67,   # Potência média
    seed=42             # Para reprodutibilidade
)

# Resultado: 24 valores estocásticos
print(f"Total: {perfil_dia.sum():.2f} MWh")  # ~10.000 MWh
```

### 3. Gerar Múltiplos Cenários

```python
# Gerar 100 cenários para análise de risco
cenarios = sampler.gerar_multiplos_cenarios(
    mes=9,
    mw_medios=416.67,
    n_cenarios=100,
    seed=42
)

# Resultado: array (100, 24)
# Calcular estatísticas
media = cenarios.mean(axis=0)
p05 = np.percentile(cenarios, 5, axis=0)
p95 = np.percentile(cenarios, 95, axis=0)
```

### 4. Perfil Determinístico (Sem Ruído)

```python
# Se quiser apenas o perfil médio (sem variabilidade)
perfil_det = sampler.gerar_perfil_dia(
    mes=9,
    mw_medios=416.67,
    deterministico=True  # Sem ruído AR(1)
)
```

## 📁 Estrutura de Diretórios

```
mini_dessem/
├── output/
│   └── sample/
│       └── eolica/
│           ├── perfis_horarios.json       # Perfis μ_h por mês
│           ├── perfis_horarios.csv        # Mesmos dados em CSV
│           ├── parametros_ar1.json        # Parâmetros φ, σ_ε
│           └── backtest/
│               ├── metricas_backtest.csv
│               └── backtest_perfis_eolicos.png
│
└── Scripts/
    └── src/
        └── auxiliar/
            └── sample/
                └── eolica/
                    ├── __init__.py
                    ├── processar_perfis_eolicos.py
                    ├── eolica_sampler.py         # Classe principal
                    ├── backtest_perfis_eolicos.py
                    ├── analise_exploratoria.py
                    └── README.md
```

## 🌬️ Características da Geração Eólica

### Diferenças vs Solar:
- **Pico**: 22-23h (noite/madrugada) vs 11-12h (meio-dia)
- **Geração noturna**: Significativa (~13.000 MWh) vs ~0 MWh
- **Variação horária**: 40% vs 100%
- **Autocorrelação**: 0.974 (alta) vs 0.999 (determinístico)

### Perfil Típico:
- **Menor geração**: 13-14h (tarde)
- **Maior geração**: 22-23h (noite)
- **Padrão**: Inverso ao solar (vento mais forte à noite)

## 🔧 Validação (Backtest)

Execute para validar:

```bash
python backtest_perfis_eolicos.py
```

Métricas calculadas:
- MAE, RMSE, MAPE (perfil médio)
- Cobertura de IC95 (calibração da incerteza)
- Autocorrelação dos resíduos (adequação do AR(1))
- Correlação real vs previsto

## 📝 Exemplo Completo

```python
from eolica_sampler import EolicaSampler
import numpy as np

# Inicializar
sampler = EolicaSampler()

# Cenário: Setembro com 300.000 MWh total mensal
# 720 horas → MWmédios = 300.000 / 720 = 416,67 MW
mw_medios = 416.67

# Gerar 1 cenário
perfil = sampler.gerar_perfil_dia(mes=9, mw_medios=mw_medios, seed=42)
print(f"Total: {perfil.sum():.0f} MWh")
print(f"Pico: {perfil.max():.0f} MWh na hora {perfil.argmax()}h")

# Gerar múltiplos cenários
cenarios = sampler.gerar_multiplos_cenarios(9, mw_medios, n_cenarios=1000, seed=42)
print(f"\nEstatísticas (1000 cenários):")
print(f"  Média: {cenarios.mean():.2f} MWh/h")
print(f"  P05-P95: [{np.percentile(cenarios, 5):.0f}, {np.percentile(cenarios, 95):.0f}] MWh")
```

## ⚠️ Observações Importantes

### Diferença vs Solar:
**EÓLICA é ESTOCÁSTICA**, **SOLAR é DETERMINÍSTICA**

- **Solar**: Perfil determinístico (sol nasce/se põe sempre igual)
- **Eólica**: Perfil estocástico (vento é variável e imprevisível)

### Reprodutibilidade:
Use `seed` para resultados reproduzíveis:
```python
perfil1 = sampler.gerar_perfil_dia(9, 400, seed=42)
perfil2 = sampler.gerar_perfil_dia(9, 400, seed=42)
# perfil1 == perfil2 ✓
```

### Autocorrelação Alta:
O modelo AR(1) captura que geração em horas consecutivas é correlacionada (φ = 0.974).
Se precisar de mais realismo, considere ARMA(p,q) no futuro.

## 📞 Suporte

Desenvolvido para ONS - Operador Nacional do Sistema Elétrico  
Versão: 1.0.0  
Data: Novembro 2024








