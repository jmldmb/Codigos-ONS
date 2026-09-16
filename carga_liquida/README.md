# Carga Líquida do SIN

Medição (e, na etapa 2, simulação) da **carga líquida** do Sistema Interligado Nacional a partir dos
dados abertos do ONS.

```
carga_liquida = Hidro_R + termica_flexivel

Hidro_R          = geração das UHEs classificadas como 'R' (reservatório) no cadastro manual
termica_flexivel = val_verifordemdemeritoacimadainflex + val_verifunitcommitment
```

É a parcela da carga que o operador **decide** despachar: exclui renováveis, hidro fio d'água (FD) e a
térmica forçada (inflexibilidade, razão elétrica, garantia energética, GFOM, exportação, reserva, GSUB).
A mesma identidade contábil vale para o simulador (`Carga − Renováveis − Inflexível − FD`), o que permite
validar o modelo contra o observado.

## Estrutura

```
carga_liquida/
├── run.py                      ponto de entrada (CLI)
├── config/config.yaml          caminhos, datasets ONS, período, definição da carga líquida, gráficos
├── src/carga_liquida/
│   ├── config.py               leitura do config, diretórios, logging
│   ├── dados/
│   │   ├── download.py         download incremental dos datasets ONS (S3 open data)
│   │   └── ons.py              leitores dos brutos: geração por usina, despacho térmico, CMO, cadastro, curtailment
│   ├── observado/
│   │   ├── carga_liquida.py    cálculo da carga líquida histórica horária
│   │   └── analises.py         hidro FD×R, CL×CMO, gráficos diários, CL×curtailment
│   ├── modelo/                 (etapa 2) simulador: samplers, regressão hidro FD, despacho, PLD
│   ├── validacao/              (etapa 2) observado vs simulado
│   └── cli.py
├── legacy/Scripts/             scripts originais (notebook exportado + validações do mini_dessem), sem manutenção
├── Data/                       brutos do ONS (gitignored)  — config.paths.data_dir
└── Output/                     processados e gráficos (gitignored)
```

## Uso

```bash
pip install -r requirements.txt

python run.py baixar                 # baixa só o que falta (geracao_usina, termica_despacho, cmo)
python run.py processar              # Data/raw -> Output/observado/carga_liquida_historica.parquet  (~30 s)
python run.py analisar               # todas as análises; ou: analisar hidro cmo diarios curtailment
python run.py tudo                   # os três acima
```

Variáveis de ambiente `CARGA_LIQUIDA_DATA_DIR` e `CARGA_LIQUIDA_OUTPUT_DIR` sobrescrevem `config.paths.*`
(útil em worktrees). O cadastro `Data/raw/cadastros/cadastro.xlsx` (colunas `nom_usina`, `Classificação`
= `R`|`FD`) é insumo manual e **não** é baixado.

Como biblioteca:

```python
import sys; sys.path.insert(0, "src")
from carga_liquida.observado import carga_liquida as cl, analises
df = cl.carregar_historico()                 # din_instante, FD, R, termica_flexivel, carga_liquida_historica, ano, mes, dia, hora
df_cmo = analises.carga_liquida_com_cmo()    # + val_cmo (média horária dos patamares semi-horários)
```

## Dados

| Dataset (config) | Fonte ONS | Pasta local | Uso |
|---|---|---|---|
| `geracao_usina` | `geracao_usina_2_ho` (mensal, desde 2022-01) | `Data/raw/geracao por usina/` | geração horária por usina → FD/R e tipos |
| `termica_despacho` | `geracao_termica_despacho_2_ho` (mensal) | `Data/raw/termoeletrica/` | componentes verificadas do despacho térmico |
| `cmo` | `cmo_tm` (anual) | `Data/raw/CMO/` | CMO semi-horário (Sudeste por padrão) |
| — | `restricao_coff_{eolica,fotovoltaica}_tm` | `baterias/Data/coff_*` (reaproveitado) | curtailment horário do SIN |

Saídas em `Output/`:

- `observado/carga_liquida_historica.parquet` (+ `.xlsx`), `geracao_por_tipo.parquet`, `termica_componentes.parquet`
- `hidro_reservatorio/` — mensal, dia da semana, horário/heatmaps, distribuições, séries diárias, `RELATORIO_RESUMO.txt`
- `cmo/` — scatters CL×CMO (grade mensal e geral), `carga_liquida_cmo.csv`, `resumo_mensal.csv`
- `diarios/` — últimos N dias: despacho térmico empilhado por componente; geração por tipo + carga líquida
- `curtailment/` — scatters CL×curtailment por ano/mês, `carga_liquida_curtailment.csv`, `resumo_mensal.csv`

## Premissas embutidas (herdadas do código original)

- Período a partir de 2022-01-01; geração do **SIN** inteiro (inclui MMGD), CMO do **Sudeste**.
- Térmica flexível = só ordem de mérito acima da inflexibilidade + unit commitment.
- Horas sem registro no despacho térmico recebem térmica flexível = 0.
- Eixos fixos nos scatters: carga líquida 10–50 GW, CMO 0–2000 R$/MWh.

## Diferenças em relação ao legado

- **Aliases de usinas renomeadas pelo ONS** (`config.cadastro.aliases`): `Corumbá I → Corumbá` (nov/2024) e
  `Sobradinho → UHE Sobradinho` (out/2025). O legado deixava esses reservatórios silenciosamente fora de R.
  UHEs ainda sem classificação são listadas no log a cada `processar`.
- CMO horário = média dos dois patamares semi-horários (o legado casava só o patamar `:00`).
- Curtailment vem dos datasets `RESTRICAO_COFF_*` (desde 2023-10), com o mesmo método validado no
  módulo `baterias/` (37,2 TWh em 2025).
- Fora isso, `processar` reproduz o parquet antigo exatamente (2022-01 → 2025-09; out/2025 difere porque o
  ONS revisou o arquivo bruto após a última execução do legado).

## Roadmap — etapa 2 (fusão com o mini_dessem)

`modelo/` (samplers de carga v6 / eólica AR(1) / solar cent+dist, regressão hidro FD, despacho com
curtailment em cascata, PLD pela pilha térmica) e `validacao/` (observado vs simulado, decomposição por
componente, backtest da regressão FD — hoje em `legacy/Scripts/`). Requer retreino dos samplers a partir
dos brutos (`BALANCO_ENERGIA`, COFF, temperatura, ENA).
