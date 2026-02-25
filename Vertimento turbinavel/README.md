## Vertimento Turbinável — Coleta de Dados (ONS)

Este diretório contém o coletor para baixar os arquivos Parquet de energia vertida turbinável do ONS.

### Estrutura
- `src/download_vertimento.py`: script de download
- `src/process_vertimento.py`: processamento e agregação mensal
- `data/raw/vertimento/`: destino dos arquivos baixados (organizados por ano)
- `data/processed/vertimento/`: saídas processadas (mensal por usina e por subsistema)

### Fontes
- Mensal (2023–atual): [`ENERGIA_VERTIDA_TURBINAVEL_2025_10.parquet`](https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/energia_vertida_turbinavel_ho/ENERGIA_VERTIDA_TURBINAVEL_2025_10.parquet)
- Anual (2015–2022): [`ENERGIA_VERTIDA_TURBINAVEL_2023.parquet`](https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/energia_vertida_turbinavel_ho/ENERGIA_VERTIDA_TURBINAVEL_2023.parquet)

Observação: conforme solicitado, 2015–2022 são tratados como arquivos anuais; 2023–2025 são tratados como arquivos mensais.

### Instalação
Instale as dependências:

```bash
py -3 -m pip install requests pandas pyarrow openpyxl
```

### Uso (somente Python)
Execute a partir do diretório do projeto (Windows PowerShell):

```powershell
py -3 ".\Codigos ONS\Vertimento turbinavel\src\download_vertimento.py"
```

Ou especifique o diretório de saída:

```powershell
py -3 ".\Codigos ONS\Vertimento turbinavel\src\download_vertimento.py" --output ".\Codigos ONS\Vertimento turbinavel\data\raw\vertimento"
```
- Processar e agregar (gera `monthly_by_usina.parquet` e `monthly_by_subsistema.parquet`):

```powershell
py -3 ".\Codigos ONS\Vertimento turbinavel\src\process_vertimento.py"
```
Também é gerado o Excel `monthly_by_subsistema.xlsx` (requer `openpyxl` ou `xlsxwriter`).
Parâmetros úteis:
- `--no-skip-existing`: força re-download mesmo se o arquivo já existir
- `--quiet`: menos logs


