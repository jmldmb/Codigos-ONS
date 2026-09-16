# Guia Prático de Uso - Modelos Solar e Eólica

## Início Rápido

### 1. Processar Dados (Executar uma vez)

```bash
# Solar
cd C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem\Scripts\src\auxiliar\sample\solar
python processar_perfis_solares.py

# Eólica
cd C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem\Scripts\src\auxiliar\sample\eolica
python processar_perfis_eolicos.py
```

### 2. Usar os Modelos

```python
# Importar
from auxiliar.sample.solar import SolarSampler
from auxiliar.sample.eolica import EolicaSampler

# Criar samplers
sampler_solar = SolarSampler()
sampler_eolica = EolicaSampler()

# Gerar perfis
perfil_solar = sampler_solar.gerar_perfil_dia(mes=6, mw_medios=150)
perfil_eolica = sampler_eolica.gerar_perfil_dia(mes=9, mw_medios=400, seed=42)
```

---

## Exemplos Práticos

### Exemplo 1: Simular Junho/2025

```python
from auxiliar.sample.solar import SolarSampler

sampler = SolarSampler()

# Dados do mês
# Junho tem 720 horas (30 dias × 24h)
# Previsto: 110.000 MWh para o mês
# MWmédios = 110.000 / 720 = 152,78 MW

mw_medios = 152.78

# Gerar perfil de um dia típico
perfil_dia = sampler.gerar_perfil_dia(mes=6, mw_medios=mw_medios)

print(f"Total do dia: {perfil_dia.sum():,.0f} MWh")  # ~3.667 MWh
print(f"Hora de pico: {perfil_dia.argmax()}h")        # 11h
print(f"Geração no pico: {perfil_dia.max():,.0f} MWh")

# Simular mês inteiro (30 dias iguais - determinístico)
perfis_mes = [sampler.gerar_perfil_dia(6, mw_medios) for _ in range(30)]
total_mes = sum(p.sum() for p in perfis_mes)
print(f"Total do mês: {total_mes:,.0f} MWh")  # ~110.000 MWh
```

---

### Exemplo 2: Simular Setembro/2025 com Variabilidade

```python
from auxiliar.sample.eolica import EolicaSampler
import numpy as np

sampler = EolicaSampler()

# Dados do mês
# Setembro tem 720 horas (30 dias × 24h)
# Previsto: 300.000 MWh para o mês
# MWmédios = 300.000 / 720 = 416,67 MW

mw_medios = 416.67

# Gerar 30 dias DIFERENTES (estocástico)
perfis_mes = []
for dia in range(30):
    perfil_dia = sampler.gerar_perfil_dia(
        mes=9,
        mw_medios=mw_medios,
        seed=1000 + dia  # Seed diferente para cada dia
    )
    perfis_mes.append(perfil_dia)

# Estatísticas
perfis_array = np.array(perfis_mes)
print(f"Total do mês: {perfis_array.sum():,.0f} MWh")  # ~300.000 MWh
print(f"Média diária: {[p.sum() for p in perfis_mes]}")
print(f"Std diária: {np.std([p.sum() for p in perfis_mes]):,.2f} MWh")
```

---

### Exemplo 3: Análise de Risco (Monte Carlo)

```python
from auxiliar.sample.eolica import EolicaSampler
import numpy as np

sampler = EolicaSampler()

# Gerar 1000 cenários para análise de risco
cenarios = sampler.gerar_multiplos_cenarios(
    mes=9,
    mw_medios=416.67,
    n_cenarios=1000,
    seed=42
)

# Estatísticas
total_diario = cenarios.sum(axis=1)

print(f"Média diária: {total_diario.mean():,.0f} MWh")
print(f"P05: {np.percentile(total_diario, 5):,.0f} MWh")
print(f"P50: {np.percentile(total_diario, 50):,.0f} MWh")
print(f"P95: {np.percentile(total_diario, 95):,.0f} MWh")

# Análise por hora
print("\nRisco por hora (exemplo: hora 12h):")
hora_12 = cenarios[:, 12]
print(f"  P05: {np.percentile(hora_12, 5):,.0f} MWh")
print(f"  P50: {np.percentile(hora_12, 50):,.0f} MWh")
print(f"  P95: {np.percentile(hora_12, 95):,.0f} MWh")
```

---

### Exemplo 4: Usar via sampling.py (Integrado)

```python
from mini_dessem.sampling import (
    sample_val_gersolar_perfil_ar1,
    sample_val_geolica_perfil_ar1
)

# Simular 1 semana (168 horas)

# Solar - Determinístico
serie_solar = sample_val_gersolar_perfil_ar1(
    media_diurna=150,    # MWmédios
    mes=6,               # Junho
    num_horas=168        # 1 semana
)

# Eólica - Estocástico
serie_eolica = sample_val_geolica_perfil_ar1(
    media_mensal=400,    # MWmédios
    mes=9,               # Setembro
    num_horas=168,       # 1 semana
    num_cenarios=10,     # 10 cenários
    seed=42
)

print(f"Solar shape: {serie_solar.shape}")    # (168,)
print(f"Eólica shape: {serie_eolica.shape}")  # (10, 168)
```

---

### Exemplo 5: Comparar Perfis Solar vs Eólica

```python
from auxiliar.sample.solar import SolarSampler
from auxiliar.sample.eolica import EolicaSampler
import matplotlib.pyplot as plt

sampler_solar = SolarSampler()
sampler_eolica = EolicaSampler()

# Mesmos MWmédios para comparar padrão
mw_medios = 400

# Gerar perfis
perfil_solar = sampler_solar.gerar_perfil_dia(6, mw_medios)
perfil_eolica = sampler_eolica.gerar_perfil_dia(9, mw_medios, deterministico=True)

# Plotar
plt.figure(figsize=(12, 6))
plt.plot(range(24), perfil_solar, 'o-', label='Solar (Junho)', linewidth=2)
plt.plot(range(24), perfil_eolica, 's-', label='Eólica (Setembro)', linewidth=2)
plt.xlabel('Hora do Dia')
plt.ylabel('Geração (MWh)')
plt.title('Comparação: Perfis Solar vs Eólica')
plt.legend()
plt.grid(True, alpha=0.3)
plt.xticks(range(0, 24, 2))
plt.tight_layout()
plt.savefig('comparacao_solar_eolica.png', dpi=150)
plt.show()
```

---

### Exemplo 6: Perfil Determinístico vs Estocástico (Eólica)

```python
from auxiliar.sample.eolica import EolicaSampler
import matplotlib.pyplot as plt

sampler = EolicaSampler()

# Perfil determinístico (médio)
perfil_medio = sampler.gerar_perfil_dia(9, 400, deterministico=True)

# 5 perfis estocásticos
plt.figure(figsize=(12, 6))
plt.plot(range(24), perfil_medio, 'k-', linewidth=3, label='Perfil Médio', alpha=0.8)

for i in range(5):
    perfil_stoc = sampler.gerar_perfil_dia(9, 400, seed=100+i)
    plt.plot(range(24), perfil_stoc, '--', alpha=0.6, label=f'Cenário {i+1}')

plt.xlabel('Hora do Dia')
plt.ylabel('Geração (MWh)')
plt.title('Eólica: Perfil Médio vs Cenários Estocásticos')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('eolica_deterministico_vs_estocastico.png', dpi=150)
plt.show()
```

---

## Quando Usar Cada Modelo

### SOLAR (Determinístico):
- Planejamento de médio/longo prazo
- Quando variabilidade não importa
- Estudos de expansão
- Previsão de geração média

### EÓLICA (Estocástico):
- Simulação Monte Carlo
- Análise de risco
- Dimensionamento de reservas
- Estudos de confiabilidade
- Otimização under uncertainty

---

## Conversão MWmédios

Sempre lembre:
```
MWmédios = Energia Total (MWh) / Número de Horas
```

### Exemplos:

**Janeiro** (31 dias, 744 horas):
- 120.000 MWh → 120.000 / 744 = **161,29 MWmédios**

**Junho** (30 dias, 720 horas):
- 110.000 MWh → 110.000 / 720 = **152,78 MWmédios**

**Setembro** (30 dias, 720 horas):
- 300.000 MWh → 300.000 / 720 = **416,67 MWmédios**

---

## Validação dos Modelos

### Solar:
```bash
cd Scripts/src/auxiliar/sample/solar
python solar_sampler.py  # Ver exemplos
```

### Eólica:
```bash
cd Scripts/src/auxiliar/sample/eolica
python eolica_sampler.py        # Ver exemplos
python backtest_perfis_eolicos.py  # Rodar validação completa
```

---

## Troubleshooting

### Erro: "Arquivo de perfis não encontrado"
**Solução**: Execute o script de processamento primeiro:
```bash
python processar_perfis_solares.py  # ou
python processar_perfis_eolicos.py
```

### Erro: "Module not found"
**Solução**: Verifique que está executando do diretório correto ou ajuste sys.path

### Valores negativos na eólica
**Solução**: O modelo já garante não-negatividade via `np.maximum(perfil, 0)`

---

## Performance Esperada

### Solar:
- MAPE: ~1.3%
- Erro típico: 40 MWh por hora
- Sempre reproduzível

### Eólica:
- MAPE: ~3.3%
- Erro típico: 350 MWh por hora
- Cobertura IC95: ~99%
- Variabilidade entre cenários: normal e esperada

---

Desenvolvido para ONS  
Novembro 2024








