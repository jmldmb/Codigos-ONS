# 📦 Instruções para Backup e Sincronização de Dados

## ✅ Repositório no GitHub

Seu código foi enviado com sucesso para:
**https://github.com/jmldmb/Codigos-ONS**

## 🔄 Próximos Passos - ANTES DE SAIR DO COMPUTADOR

### 1. Fazer Backup dos Dados

Execute este comando para fazer backup de todos os dados:

```bash
cd "C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS"
python sync_data.py --backup --output "D:\Backup_Codigos_ONS"
```

**Ou escolha outro local:**
```bash
# Para pen drive
python sync_data.py --backup --output "E:\Backup_Codigos_ONS"

# Para Google Drive (se instalado)
python sync_data.py --backup --output "C:\Users\joao.barbosa\Google Drive\Backup_Codigos_ONS"

# Para OneDrive
python sync_data.py --backup --output "C:\Users\joao.barbosa\OneDrive\Backup_Codigos_ONS"
```

### 2. O que o backup vai fazer:

- ✅ Escanear todos os arquivos de dados (~4.6 GB)
- ✅ Criar manifesto com checksums MD5
- ✅ Copiar 15.855 arquivos de dados
- ✅ Organizar tudo por pasta
- ✅ Gerar relatório completo

**Tempo estimado:** 10-15 minutos

### 3. Copiar o Backup

Após o backup, você tem 3 opções:

#### Opção A: Google Drive (RECOMENDADO) ⭐
1. Instale Google Drive Desktop (se não tiver)
2. Faça backup direto para a pasta do Google Drive
3. Aguarde sincronização
4. No PC novo, instale Google Drive e aguarde download

#### Opção B: Pen Drive / HD Externo
1. Copie a pasta de backup para o dispositivo
2. Leve para o novo PC
3. Copie para o novo PC

#### Opção C: Rede / Compartilhamento
1. Compartilhe a pasta em rede
2. Acesse do novo PC
3. Copie os arquivos

---

## 💻 No Novo Computador

### 1. Clonar o Repositório

```bash
git clone https://github.com/jmldmb/Codigos-ONS.git
cd Codigos-ONS
```

### 2. Restaurar os Dados

```bash
python sync_data.py --restore --source "caminho/para/backup"
```

Exemplos:
```bash
# De pen drive
python sync_data.py --restore --source "E:\Backup_Codigos_ONS"

# Do Google Drive
python sync_data.py --restore --source "C:\Users\seu_usuario\Google Drive\Backup_Codigos_ONS"

# De pasta local
python sync_data.py --restore --source "D:\Backup_Codigos_ONS"
```

### 3. Verificar Instalação

```bash
python sync_data.py --verify
```

Você deve ver:
```
✓ Arquivos Python: 213
✓ Arquivos de configuração: XX
📊 Arquivos de dados: 15,855
💾 Tamanho total: 4.59 GB
```

---

## 📊 Estrutura de Dados

O backup inclui:

| Módulo | Arquivos | Tamanho |
|--------|----------|---------|
| Captura ENA | 169 | ~45 MB |
| Carga | 28 | ~120 MB |
| Carga Líquida | 103 | ~200 MB |
| Curtailment | 79 | ~150 MB |
| CVU Térmicas | 16 | ~50 MB |
| Mini DESSEM | 1,209 | ~1.2 GB |
| Geração por Usina | 150 | ~300 MB |
| Preços Energia BR | 37 | ~100 MB |
| Outros | 14,064 | ~2.5 GB |
| **TOTAL** | **15,855** | **~4.6 GB** |

---

## ⚠️ Arquivos Grandes

Atenção para estes arquivos (>100 MB):
- `mini_dessem/output/curtailment/curtailment_raw.parquet` (315 MB)
- `output/curtailment/curtailment_raw.parquet` (298 MB)

Eles estão incluídos no backup!

---

## 🔐 Segurança

### ✅ O que ESTÁ no GitHub:
- ✅ Todo o código Python
- ✅ Notebooks Jupyter
- ✅ Configurações (YAML, JSON)
- ✅ Documentação (README, SETUP)
- ✅ Scripts de sincronização

### ❌ O que NÃO está no GitHub:
- ❌ Arquivos de dados (.parquet, .csv, .xlsx)
- ❌ Logs (.log)
- ❌ Outputs (.png, .html)
- ❌ Credenciais (removidas por segurança)
- ❌ Ambientes virtuais (venv)

---

## 🆘 Problemas Comuns

### "Arquivo não encontrado"
```bash
# Verifique se o caminho está correto
python sync_data.py --verify
```

### "Erro de permissão"
```bash
# Execute como administrador (Windows)
# Ou use sudo (Linux/Mac)
```

### "Espaço insuficiente"
```bash
# Você precisa de pelo menos 5 GB livres
# Verifique: df -h (Linux/Mac) ou dir (Windows)
```

---

## 📞 Informações Úteis

- **Repositório GitHub:** https://github.com/jmldmb/Codigos-ONS
- **Tamanho total:** 4.59 GB (15.855 arquivos)
- **Módulos:** 13 principais
- **Linguagem:** Python 3.8+

---

## ✅ Checklist Final

Antes de sair do computador:

- [ ] Fazer backup dos dados (`python sync_data.py --backup`)
- [ ] Copiar backup para local seguro (Google Drive, pen drive, etc.)
- [ ] Verificar que o backup está completo
- [ ] Anotar o caminho do backup
- [ ] (Opcional) Testar restore em pasta temporária

No novo computador:

- [ ] Instalar Python 3.8+
- [ ] Instalar Git
- [ ] Clonar repositório do GitHub
- [ ] Restaurar dados do backup
- [ ] Verificar instalação (`python sync_data.py --verify`)
- [ ] Testar um módulo

---

**Pronto! Você está preparado para trabalhar em qualquer computador! 🚀**

Para dúvidas, consulte:
- `README.md` - Documentação geral
- `SETUP.md` - Guia de configuração detalhado
- `data_structure.json` - Estrutura de dados
