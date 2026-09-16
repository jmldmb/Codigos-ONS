# ✅ Modelo de Perfis Horários Solares - ENTREGUE

## 📋 O Que Foi Desenvolvido

Um sistema **simplificado** que recebe:
- **Input**: Mês (1-12) + **Potência Média Mensal (MWmédios)**
- **Output**: Array com **24 valores** (perfil de UM dia típico)

**Sem previsão mensal** - apenas desagregação horária de um dia típico!

### ⚡ Importante: Input em MWmédios

O input é em **MWmédios** (potência média), não energia total:

```
MWmédios = Energia Total (MWh) / Número de Horas no Período
```

**Exemplo**: 
- Janeiro tem 744 horas (31 dias × 24h)
- Se energia total = 120.000 MWh
- **MWmédios = 120.000 ÷ 744 = 161,29 MW** ← Este é o input!

## 📁 Estrutura de Arquivos (Organizada)

### ✅ Parâmetros do Modelo
```
C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem\output\sample\solar\
├── perfis_horarios.json       # 12 perfis mensais (proporções horárias)
└── perfis_horarios.csv         # Mesmos dados em CSV
```

### ✅ Backtest / Validação
```
C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem\output\sample\solar\backtest\
├── metricas_backtest.csv              # Métricas de erro
└── backtest_perfis_solares.png        # Visualizações
```

### ✅ Scripts
```
C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem\Scripts\src\auxiliar\sample\solar\
├── __init__.py                        # Módulo Python
├── processar_perfis_solares.py       # [1] Processar dados históricos
├── solar_sampler.py                  # [2] Classe principal de uso
├── backtest_perfis_solares.py        # [3] Validação
└── README.md                          # Documentação
```

## 🚀 Como Usar

### Opção 1: Usar a Classe

```python
from auxiliar.sample.solar import SolarSampler

sampler = SolarSampler()

# Gerar perfil de UM dia típico
# Dezembro: 124.000 MWh total mensal / 744 horas = 166,67 MWmédios
perfil_dia = sampler.gerar_perfil_dia(
    mes=12,                    # Dezembro
    mw_medios=166.67           # Potência média do mês
)
# Retorna: array com 24 valores (MWh/hora de um dia típico)
# Total do dia: ~4.000 MWh

# Para simular o mês inteiro, gere 31 dias:
perfis_mes = [sampler.gerar_perfil_dia(12, 166.67) for _ in range(31)]
```

### Opção 2: Funções Diretas

```python
from auxiliar.sample.solar import gerar_dia_tipico

# Gerar dia típico
# Junho com 105.000 MWh total mensal
# 720 horas no mês → 105.000 / 720 = 145,83 MWmédios
perfil_dia = gerar_dia_tipico(mes=6, mw_medios=145.83)
# Retorna: array com 24 valores (um dia típico)
```

## 📊 Características

✅ **12 perfis mensais** - Um para cada mês do ano  
✅ **Baseado em dados reais** - Médias históricas de Abr/2024 a Out/2025  
✅ **Sem ajuste semanal** - Geração solar não depende de dia útil/FDS  
✅ **Hora de pico típica** - 11h-12h (meio-dia solar)  
✅ **Normalização garantida** - Soma sempre iguala o total fornecido  

## 🔧 Ajustes Feitos

1. ✅ **Removido modelo de previsão mensal** - Agora recebe total mensal como input
2. ✅ **Arquivos organizados** nos diretórios corretos:
   - Parâmetros: `output/sample/solar/`
   - Backtest: `output/sample/solar/backtest/`
   - Scripts: `Scripts/src/auxiliar/sample/solar/`
3. ✅ **Removida diferenciação dia útil/FDS** - Não faz sentido para solar
4. ✅ **Arquivos antigos deletados** do diretório raiz

## 📈 Perfis Gerados

| Mês | Nome | Hora Pico | % no Pico | Total Médio (MWh) |
|-----|------|-----------|-----------|-------------------|
| 1 | Janeiro | 11h | 11.28% | 100,152 |
| 2 | Fevereiro | 12h | 10.68% | 113,342 |
| 3 | Março | 11h | 11.08% | 112,853 |
| 4 | Abril | 11h | 11.52% | 88,885 |
| 5 | Maio | 11h | 11.29% | 88,610 |
| 6 | Junho | 11h | 11.53% | 88,172 |
| 7 | Julho | 11h | 11.21% | 93,563 |
| 8 | Agosto | 11h | 10.92% | 105,632 |
| 9 | Setembro | 13h | 10.77% | 114,553 |
| 10 | Outubro | 11h | 10.65% | 113,585 |
| 11 | Novembro | 11h | 10.86% | 98,187 |
| 12 | Dezembro | 11h | 10.80% | 101,893 |

## 💡 Exemplo Prático

```python
# Cenário: Simular geração solar de Janeiro/2026
# Total previsto para o mês: 120.000 MWh

from auxiliar.sample.solar import SolarSampler
import numpy as np

sampler = SolarSampler()

# Calcular MWmédios
# Janeiro tem 744 horas (31 dias × 24h)
mw_medios = 120000 / 744  # = 161,29 MW

# Gerar perfil de UM dia típico
perfil_dia = sampler.gerar_perfil_dia(mes=1, mw_medios=mw_medios)

print(f"Input: {mw_medios:.2f} MWmédios")
print(f"Output: {len(perfil_dia)} valores (um dia típico)")
print(f"Total do dia: {perfil_dia.sum():,.0f} MWh")  # ~3.871 MWh

# Para simular o mês inteiro (31 dias):
perfis_mes = [sampler.gerar_perfil_dia(1, mw_medios) for _ in range(31)]
total_mes = sum(p.sum() for p in perfis_mes)
print(f"Total do mês (31 dias): {total_mes:,.0f} MWh")  # ~120.000 MWh

# Exportar
np.savetxt('perfil_dia_tipico_janeiro.csv', perfil_dia, delimiter=',')
```

## ✅ Status

**🎉 CONCLUÍDO E OPERACIONAL**

- ✅ Scripts organizados nos diretórios corretos
- ✅ Parâmetros salvos em `output/sample/solar/`
- ✅ Backtest salvo em `output/sample/solar/backtest/`
- ✅ Sem distinção dia útil/FDS (corrigido)
- ✅ Modelo simplificado (apenas desagregação horária)
- ✅ Documentação completa (README.md)

---

**Desenvolvido para ONS**  
**Versão**: 1.0  
**Data**: Novembro 2024

