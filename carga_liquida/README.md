# Carga Líquida do SIN

Medição e simulação da **carga líquida** do Sistema Interligado Nacional a partir dos dados abertos
do ONS. Funde os projetos antigos `carga_liquida` (observado) e `mini_dessem` (simulador) num pacote só.

```
carga_liquida = Hidro_R + termica_flexivel

Hidro_R          = geração das UHEs classificadas como 'R' (reservatório) no cadastro manual
termica_flexivel = val_verifordemdemeritoacimadainflex + val_verifunitcommitment
```

É a parcela da carga que o operador **decide** despachar: exclui renováveis, hidro fio d'água (FD) e a
térmica forçada (inflexibilidade, razão elétrica, garantia energética, GFOM, exportação, reserva, GSUB).
A mesma identidade contábil vale para o simulador (`carga − renováveis − inflexível − FD`), o que permite
validar o modelo contra o observado.

## Estrutura

```
carga_liquida/
├── run.py                      ponto de entrada (CLI)
├── config/config.yaml          caminhos, datasets ONS, período, definição da CL, parâmetros do modelo
├── config/projecoes.yaml       premissas mensais 2026-28 (herdadas do data.py do mini_dessem)
├── src/carga_liquida/
│   ├── config.py               leitura do config, diretórios, logging
│   ├── dados/
│   │   ├── download.py         download incremental dos datasets ONS (S3 open data)
│   │   ├── ons.py              leitores dos brutos: geração por usina, despacho térmico, CMO, balanço, ENA, COFF, cadastro
│   │   └── temperatura.py      temperatura horária "Brasil" (Meteostat, 15 estações ponderadas pela carga)
│   ├── observado/
│   │   ├── carga_liquida.py    cálculo da carga líquida histórica horária
│   │   └── analises.py         hidro FD×R, CL×CMO, gráficos diários, CL×curtailment
│   ├── modelo/
│   │   ├── premissas.py        médias mensais (histórico calculado dos dados; projeções do yaml)
│   │   ├── samplers/           carga v6 (temperatura), eólica AR(1), solar cent/dist — treino + amostragem
│   │   ├── hidro_fd.py         regressão FD = f(R, ENA, mês, hora, tipo de dia) + calibração OLS
│   │   ├── despacho.py         balanço horário: R máximo, brentq, curtailment em cascata, térmica flexível
│   │   ├── pilha_termica.py    merit order mensal: CVU semanal (ONS) x capacidade por usina
│   │   ├── preco.py            PLD pela pilha térmica do mês
│   │   ├── simulacao.py        Monte Carlo (ano × mês × cenário × dia × hora)
│   │   └── feriados.py         feriados nacionais calculados; tipo de dia DU/FDS
│   ├── validacao/comparar.py   observado vs simulado por componente (métricas + gráficos)
│   └── cli.py
├── legacy/Scripts/             scripts originais do carga_liquida (notebook exportado + validações), sem manutenção
├── legacy/mini_dessem/         projeto mini_dessem original, sem manutenção
├── Data/                       brutos (gitignored)  — config.paths.data_dir
└── Output/                     processados, parâmetros, resultados e gráficos (gitignored)
```

## Uso

```bash
pip install -r requirements.txt

python run.py baixar                 # só o que falta: geracao_usina, termica_despacho, cmo, balanco, ena, coff_*, temperatura
python run.py processar              # Data/raw -> Output/observado/*.parquet (~30 s) + temperatura processada
python run.py analisar               # observado: hidro cmo diarios curtailment
python run.py treinar                # samplers eolica solar carga + hidro_fd + pilhas térmicas -> Output/modelo/ (~40 s)
python run.py simular --anos 2024 2025 -n 6 --seed 42   # Monte Carlo -> Output/modelo/ (~4 s por ano)
python run.py validar                # observado vs simulado -> Output/validacao/
python run.py tudo                   # tudo acima, em ordem
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

from carga_liquida.modelo import simulacao, premissas
sim = simulacao.simular(anos=[2026], num_simulacoes=20, seed=1, salvar=False)   # um registro por cenário/dia/hora
prem = premissas.montar()                    # tabela (ano, mês): carga, eólica, solar, ENA, térmica, inflexterm
```

## Dados

| Dataset (config) | Fonte | Pasta local | Uso |
|---|---|---|---|
| `geracao_usina` | ONS `geracao_usina_2_ho` (mensal, 2022-01+) | `Data/raw/geracao por usina/` | geração horária por usina → FD/R, tipos, MMGD |
| `termica_despacho` | ONS `geracao_termica_despacho_2_ho` (mensal) | `Data/raw/termoeletrica/` | componentes verificadas do despacho térmico |
| `cmo` | ONS `cmo_tm` (anual) | `Data/raw/CMO/` | CMO semi-horário (Sudeste por padrão) |
| `balanco` | ONS `balanco_energia_subsistema_ho` (anual) | `baterias/Data/balanco` (reaproveitado) | carga, térmica total, eólica, solar do SIN |
| `ena` | ONS `ena_subsistema_di` (anual) | `Data/raw/ENA/` | ENA armazenável diária (soma SIN) |
| `coff_eolica`, `coff_fotovoltaica` | ONS `restricao_coff_*_tm` (mensal) | `baterias/Data/coff_*` (reaproveitado) | curtailment e potencial renovável |
| `temperatura` | Meteostat bulk (NOAA ISD/SYNOP), 15 aeroportos | `Data/raw/temperatura/` | perfil horário da carga (sampler v6) |
| `cvu` | ONS `cvu_usitermica_se` (anual) | `Data/raw/CVU/` | CVU semanal por usina → pilha térmica |

Saídas em `Output/`:

- `observado/carga_liquida_historica.parquet` (+ `.xlsx`), `geracao_por_tipo.parquet`, `termica_componentes.parquet`
- `hidro_reservatorio/` — mensal, dia da semana, horário/heatmaps, distribuições, séries diárias, `RELATORIO_RESUMO.txt`
- `cmo/` — scatters CL×CMO (grade mensal e geral), `carga_liquida_cmo.csv`, `resumo_mensal.csv`
- `diarios/` — últimos N dias: despacho térmico empilhado por componente; geração por tipo + carga líquida
- `curtailment/` — scatters CL×curtailment por ano/mês, `carga_liquida_curtailment.csv`, `resumo_mensal.csv`
- `modelo/params/` — `eolica.json`, `solar_centralizada.json`, `solar_distribuida.json`, `carga_v6.json`, `hidro_fd.json`
- `modelo/` — `resultados_simulacao.parquet` (cenário × dia × hora), `resumo_mensal.csv`, `pilhas_termicas.csv`
- `validacao/` — `metricas.csv`, `metricas_por_ano_mes.csv`, `comparacao_horaria.csv`, gráficos (médias mensais,
  perfil horário por mês com faixa P10–P90, dispersão, decomposição do erro, erro por hora)

## Modelo

Mesma identidade nos dois lados: **observado** `R + térmica_flex` ≡ **simulado** `carga − eólica_pós − solar_pós − inflexterm − FD`.

| Bloco | Premissa (herdada do mini_dessem) | Treino / fonte |
|---|---|---|
| Carga v6 | `carga_norm(h) = a[tipo,mês,h] + b[tipo,mês,h]·temp(h)`, Σ=24, DU vs FDS (fim de semana + feriado), ajuste de viés por hora | balanço SIN + temperatura; MAPE 3,9 %, R² 0,87 |
| Eólica | perfil médio por mês × ruído AR(1) multiplicativo `Y = μ(1+Z)`, φ≈0,95 | potencial COFF (geração + corte), 2023-10+ |
| Solar | perfil determinístico por mês; centralizada (expoente 1,5) e distribuída (1,0) | COFF FV / geração usina não-MMGD; MMGD |
| Hidro FD | `FD = c + 0,364·R + 0,108·ENA + mês + hora + FDS` (OLS; legado 0,33 / 0,15) | histórico FD/R + ENA diária; MAE 1,7 GW, R² 0,91 |
| Despacho | R até 42 GW; excesso → reduz R até 14,5 GW (brentq), depois corta eólica + solar cent. pro rata e por fim MMGD; déficit → térmica | — |
| PLD | CVU da pilha térmica do mês no ponto `térmica_flex + 3.500 MW`, piso 61 | pilha mensal = CVU semanal × capacidade (máx. geração verificada em 12 meses), casadas por `cod_usinaplanejamento`; ~23 GW flexíveis |

Premissas mensais (`modelo/premissas.py`): nos anos observados tudo vem dos dados — carga (+ exportação),
eólica potencial, solar cent/dist, ENA armazenável SIN, térmica total (o `data.py` do legado era uma cópia
manual do BALANCO_ENERGIA). Para 2026-28, `config/projecoes.yaml`.

### Validação (2022-01 → 2025-12, 6 cenários; média dos cenários vs observado, hora a hora)

| componente | obs (MW) | sim (MW) | viés | MAE | MAE/média | R² |
|---|---|---|---|---|---|---|
| carga | 75.598 | 75.598 | +1 | 2.832 | 3,7 % | 0,87 |
| eólica pós-corte | 11.388 | 11.905 | +517 | 2.333 | 20,5 % | 0,61 |
| solar pós-corte | 6.198 | 6.260 | +62 | 702 | 11,3 % | 0,98 |
| hidro FD | 23.627 | 23.749 | +122 | 1.777 | 7,5 % | 0,90 |
| hidro R | 25.131 | 25.477 | +346 | 2.707 | 10,8 % | 0,74 |
| térmica flexível | 1.039 | 2 | −1.036 | 1.038 | — | — |
| **carga líquida** | **26.170** | **25.454** | **−716** | **2.879** | **11,0 %** | **0,71** |
| PLD vs CMO SE (R$/MWh) | 91 | 111 | +20 | 117 | — | 0,01 |

Limitações estruturais (visíveis em `validacao/perfil_horario_carga_liquida.png`): o despacho só usa
térmica flexível quando a hidro bate no limite, então a térmica flexível observada (ex.: 5–6 GW em
set–out/2024, por segurança energética) aparece no simulado como R; e o curtailment simulado (~0,7 GW) é
só o energético — o de rede (CNF/REL, a maior parte hoje) não é modelado. Pela mesma razão o PLD simulado
é quase constante dentro do mês (≈ CVU no ponto dos 3.500 MW): não captura a dinâmica horária do CMO.

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
- Curtailment vem dos datasets `RESTRICAO_COFF_*` (desde 2023-10), com o método validado no módulo
  `baterias/` (37,2 TWh em 2025).
- Fora isso, `processar` reproduz o parquet antigo exatamente (2022-01 → 2025-09; out/2025 difere porque
  o ONS revisou o bruto após a última execução do legado).
- **Temperatura**: a fonte original (`temperatura_processada.parquet`) não existia mais; substituída por
  Meteostat (estações WMO de aeroportos, pesos ≈ carga). Climatologia ~1 °C acima da hardcoded; o v6 foi retreinado.
- **`inflexterm`** (config.modelo): padrão `termica_forcada` (= térmica total − flexível observada); o legado
  usava a térmica total (`termica_total`), que dá viés −1,6 GW na carga líquida em vez de −0,7 GW.
- **Carga + exportação** (`carga_inclui_intercambio`): a carga do balanço exclui a exportação, mas a
  geração observada não; somar fecha a identidade contábil (~0,2–1 GW).
- **Hidro FD** recalibrada por OLS em 2022-25 (MAE 1,7 GW vs 1,85 GW dos parâmetros do legado nos mesmos dados).
- **Cascata de curtailment**: quando eólica + solar centralizada = 0, o legado não cortava nada; aqui a distribuída é cortada.
- `data.py` (dicionários manuais) → `premissas.py` (dados) + `projecoes.yaml`; feriados calculados em vez de tabela 2023-25.

- **Pilha térmica** montada dos dados ONS (`cvu_usitermica_se` + despacho térmico) em vez das planilhas manuais
  do módulo CVU térmicas (equivalência de nomes, indisponibilidade, exceções); ficam de fora ~0,8 GW sem CVU
  (Norte Fluminense, despacho contratual). Um xlsx em `config.modelo.pilha_termica_xlsx` ainda pode substituir.

## Pendências

- Fontes das projeções 2026-28 em `projecoes.yaml` (herdadas sem documentação).
- 5 UHEs pequenas sem classificação R/FD no cadastro (~50 MW): Alto Jatapu, Conj. Barreiras, Eng. Dreher,
  Eng. Kotzian, Juruena.
- Despacho de térmica flexível por decisão energética (não só por limite de capacidade) — mudança de modelo.
