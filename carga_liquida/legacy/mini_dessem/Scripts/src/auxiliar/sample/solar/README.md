# Gerador de Perfis Horários Solares

## 📋 Descrição

Módulo para gerar perfis horários de geração solar baseado em dados históricos.

**Input**: Mês + Potência Média Mensal (MWmédios)  
**Output**: Array com **24 valores** (perfil de UM dia típico)

**Importante**: O input é em **MWmédios**, que é a energia total dividida pelo número de horas:
```
MWmédios = Energia Total Mensal (MWh) / Número de Horas no Mês
```

**Exemplo**: Para Janeiro (744 horas) com 120.000 MWh total no mês:
- MWmédios = 120.000 MWh ÷ 744 h = **161,29 MW**
- Output: 24 valores representando um dia típico de ~3.871 MWh

## 🚀 Como Usar

### 1. Processar Perfis Históricos (Executar uma vez)

```bash
python processar_perfis_solares.py
```

Isso gera:
- `output/sample/solar/perfis_horarios.json` - Parâmetros do modelo
- `output/sample/solar/perfis_horarios.csv` - Perfis em formato tabular

### 2. Usar o Sampler

```python
from solar_sampler import SolarSampler

# Criar sampler
sampler = SolarSampler()

# Gerar perfil de UM DIA TÍPICO
# Janeiro: 120.000 MWh / 744 horas = 161,29 MWmédios
perfil_dia = sampler.gerar_perfil_dia(
    mes=1,                     # Janeiro
    mw_medios=161.29           # Potência média do mês
)
# Retorna: array com 24 valores (MWh por hora de um dia típico)
# Total do dia: ~3.871 MWh
```

### 3. Funções de Conveniência

```python
from solar_sampler import gerar_dia_tipico

# Gerar perfil de um dia típico
# Junho com 105.000 MWh total mensal
# 720 horas no mês → 105.000 / 720 = 145,83 MWmédios
perfil_dia = gerar_dia_tipico(mes=6, mw_medios=145.83)

# Retorna: array com 24 valores (um dia típico de ~3.500 MWh)
```

## 📊 Estrutura de Diretórios

```
mini_dessem/
├── output/
│   └── sample/
│       └── solar/
│           ├── perfis_horarios.json         # Parâmetros do modelo
│           ├── perfis_horarios.csv          # Perfis em CSV
│           └── backtest/
│               ├── metricas_backtest.csv    # Métricas de validação
│               └── backtest_perfis_solares.png  # Gráficos
│
└── Scripts/
    └── src/
        └── auxiliar/
            └── sample/
                └── solar/
                    ├── __init__.py
                    ├── processar_perfis_solares.py   # Script de processamento
                    ├── solar_sampler.py              # Classe principal
                    ├── backtest_perfis_solares.py    # Validação
                    └── README.md                     # Este arquivo
```

## 📈 Características dos Perfis

- **12 perfis mensais** (um para cada mês do ano)
- **Hora de pico típica**: 11h-12h (meio-dia solar)
- **Geração noturna**: ~0 MWh (0h-5h, 19h-23h)
- **Distribuição diária**: Uniforme (cada dia recebe 1/N do total mensal)

## ⚠️ Observações

- **Sem ajuste por dia da semana**: Geração solar não depende de dia útil vs fim de semana
- **Perfis baseados em médias históricas**: Capturam padrão típico de cada mês
- **Normalização garantida**: A soma horária sempre iguala o total fornecido

## 🔬 Validação

Execute o backtest para validar a qualidade dos perfis:

```bash
python backtest_perfis_solares.py
```

Métricas calculadas:
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- MAPE (Mean Absolute Percentage Error) - apenas horas com geração > 100 MWh
- R² (Coeficiente de determinação)

## 📝 Exemplo Completo

```python
from solar_sampler import SolarSampler
import numpy as np

# Inicializar
sampler = SolarSampler()

# Cenário: Gerar perfil de um dia típico de Junho
# Se o mês tem 110.000 MWh total
# Junho tem 720 horas (30 dias × 24h)
# MWmédios = 110.000 MWh / 720 h = 152,78 MW
mw_medios = 152.78

perfil_dia = sampler.gerar_perfil_dia(mes=6, mw_medios=mw_medios)

print(f"Input: {mw_medios:.2f} MWmédios")
print(f"Output: {len(perfil_dia)} valores (um dia típico)")
print(f"Total do dia: {perfil_dia.sum():,.2f} MWh")
print(f"Hora de pico: {perfil_dia.argmax()}h")

# Se quiser simular o mês inteiro, chame 30 vezes:
perfis_mes = [sampler.gerar_perfil_dia(6, mw_medios) for _ in range(30)]
total_mes = sum(p.sum() for p in perfis_mes)
print(f"Total do mês (30 dias): {total_mes:,.2f} MWh")
```

## 📞 Suporte

Desenvolvido para ONS - Operador Nacional do Sistema Elétrico
Versão: 1.0.0
Data: Novembro 2024

