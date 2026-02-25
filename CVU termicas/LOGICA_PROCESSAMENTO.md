# 🔄 LÓGICA DE PROCESSAMENTO DE DADOS - MERIT ORDER

## 📋 **VISÃO GERAL DO PROCESSAMENTO**

O script `merit_order.py` implementa uma pipeline completa para geração da curva de mérito, combinando dados de CVU (Custo Variável Unitário) com dados de capacidade de geração térmica/nuclear.

---

## 🎯 **FLUXO PRINCIPAL DE PROCESSAMENTO**

### **1. INICIALIZAÇÃO E CONFIGURAÇÃO**
• **Encontrar diretório raiz do projeto** dinamicamente
• **Carregar arquivo de configuração** (`config.yaml`)
• **Configurar diretórios** de dados brutos, processados e saída
• **Configurar logging** para acompanhamento do processamento

### **2. CARREGAMENTO DE DADOS BASE**
• **Equivalência de nomes** - Mapeamento entre nomes CVU e Capacidade
• **Dados de capacidade** - Download/load de dados ONS (Parquet)
• **Dados CVU** - Carregamento por ano/mês/semana
• **Dados de inflexibilidade** - Limitações operacionais por mês
• **Dados de exceções CVU** - Valores específicos para usinas
• **Dados de indisponibilidade** - Usinas fora de operação

---

## 🔄 **LÓGICA DE PROCESSAMENTO DETALHADA (NOVA VERSÃO)**

### **3. PRÉ-PROCESSAMENTO DE CVU (PRIMEIRA ETAPA)**
• **Carregar dados CVU** originais
• **Aplicar equivalência de nomes** para padronização
• **Preparar base CVU** para processamento

### **4. REMOÇÃO DE INDISPONIBILIDADE (SEGUNDA ETAPA)**
• **Ler planilha de indisponibilidade** com nomes originais
• **Remover usinas indisponíveis** da base CVU
• **Converter nomes de indisponibilidade** segundo equivalência
• **Remover usinas indisponíveis** convertidas da base CVU
• **Logging detalhado** de cada remoção

### **5. APLICAÇÃO DE EXCEÇÕES CVU (TERCEIRA ETAPA)**
• **Ler planilha de exceções** com nomes originais
• **Aplicar novos CVUs** para usinas com exceção
• **Converter nomes de exceções** segundo equivalência
• **Aplicar novos CVUs** para exceções convertidas
• **Logging detalhado** de cada exceção aplicada

### **6. VALIDAÇÃO PÓS-PROCESSAMENTO**
• **Verificar CVUs zerados** restantes
• **Validar se usinas com CVU zero** estão em exceções ou indisponibilidade
• **Gerar relatório** de validação
• **Alertar sobre inconsistências** encontradas

### **7. AUDITORIA DE CORRESPONDÊNCIAS**
• **Mapeamento de equivalência** entre bases CVU e Capacidade
• **Aplicação de equivalências** disponíveis
• **Identificação de correspondências** encontradas
• **Detecção de usinas** apenas em uma base
• **Geração de relatório** de auditoria em Excel
• **Cálculo de taxa** de correspondência

### **8. COMBINAÇÃO DE DADOS (MERGE)**
• **Merge entre CVU e Capacidade** usando nomes mapeados
• **Aplicação de equivalência reversa** para usinas sem CVU
• **Validação de dados** combinados

### **9. APLICAÇÃO DE INFLEXIBILIDADE**
• **Carregamento de dados** de inflexibilidade por mês
• **Busca por correspondência exata** direta
• **Busca via equivalência** para nomes mapeados
• **Cálculo de potência flexível** = Potência Total - Inflexibilidade
• **Validação de consistência** (inflexibilidade ≤ potência total)
• **Substituição da potência** efetiva pela flexível

### **10. VALIDAÇÕES FINAIS**
• **Verificação de CVUs zerados** após todo processamento
• **Identificação de inconsistências** nos dados
• **Logging de estatísticas** finais
• **Detecção de usinas** não encontradas

---

## 📊 **GERAÇÃO DE OUTPUTS**

### **11. CURVA DE MÉRITO**
• **Ordenação por CVU** crescente
• **Cálculo de potência acumulada**
• **Geração de gráfico** com matplotlib
• **Salvamento em PNG** com estatísticas

### **12. TABELA DE MÉRITO**
• **Ordenação completa** das usinas
• **Cálculo de estatísticas** por faixa de CVU
• **Exportação em Excel** com múltiplas abas
• **Inclusão de metadados** do processamento

### **13. RELATÓRIOS DE AUDITORIA**
• **Relatório detalhado** em Excel
• **Resumo em texto** para análise rápida
• **Estatísticas de correspondência**
• **Lista de usinas** não encontradas

---

## 🔧 **FUNCIONALIDADES ESPECIAIS**

### **BUSCA FLEXÍVEL DE NOMES**
• **Normalização de acentos** e caracteres especiais
• **Comparação fuzzy** para nomes similares
• **Múltiplas variações** de um mesmo nome
• **Fallback para busca** exata

### **TRATAMENTO DE EQUIVALÊNCIAS**
• **Mapeamento bidirecional** entre bases
• **Aplicação de equivalência reversa** para usinas sem CVU
• **Validação de consistência** dos mapeamentos
• **Logging de correspondências** encontradas

### **GESTÃO DE ERROS E WARNINGS**
• **Tratamento de dados** ausentes
• **Validação de consistência** dos dados
• **Logging detalhado** de cada etapa
• **Continuidade do processamento** mesmo com warnings

---

## 📈 **ESTATÍSTICAS E MÉTRICAS**

### **MÉTRICAS DE PROCESSAMENTO**
• **Taxa de correspondência** entre bases
• **Número de usinas** processadas
• **CVU médio, mínimo e máximo**
• **Potência total** e flexível
• **Redução por inflexibilidade**

### **INDICADORES DE QUALIDADE**
• **Usinas com CVU = 0** (após validação)
• **Inconsistências** nos dados
• **Usinas não encontradas**
• **Mapeamentos aplicados**

---

## 🎯 **RESULTADO FINAL**

O processamento gera uma **curva de mérito completa** com:
• **Ordenação correta** das usinas por CVU
• **Aplicação de todas as regras** operacionais
• **Validação de consistência** dos dados
• **Relatórios detalhados** para auditoria
• **Outputs visuais** e tabulares prontos para uso

---

## 🔄 **MELHORIAS IMPLEMENTADAS**

### **RESOLUÇÃO DE PROBLEMAS DE CVU ZERO**
• **Processamento sequencial** de indisponibilidade e exceções
• **Aplicação de equivalências** em ambas as etapas
• **Validação pós-processamento** para garantir consistência
• **Logging detalhado** para rastreamento de problemas 