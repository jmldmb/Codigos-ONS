# Lógica de Processamento e Cálculo dos Gráficos

## 📊 **VISÃO GERAL**

O sistema processa dados de geração renovável (eólica e fotovoltaica) do ONS e gera gráficos comparando a geração real com o potencial certificado (P50/P90).

---

## 🔄 **FLUXO DE PROCESSAMENTO**

### **1. DADOS DE ENTRADA**

#### **Dados Brutos (ONS)**
- **Fonte:** Arquivos parquet de `Data/geracao/`
  - `RESTRICAO_COFF_EOLICA_DETAIL_YYYY_MM.parquet`
  - `RESTRICAO_COFF_FOTOVOLTAICA_DETAIL_YYYY_MM.parquet`

#### **Campos principais nos dados brutos:**
- `ceg` - Código de Empreendimento de Geração (identificador da usina)
- `din_instante` - Timestamp (hora a hora)
- `val_geracaoestimada` - **Geração Potencial** (capacidade máxima instantânea)
- `val_geracaoverificada` - **Geração Real** (verificada/medida)

#### **Dados de Cadastro**
- **Arquivo:** `RELACIONAMENTO_USINA_EMPRESA.xlsx`
- **Campos chave:**
  - `ceg` - Identificador da usina
  - `Complexo` - Agrupamento de usinas
  - `SPE` - Sociedade de Propósito Específico (ativo/usina individual)
  - `empresa` - Empresa controladora

---

## 📈 **PROCESSAMENTO DE DADOS**

### **Etapa 1: Consolidação dos Arquivos**
```
Carrega TODOS os arquivos .parquet → DataFrame consolidado
```

### **Etapa 2: Merge com Cadastro**
```python
# Merge por CEG
merged_df = pd.merge(dados_geracao, cadastro, on='ceg', how='left')

# Resultado: dados de geração + Complexo + SPE + empresa
```

### **Etapa 3: Filtragem Temporal**
```python
# Filtra apenas anos de análise (2024, 2025)
merged_df = merged_df[merged_df['ano'].isin([2024, 2025])]
```

### **Etapa 4: AGREGAÇÃO POR EMPRESA/MÊS**
```python
grouped_df = merged_df.groupby(
    ['Complexo', 'SPE', 'empresa', 'mes_ano'], 
    as_index=False
)[['val_geracaoestimada', 'val_geracaoverificada']].mean()
```

⚠️ **IMPORTANTE:** A agregação usa **`.mean()`** (MÉDIA), não `.sum()`

**Por quê?**
- Os dados originais são **horários** (8.760 registros/ano por usina)
- A média representa a **geração média do mês** em MWh
- Cada linha do resultado = 1 SPE (ativo) em 1 mês

---

## 📊 **ESTRUTURA DO ARQUIVO `geracao_renovavel.xlsx`**

### **Granularidade:**
- **1 linha = 1 SPE (ativo) em 1 mês específico**

### **Exemplo: Alupar - Janeiro/2024**
```
Complexo         | SPE              | empresa | mes_ano  | val_geracaoestimada | val_geracaoverificada
nao_declarado    | AW Santa Régia   | Alupar  | 2024-01  | 8.97 MWm           | 8.84 MWm
nao_declarado    | AW São João      | Alupar  | 2024-01  | 7.27 MWm           | 6.28 MWm
```

---

## 📈 **GERAÇÃO DOS GRÁFICOS**

### **Etapa 1: Agregação por Empresa no Gráfico**
```python
# Para cada empresa
for empresa, sub in df.groupby("empresa"):
    
    # GERAÇÃO REAL (verificada)
    real_tab = sub.pivot_table(
        index="mes",           # Eixo X (1-12)
        columns="ano",         # Séries (2024, 2025)
        values="val_geracaoverificada",
        aggfunc="sum"          # ← SOMA todos os SPEs da empresa
    )
    
    # GERAÇÃO POTENCIAL (estimada)
    estimado_tab = sub.pivot_table(
        index="mes",
        columns="ano",
        values="val_geracaoestimada", 
        aggfunc="sum"          # ← SOMA todos os SPEs da empresa
    )
```

### **Etapa 2: Dados de Certificação (P50/P90)**
- **Fonte:** Arquivo `GERACAO_CERTIFICADA.xlsx`
- **P50:** Geração média esperada (50% de probabilidade de ser superada)
- **P90:** Geração conservadora (90% de probabilidade de ser superada)
- **Unidade:** MWm (Megawatt-médio)

---

## 🎯 **DEFINIÇÕES IMPORTANTES**

### **1. Geração Real (val_geracaoverificada)**
- **O que é:** Geração efetivamente medida/verificada
- **Origem:** Dados do ONS (medição real das usinas)
- **Agregação:** MÉDIA horária → SOMA mensal por empresa
- **Linha sólida no gráfico**

### **2. Geração Potencial (val_geracaoestimada)**
- **O que é:** Capacidade máxima de geração (potencial)
- **Origem:** Dados do ONS (estimativa de capacidade)
- **Agregação:** MÉDIA horária → SOMA mensal por empresa
- **Linha tracejada no gráfico**

### **3. P50 e P90 (Certificação)**
- **O que é:** Garantias físicas/certificação energética
- **Origem:** Estudos de certificação (ex: EPE)
- **Granularidade:** Por empresa, por mês
- **Linhas pontilhadas no gráfico**

---

## 📊 **CÁLCULO FINAL NO GRÁFICO**

### **Para cada empresa em cada mês:**

```
Geração Real da Empresa (MWm) = 
    SOMA(Geração Real de todos os SPEs da empresa naquele mês)

Geração Potencial da Empresa (MWm) = 
    SOMA(Geração Potencial de todos os SPEs da empresa naquele mês)
```

### **Exemplo Numérico - Alupar Jan/2024:**
```
SPE 1: 8.84 MWm (real) + 8.97 MWm (potencial)
SPE 2: 6.28 MWm (real) + 7.27 MWm (potencial)
---------------------------------------------------
TOTAL EMPRESA: 15.12 MWm (real) + 16.24 MWm (potencial)
```

Este valor de **15.12 MWm** aparece como o ponto no gráfico da Alupar em Janeiro/2024.

---

## 🔧 **PARA FAZER O MESMO POR ATIVO (SPE)**

### **Modificações necessárias:**

#### **1. No Processamento (`data_processor.py`):**
```python
# ATUAL (por empresa):
grouped_df = merged_df.groupby(
    ['Complexo', 'SPE', 'empresa', 'mes_ano'], 
    as_index=False
)[['val_geracaoestimada', 'val_geracaoverificada']].mean()

# MODIFICAR PARA (por SPE):
# Já está por SPE! Não precisa modificar o processamento.
# Cada linha já representa 1 SPE em 1 mês.
```

#### **2. Na Visualização (`visualization.py`):**
```python
# ATUAL:
for empresa, sub in df.groupby("empresa"):
    real_tab = sub.pivot_table(
        index="mes", 
        columns="ano",
        values="val_geracaoverificada",
        aggfunc="sum"  # Soma todos SPEs
    )

# MODIFICAR PARA:
for spe, sub in df.groupby("SPE"):
    real_tab = sub.pivot_table(
        index="mes",
        columns="ano", 
        values="val_geracaoverificada",
        aggfunc="first"  # Apenas 1 valor (não precisa somar)
    )
```

#### **3. Certificação por SPE:**
Você precisará de um arquivo de certificação por ativo:
```
SPE              | mes | p50_mwm | p90_mwm
AW Santa Régia   | 1   | 8.5     | 7.2
AW São João      | 1   | 6.8     | 5.9
```

---

## ⚠️ **VALIDAÇÕES IMPORTANTES**

1. **Unidades:**
   - Todos os valores estão em **MWm** (Megawatt-médio)
   - MWm = Energia média gerada ao longo do período

2. **Temporalidade:**
   - Dados originais: horários
   - Processamento: média mensal por SPE
   - Gráfico: soma mensal por empresa

3. **Agregação:**
   - **No processamento:** `.mean()` (reduz dados horários para média mensal)
   - **No gráfico:** `.sum()` (soma todos os SPEs da empresa)

---

## 📝 **RESUMO DA LÓGICA**

```
Dados Horários do ONS (por usina/CEG)
    ↓ [mean por mês]
Dados Mensais por SPE (1 linha = 1 SPE/mês)
    ↓ [sum no gráfico]
Gráfico por Empresa (soma de todos SPEs)
```

---

**Criado em:** 13/10/2025  
**Versão:** 1.0


