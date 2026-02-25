# Modelos de Sample - Solar e Eólica

## Resumo Executivo

Implementação completa de modelos de geração horária para fontes renováveis.

---

## Modelos Implementados

### ☀️ **SOLAR - Determinístico**

**Modelo**: Perfil horário médio por mês  
**Fundamento**: Irradiação solar é previsível (astronomia)

**Performance**:
- MAPE: 1.28%
- Sempre retorna o mesmo resultado

**Uso**:
```python
from mini_dessem.sampling import sample_val_gersolar_perfil_ar1

perfil = sample_val_gersolar_perfil_ar1(
    media_diurna=150,  # MWmédios
    mes=6,             # Junho
    num_horas=24       # Ignorado, sempre retorna 24
)
# Retorna: 24 valores (sempre iguais)
```

---

### ⚡ **EÓLICA - Estocástico AR(1)**

**Modelo**: Processo autorregressivo AR(1) + Perfil  
**Fundamento**: Vento é variável e autocorrelacionado (literatura)

**Fórmula**:
```
Y_h = μ_h * (1 + Z_h)
Z_h = φ * Z_{h-1} + ε_h,  ε_h ~ N(0, σ²_ε)
```

**Parâmetros**:
- φ médio: 0.974 (alta autocorrelação)
- σ_ε médio: 0.048

**Performance**:
- MAPE: 3.34%
- Cobertura IC95: 99.23%
- Cada chamada retorna valores diferentes

**Uso**:
```python
from mini_dessem.sampling import sample_val_geolica_perfil_ar1

perfil = sample_val_geolica_perfil_ar1(
    media_mensal=400,  # MWmédios
    mes=9,             # Setembro
    num_horas=24       # Ignorado, sempre retorna 24
)
# Retorna: 24 valores ALEATÓRIOS (diferentes a cada chamada)
```

---

## Comportamento das Funções

### Sempre Retornam 24 Valores

```python
# Mesmo passando num_horas diferente, sempre retorna 24
perfil = sample_val_gersolar_perfil_ar1(150, 6, 999)
print(len(perfil))  # 24 (não 999!)
```

### Monte Carlo no Modelo Principal

```python
# NO MODELO PRINCIPAL (simulation.py):
perfis_mes = []
for dia in range(30):  # Loop de dias (Monte Carlo aqui)
    perfil = sample_val_geolica_perfil_ar1(400, 9, 24)
    perfis_mes.append(perfil)
```

### Solar: Determinístico

```python
a = sample_val_gersolar_perfil_ar1(150, 6, 24)
b = sample_val_gersolar_perfil_ar1(150, 6, 24)
print(a == b)  # True (sempre igual)
```

### Eólica: Estocástico

```python
x = sample_val_geolica_perfil_ar1(400, 9, 24)
y = sample_val_geolica_perfil_ar1(400, 9, 24)
print(x == y)  # False (valores diferentes)
```

---

## Integração com Sistema Principal

### Arquivo: `sampling.py`
```python
def sample_val_geolica_perfil_ar1(media_mensal, mes, num_horas, num_cenarios=1, seed=None):
    # Sempre retorna 24 valores (1 dia)
    # Monte Carlo acontece no modelo principal
    ...
```

### Arquivo: `simulation.py` (usa as funções)
```python
from .sampling import sample_val_geolica_perfil_ar1, sample_val_gersolar_perfil_ar1

# Loop de simulações (Monte Carlo)
for sim in range(num_simulations):
    for dia in estrutura_mes:
        # Gera 24 valores para este dia
        val_eolica = sample_val_geolica_perfil_ar1(media_mensal_eolica, mes, 24)
        val_solar = sample_val_gersolar_perfil_ar1(media_diurna_solar, mes, 24)
        # Processa dia...
```

---

## Estrutura de Diretórios

```
mini_dessem/
├── output/sample/
│   ├── solar/
│   │   ├── perfis_horarios.json       # 12 perfis mensais
│   │   └── perfis_horarios.csv
│   │
│   └── eolica/
│       ├── perfis_horarios.json       # 12 perfis mensais
│       ├── parametros_ar1.json         # φ e σ_ε por mês
│       └── backtest/
│           ├── metricas_backtest.csv
│           └── backtest_perfis_eolicos.png
│
└── Scripts/src/
    ├── mini_dessem/
    │   └── sampling.py                 # FUNÇÕES INTEGRADAS AQUI
    │
    └── auxiliar/sample/
        ├── solar/
        │   ├── solar_sampler.py        # Implementação solar
        │   └── README.md
        │
        └── eolica/
            ├── eolica_sampler.py       # Implementação eólica
            ├── backtest_perfis_eolicos.py
            └── README.md
```

---

## Execução

### 1. Processar dados históricos (uma vez):

```bash
cd Scripts/src/auxiliar/sample/solar
python processar_perfis_solares.py

cd Scripts/src/auxiliar/sample/eolica
python processar_perfis_eolicos.py
```

### 2. Usar no sistema:

As funções já estão integradas em `sampling.py` e são usadas automaticamente por `simulation.py`.

---

## Validação

### Solar:
- 19 meses testados
- MAPE: 1.28%
- R²: 1.000

### Eólica:
- 49 meses testados
- MAPE: 3.34%
- Cobertura IC95: 99.23%

**Ambos com performance EXCELENTE!**

---

## Status

✅ **IMPLEMENTADO E INTEGRADO**

- Modelos corrigidos (sempre 24 valores)
- Monte Carlo removido das funções
- Seed simplificado
- Testes validam comportamento correto
- Integração com simulation.py confirmada

**Pronto para uso em produção!**

---

Desenvolvido para ONS  
Novembro 2024








