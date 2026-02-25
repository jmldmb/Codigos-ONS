# Correções Aplicadas - Funções de Sampling

## Problemas Identificados e Corrigidos

### 1. ❌ Retornava múltiplos dias (ex: 168 valores para 1 semana)
**CORRIGIDO** ✅ Agora sempre retorna **24 valores** (1 dia)

### 2. ❌ Tinha Monte Carlo interno (num_cenarios)
**CORRIGIDO** ✅ Monte Carlo acontece no modelo principal (loop externo)

### 3. ❌ Seed confuso
**CORRIGIDO** ✅ Simplificado - eólica sempre aleatória, solar sempre determinística

---

## Como Funcionam Agora

### `sample_val_gersolar_perfil_ar1()`

```python
perfil = sample_val_gersolar_perfil_ar1(
    media_diurna=150,  # MWmédios
    mes=6,             # Junho
    num_horas=168,     # IGNORADO
    num_cenarios=1,    # IGNORADO
    seed=None          # IGNORADO
)

# SEMPRE retorna: array com 24 valores (1 dia)
print(perfil.shape)  # (24,)
print(perfil.sum())  # ~3.600 MWh (150 MW × 24h)
```

**Características**:
- ✅ Sempre retorna 24 valores
- ✅ Sempre o mesmo resultado (determinístico)
- ✅ Perfil com pico ao meio-dia (11-12h)

---

### `sample_val_geolica_perfil_ar1()`

```python
perfil = sample_val_geolica_perfil_ar1(
    media_mensal=400,  # MWmédios
    mes=9,             # Setembro
    num_horas=168,     # IGNORADO
    num_cenarios=1,    # IGNORADO
    seed=None          # IGNORADO
)

# SEMPRE retorna: array com 24 valores (1 dia)
print(perfil.shape)  # (24,)
print(perfil.sum())  # ~9.600 MWh (400 MW × 24h)
```

**Características**:
- ✅ Sempre retorna 24 valores
- ✅ **Resultado diferente a cada chamada** (estocástico AR1)
- ✅ Perfil com pico noturno (22-23h típico)

---

## Como o Modelo Principal Usa

### No simulation.py (linhas 274-291):

```python
# Loop de simulações (Monte Carlo AQUI)
for sim in range(num_simulations):
    
    # Loop de dias do mês
    for dia, tipo_dia in estrutura_mes:
        
        # Gerar 24 horas para ESTE dia
        val_gereolica_sample = sample_val_geolica_perfil_ar1(
            media_mensal=media_mensal_eolica,
            mes=mes,
            num_horas=24  # Sempre 24
        )
        # Retorna: 24 valores (1 dia)
        
        val_gersolar_sample = sample_val_gersolar_perfil_ar1(
            media_diurna=media_diurna_solar,
            mes=mes,
            num_horas=24  # Sempre 24
        )
        # Retorna: 24 valores (1 dia)
        
        # Usar val_gereolica_sample e val_gersolar_sample
        # para calcular despacho deste dia...
```

### Fluxo Correto:

1. **Modelo principal** faz loop de simulações (Monte Carlo)
2. Para cada dia, **chama** `sample_val_geolica_perfil_ar1()` → recebe 24 valores
3. **Modelo principal** processa esses 24 valores
4. **Repete** para próximo dia

**NÃO** há Monte Carlo dentro das funções de sample!

---

## Parâmetros Explicados

### num_horas (IGNORADO)
- **Era**: "quantas horas gerar" (ex: 168 para 1 semana)
- **Agora**: SEMPRE retorna 24 (1 dia)
- **Motivo**: Modelo principal faz loop de dias

### num_cenarios (IGNORADO)
- **Era**: "quantos cenários gerar" (ex: 100 para Monte Carlo)
- **Agora**: SEMPRE retorna 1 cenário (24 valores)
- **Motivo**: Monte Carlo acontece no loop do modelo principal

### seed (IGNORADO/REMOVIDO)
- **Era**: Para reprodutibilidade (ex: seed=42)
- **Agora**: 
  - **Solar**: Ignorado (sempre determinístico)
  - **Eólica**: Sempre None (sempre aleatório)
- **Motivo**: Simplificação - Monte Carlo no modelo principal controla aleatoriedade

---

## Testes de Validação

### Teste 1: Sempre 24 valores ✅
```python
eolica = sample_val_geolica_perfil_ar1(400, 9, 999)  # Passa 999
print(len(eolica))  # 24 (não 999!)
```

### Teste 2: Solar determinístico ✅
```python
a = sample_val_gersolar_perfil_ar1(150, 6, 24)
b = sample_val_gersolar_perfil_ar1(150, 6, 24)
print(np.allclose(a, b))  # True (sempre igual)
```

### Teste 3: Eólica estocástica ✅
```python
x = sample_val_geolica_perfil_ar1(400, 9, 24)
y = sample_val_geolica_perfil_ar1(400, 9, 24)
print(np.allclose(x, y))  # False (valores diferentes)
```

---

## Resumo das Correções

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Valores retornados** | Variável (num_horas) | Sempre 24 |
| **Monte Carlo** | Interno (num_cenarios) | Externo (modelo principal) |
| **Seed** | Parâmetro usado | Ignorado/removido |
| **Solar** | Múltiplos dias iguais | 1 dia |
| **Eólica** | Múltiplos cenários | 1 cenário por chamada |

---

## Vantagens das Correções

1. ✅ **Mais simples**: Funções fazem apenas 1 coisa
2. ✅ **Responsabilidade clara**: Monte Carlo no modelo principal
3. ✅ **Menos confusão**: Sempre 24 valores, sem surpresas
4. ✅ **Compatível**: Modelo principal já estava preparado para isso

---

## Status

**✅ CORREÇÕES APLICADAS E TESTADAS**

- Funções sempre retornam 24 valores
- Monte Carlo removido das funções de sample
- Seed simplificado
- Testes validam comportamento correto

**Pronto para uso no modelo principal!**

---

Desenvolvido para ONS  
Novembro 2024








