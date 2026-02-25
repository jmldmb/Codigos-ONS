# 🚀 Guia do Orquestrador - Preços de Energia BR

## 📋 **Visão Geral**

O orquestrador é uma versão robusta do notebook `orchestrator.ipynb`, convertido para Python para maior confiabilidade e automação.

## 🔧 **Principais Melhorias**

### **Versão Notebook → Python**
- ✅ **Logging robusto**: Logs detalhados em arquivo e console
- ✅ **Tratamento de erros**: Captura e trata exceções específicas
- ✅ **Validação**: Verifica arquivos, diretórios e dados
- ✅ **Modular**: Código organizado em classe com métodos específicos
- ✅ **Configurável**: Usa arquivo YAML para configuração
- ✅ **Testável**: Script de teste para verificar preparação

## 📁 **Estrutura do Projeto**

```
precos de energia BR/
├── Scripts/
│   ├── orchestrator.py          # ✅ Orquestrador principal
│   ├── teste_orchestrator.py    # ✅ Script de teste
│   ├── config.yaml              # ✅ Configuração dos gráficos
│   ├── plot_utils.py            # ✅ Funções de plotagem
│   ├── data_ingest.py           # ✅ Atualização de dados
│   └── GUIA_ORQUESTRADOR.md     # ✅ Este guia
├── Data/
│   ├── raw/                     # ✅ Dados brutos
│   └── processed/               # ✅ Dados processados
├── templates/
│   └── report.html.jinja        # ✅ Template do relatório
├── charts/                      # ✅ Gráficos gerados
└── report_out/                  # ✅ Relatórios HTML
```

## 🚀 **Como Usar**

### **Passo 1: Instalar Dependências**
```powershell
cd "precos de energia BR/Scripts"
python instalar_dependencias.py
```

### **Passo 2: Testar Preparação**
```powershell
python teste_orchestrator.py
```

### **Passo 3: Executar Orquestrador**
```powershell
python orchestrator.py
```

### **Passo 3: Verificar Resultados**
- **Gráficos**: `charts/YYYY-MM-DD/`
- **Relatório**: `report_out/YYYY-MM-DD_report.html`
- **Logs**: `orchestrator.log`

## ⚙️ **Configuração**

### **Arquivo config.yaml**
```yaml
charts:
  - name: pld_se_daily
    kind: price_daily
    target_sub: SUDESTE
    start: "today-30d"
    end: "today"
    ma: 7

  - name: spread_ne_daily
    kind: spread_daily
    target_sub: NORDESTE
    start: "today-30d"
    end: "today"
    ma: 7
```

### **Tipos de Gráficos**
- `price_daily`: Preço diário com média móvel
- `spread_daily`: Spread diário com média móvel
- `price`: Preço horário

### **Tokens de Data**
- `"today"`: Data atual
- `"today-30d"`: 30 dias atrás
- `"2025-01-01"`: Data específica

## 🔍 **Logs e Debugging**

### **Logs Automáticos**
- **Arquivo**: `orchestrator.log`
- **Console**: Saída em tempo real
- **Níveis**: INFO, WARNING, ERROR

### **Exemplo de Log**
```
2025-01-01 10:00:00 - INFO - 🚀 Iniciando orquestrador...
2025-01-01 10:00:01 - INFO - 📥 Atualizando dados...
2025-01-01 10:00:05 - INFO - ✅ Dados atualizados com sucesso
2025-01-01 10:00:06 - INFO - 📊 Gerando 3 gráficos...
2025-01-01 10:00:10 - INFO - ✅ Relatório salvo: report_out/2025-01-01_report.html
```

## 🛠️ **Troubleshooting**

### **Problema: "Módulo não encontrado"**
```bash
# Verificar se está no diretório correto
cd "precos de energia BR/Scripts"

# Testar importações
python teste_orchestrator.py
```

### **Problema: "Dados não encontrados"**
```bash
# Executar primeiro o script de dados
python precos_BR_corrigido.py

# Depois executar o orquestrador
python orchestrator.py
```

### **Problema: "Dependências para parquet não encontradas"**
```bash
# Instalar dependências automaticamente
python instalar_dependencias.py

# Ou instalar manualmente
pip install pyarrow
```

### **Problema: "Template não encontrado"**
```bash
# Verificar se o template existe
ls templates/report.html.jinja

# Se não existir, criar estrutura básica
mkdir -p templates
```

## 📊 **Fluxo de Execução**

1. **🔍 Validação**: Verifica arquivos e diretórios
2. **📥 Atualização**: Baixa e processa novos dados
3. **📊 Carregamento**: Carrega dados processados
4. **🎨 Geração**: Cria gráficos conforme configuração
5. **📄 Relatório**: Gera relatório HTML
6. **✅ Finalização**: Logs de sucesso

## 🎯 **Vantagens da Versão Python**

| Aspecto | Notebook | Python |
|---------|----------|--------|
| **Automação** | ❌ Manual | ✅ Automático |
| **Logs** | ❌ Limitados | ✅ Detalhados |
| **Erro** | ❌ Para execução | ✅ Continua |
| **Teste** | ❌ Difícil | ✅ Fácil |
| **Manutenção** | ❌ Complexa | ✅ Simples |

## 🚀 **Automação**

### **Agendamento (Windows)**
```batch
# Criar arquivo .bat
@echo off
cd "C:\Users\joaom\OneDrive\Codigos\precos de energia BR\Scripts"
python orchestrator.py
```

### **Agendamento (Linux/Mac)**
```bash
# Adicionar ao crontab
0 8 * * * cd /path/to/project/Scripts && python orchestrator.py
```

---

**Status**: ✅ Notebook convertido → ✅ Python robusto → ✅ Logs detalhados → ✅ Sistema automatizado 