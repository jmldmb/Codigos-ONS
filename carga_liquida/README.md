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
│   │   ├── samplers/           carga v6 (temperatura), eólica (fator diário × AR(1)), solar cent/dist, térmica flex e corte de rede — treino + amostragem
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
python run.py treinar                # samplers eolica solar carga temperatura termica curtailment_rede + hidro_fd + pilhas térmicas -> Output/modelo/ (~40 s)
python run.py simular --anos 2024 2025 -n 6 --seed 42   # Monte Carlo -> Output/modelo/ (~4 s por ano)
python run.py validar                # observado vs simulado -> Output/validacao/  (--perfis: coerência dos perfis eólicos)
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
| `coff_eolica`, `coff_fotovoltaica` | ONS `restricao_coff_*_tm` (mensal) | `baterias/Data/coff_*` (reaproveitado) | curtailment (energético ENE × rede CNF/REL) e potencial renovável. Sem restrição = `''` até 2024-12 e `NaN` desde 2025-01 |
| `capacidade` | ONS `capacidade-geracao` (arquivo único) | `baterias/Data/capacidade` (reaproveitado) | capacidade instalada eólica por mês (teto horário do sampler) |
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
| Carga v6 | `carga(h) = carga_dia(classe) · [a[tipo,mês,h] + b[tipo,mês,h]·temp(h)]`, Σ=24 na temperatura de referência do mês (a temperatura move o **nível** do dia: +1,1 %/°C simulado, +1,35 observado); nível por classe {seg 1,02 · ter–sex 1,04 · sáb 0,96 · dom 0,88 · feriado 0,93}; forma por DU/FDS; ajuste de viés por hora; renormalização no mês. O legado renormalizava cada dia (std do nível diário 0,005 vs 0,033 observado) e tinha só DU/FDS (sáb = dom) | balanço SIN + temperatura; MAPE 2,8 %, R² 0,92 |
| Eólica | `Y_{d,h} = M · [p_h(mês) + (D_d − 1) + Z_{d,h}]`: perfil normalizado por mês + **fator diário D** (cópula gaussiana AR(1) sobre a distribuição empírica de média do dia / média do mês: std 0,13 set → 0,40 fev, P10/P90 0,5/1,5 no verão, ρ dia a dia 0,4–0,8; constante no dia com transição de ±3 h na meia-noite) + ruído AR(1) horário (φ≈0,9, σ≈0,05–0,09, média móvel de 24 h removida); média do **mês** = premissa. O nível do dia é **aditivo**: a amplitude diurna em MW não depende de quanto ventou (perfil por tercil de D é o mesmo deslocado; multiplicar estourava a capacidade: 43,8 GW vs 29,5 observados). O legado renormalizava cada dia (D ≡ 1) e estimava φ/σ nos perfis médios mês a mês (σ ≈ 0,02). Teto físico horário = capacidade instalada (`eolica_teto_capacidade`; cadastro ONS `capacidade` no histórico, `eolica_capacidade_mw` em projeções). Testes de coerência: `python run.py validar --perfis` | potencial COFF (geração + corte), 2023-10+; cadastro de unidades geradoras |
| Solar | perfil médio observado por mês (expoente de forma 1,0 — o 1,5 do legado dava pico +10 % e dia 1 h mais curto) × **fator diário D** multiplicativo (`solar_fator_diario`; cópula empírica, std 0,10 cent. / 0,08 dist.) com **choque comum com a eólica** (`solar_choque_eolica`): inovações correlacionadas pela correlação de postos observada por mês — centralizada +0,4–0,6 em jan–abr, ~0 em mai–set; distribuída +0,12 agregado (mensal é ruído). Causa comum sinótica (ZCIT ativa = nuvens + alísio fraco), não causalidade: muda a cauda (dia de sol E vento, 2–3,6 % dos dias em fev–abr vs 1 % sob independência), não a média. Zeros noturnos ficam no treino; dias com artefato noturno do ONS são descartados | COFF FV / geração usina não-MMGD; MMGD |
| Temperatura (projeção) | meses sem dado real: `T = T_mês + A_d + desvio_h(mês)`, anomalia diária `A` por cópula gaussiana AR(1) sobre a distribuição empírica do mês (std 0,9–2,1 °C, ρ 0,57–0,80), constante no dia com transição na meia-noite (`temperatura_fator_diario`). Sem ela todo dia projetado tinha a temperatura média e a carga não variava de nível. Com ela a carga projetada reproduz o std de nível diário do histórico (DU 0,019, FDS 0,038; +1,03 %/°C) | Meteostat 2022+ |
| Curtailment de rede (`curtailment_rede: true`) | **premissa mensal exógena** (CNF/REL do COFF: restrições regionais de transmissão, quase todo NE, que ocorrem mesmo com o SIN precisando da energia): histórico = observado; projeção em `projecoes.yaml`. Alocado por hora pelo perfil observado (mês × hora; pica às 7–9h, ~20 % do potencial eólico vs ~6 % de madrugada), limitado ao potencial, e subtraído da eólica e da solar centralizada **antes** do despacho. O corte energético (ENE) continua endógeno | COFF 2023-10+ |
| Hidro FD | `FD = c + ghr[hora]·R − 8·(R/GW)² + 0,09·ENA + mês + hora + FDS` — a resposta ao R varia com a hora (0,91 ao meio-dia, 0,76 às 19h) e satura (marginal ≈ 0,45 em R = 20 GW, 0,2 em 35 GW); legado: ghr único 0,33 | histórico FD/R + ENA diária; MAE 1,77 GW, R² 0,91 |
| Valor da água (`termica_flexivel: valor_agua`, padrão) | **premissa = preço-base semanal por subsistema** (papel do DECOMP): histórico = mediana semanal do CMO de cada subsistema (`valor_agua_fonte: cmo`) ou CVU da pilha na térmica de mérito observada (`pilha`); projeção em `projecoes.yaml` (número ou por subsistema; ou derivado da térmica base pela pilha). Base **comprometida** da semana = usinas com CVU ≤ VA do seu subsistema, ligadas o dia inteiro | CMO / térmica observada |
| Despacho (`despachar_va`, papel do DESSEM) | hidro R fecha o balanço entre 14,5 e 42 GW; R no máximo → térmica extra por mérito; R no mínimo → base reduzida da mais cara para a mais barata **até o mínimo técnico de cada usina**, depois curtailment (eólica + solar cent. pro rata, por fim MMGD). **PLD horário = recurso marginal**: VA · CVU da extra · CVU da parcialmente reduzida · piso | — |
| Alternativas | `exogena`: térmica base mensal como premissa (MW), perfil horário observado ou flat; `residual`: legado (térmica só na saturação) | — |
| Pilha térmica | **semanal**: CVU da semana operativa × capacidade **flexível** (máx. gerado nas 52 semanas anteriores − inflexibilidade média) + subsistema, por `cod_usinaplanejamento`; nuclear fora por definição (CEG `UTN`); ~15 GW. **Mínimo técnico** por usina (`pilha_minimo_quantil`, P10): menor nível sustentado da parcela flexível quando ligada (horas com vizinhas ligadas, sem rampa; mediana das 52 semanas) — piso da redução intradiária | datasets `cvu` + `termica_despacho` |

Premissas mensais (`modelo/premissas.py`): nos anos observados tudo vem dos dados — carga (+ exportação),
eólica potencial, solar cent/dist, ENA armazenável SIN, térmica total (o `data.py` do legado era uma cópia
manual do BALANCO_ENERGIA). Para 2026-28, `config/projecoes.yaml`.

### Validação (2022-01 → 2026-09, 6 cenários; média dos cenários vs observado, hora a hora)

| componente | obs (MW) | sim (MW) | viés | MAE | MAE/média | R² |
|---|---|---|---|---|---|---|
| carga | 76.359 | 76.349 | −10 | 2.197 | 2,9 % | 0,92 |
| eólica pós-corte | 11.480 | 11.453 | −28 | 2.353 | 20,5 % | 0,62 |
| solar pós-corte | 7.002 | 6.961 | −41 | 603 | 8,6 % | 0,98 |
| hidro FD | 24.089 | 24.125 | +36 | 1.750 | 7,3 % | 0,91 |
| hidro R | 25.001 | 25.134 | +133 | 2.545 | 10,2 % | 0,76 |
| térmica flexível | 1.203 | 1.228 | +25 | 618 | 51 % | 0,57 (mensal ~0,8) |
| **carga líquida** | **26.175** | **26.327** | **+152** | **2.609** | **10,0 %** | **0,76** |
| CMO SE (R$/MWh): recurso marginal, 0 na sobra | 109 | 95 | −14 | 25 | 23 % | **0,71** |
| PLD (R$/MWh): clip(CMO, piso 61, teto 1.400), obs = proxy do CMO | 139 | 127 | −12 | 21 | 15 % | **0,75** |
| curtailment eól. + solar cent. (COFF, 2023-10+) | 2.951 | 2.441 | −510 | 1.712 | 58 % | 0,61 |
| — só energético (ENE) | 1.618 | 1.118 | −500 | 1.103 | 68 % | 0,55 |

**Distribuição por mês** (`validacao/distribuicao_mensal.csv`: quantis das horas observadas vs das horas simuladas de
todos os cenários — critério para mudanças de *variabilidade*, onde a média dos cenários não conta): carga líquida
P10/P50/P90 obs 18,3/25,4/35,2 GW vs sim 17,7/25,7/36,2; ENE P90 obs 5,96 GW vs sim 4,34; spikes de preço (> 1,5×
mediana semanal) obs 3,3 % das horas, sim 1,6 %, recall 0,08. **Médias diárias** dentro do mês (2024-26): eólica
pós-corte P10/P90 obs 0,71/1,24 vs sim 0,68/1,29 (sem o fator diário: 0,91/1,05); carga líquida obs 0,84/1,15 vs sim
0,85/1,13 (sem: 0,88/1,06); preço obs 0,14/1,35 vs sim 0,77/1,25 — a variabilidade diária do preço é outra história
(piso 61, patamar semanal como premissa).

Histórico das últimas mudanças (mesma janela, mesma semente quando pareado):
1. Corte de rede como premissa + bug do `''` no COFF (inflava o potencial 2023-10→2024-12 em ~0,5 GW): eólica +685 → +45,
   carga líquida −457 → +78, hidro R −312 → +167. O viés da carga líquida era quase todo o corte de rede.
2. Mínimo técnico (base reduzida até zero → até o piso da usina), teste pareado por dia: térmica intradiária MAE 366 → 208,
   melhor em 98 % dos dias (p 10⁻⁸⁷); carga líquida intradiária 1.886 → 1.806 (90 %); ENE diário melhor em 60 %; PLD
   intradiário 26,0 → 26,4 (pior em 54 %, p 3·10⁻⁴); nível diário da térmica 544 → 597 (pior) — nas horas com ENE > 1 GW o
   modelo mantém 1,9 GW de térmica (obs 1,7; antes 1,0). Térmica R² 0,46 → 0,55, carga líquida R² 0,734 → 0,742.
3. Fator diário eólico: ENE 1.168 → 1.238 (P90 3,7 → 4,4 GW), spikes sim 0,7 % → 1,4 % (recall 0,03 → 0,08); as métricas
   pareadas hora a hora pioram um pouco (eólica MAE 2.244 → 2.417, carga líquida R² 0,742 → 0,728) porque a média de
   6 cenários agora carrega o ruído do fator diário (std/√6) — a média populacional não muda; a distribuição diária,
   que era errada (todo dia = média do mês), passa a bater. Aceito pelo critério de distribuição.
4. Nível diário da carga (temperatura move o nível; classes seg/ter–sex/sáb/dom/feriado): carga MAE 2.832 → 2.194
   (R² 0,87 → 0,92), carga líquida MAE 2.770 → 2.675 (R² 0,735 → 0,752), ENE 1.223 → 1.256, spikes precisão 0,15 → 0,23
   e recall 0,06 → 0,10. Bateria de testes da carga (`validar --perfis`, obs vs sim 2024-26): std do nível diário DU
   0,033 vs 0,019 (era 0,005), FDS 0,049 vs 0,039 (era 0,012); nível por classe seg 1,020/1,020, ter–sex 1,040/1,041,
   sáb 0,957/0,957, dom 0,884/0,881, feriado 0,927/0,923 (antes sáb = dom = feriado = 0,919); nível vs temperatura
   +1,35 %/°C vs +1,07 (era 0 por construção); forma, rampas e meia-noite já batiam. Resíduo horário: std 4,6 % → 3,7 %,
   MAPE 3,6 % → 2,8 %, ainda com autocorrelação 0,93/0,54 (1 h / 24 h) — o que falta no nível diário não é temperatura.
   Em projeção, a anomalia diária de temperatura amostrada dá à carga a mesma variabilidade de nível do histórico.
5. Solar (bateria `validar --perfis`): o expoente 1,5 da centralizada distorcia a forma (MAE por hora 0,09, pico 2,95 vs
   2,69 da média do dia, 11 h de sol vs 12) e o treino descartava os zeros noturnos, de modo que um artefato do ONS
   (MMGD 2024-11-10, 7.949 MW constantes de 0h a 7h) virava 1,0 de geração noturna no perfil de novembro. Corrigidos:
   forma MAE 0,006/0,005, solar MAE 752 → 597 (R² 0,985), carga líquida MAE 2.665 → 2.635 (R² 0,758); ENE 1.247 → 1.207
   (o pico exagerado inflava a sobra do meio-dia).
6. Fator diário solar + choque comum com a eólica: correlação diária sim 0,25 (obs 0,29) na centralizada, 0,09 (0,07) na
   distribuída; std de D 0,115 (obs 0,097) / 0,067 (0,083); ENE 1.207 → 1.235; carga líquida MAE 2.635 → 2.608 (R² 0,763).
   Fica fora o resíduo intradiário de nuvens (std 0,14 / 0,07 nas horas de sol) e a autocorrelação de D da centralizada
   sai baixa (0,37 vs 0,56: ρ estimado dentro do mês do calendário).
7. Hidro FD (bateria `validar --perfis`): MAE 1,78 GW, R² 0,91, mas erro diário com autocorrelação 0,7 (1 d) / 0,4 (7 d) e
   viés por ano de +0,9 (2023) a −0,5 GW (2025). **Testado e descartado:** ENA por subsistema (N 0,30, NE 0,07, S 0,11,
   SE 0,04 MW/MWmed) em vez do SIN — MAE 1.766 → 1.718 in-sample, 2.228 → 2.277 fora da amostra (treino 2022-24,
   teste 2025-26), viés por ano igual; EAR por subsistema: correlação com o resíduo ≤ 0,19. O erro é de **despacho**, não de
   hidrologia: com hidro R no mínimo o modelo dá FD +1,0 GW acima da observada (ENE > 1 GW: +0,8; CMO < 10: +0,4) — o ONS
   também reduz a fio d'água na sobra (vertimento turbinável); com R > 35 GW ou CMO > 200 fica −0,4/−0,7 GW — na escassez
   o ONS a espreme; FD > 33 GW fica −1,5 GW. A regressão dá a FD média para (R, ENA); a FD real participa do despacho numa
   faixa em torno dela.
8. FD na sobra (`fd_reducao_sobra`): a regressão passa a ser treinada FORA das horas de sobra (FD "natural", MAE 1.645 /
   R² 0,916 nessas horas) e o despacho verte água turbinável — reduz a FD até `reducao_sobra_mw` (2,0 GW = FD média
   abaixo da regressão nas horas com corte > 1 GW) depois do R no mínimo e da base no piso, antes de cortar renovável.
   Evidência de que a FD absorve a sobra primeiro: redução de 0,5 GW quando o corte é < 0,5 GW (73 % da sobra), 2,2 GW
   quando é 4–8 GW (28 %), 1,5 GW acima de 8 GW (10 %) — cresce e satura. Escassez: coeficiente −0,2 GW, n.s., não
   implementado. Vertimento turbinável estimado do `dados_hidrologicos_di` (70 usinas FD, 0,7–2,9 GW médios por ano,
   corr 0,34 com o resíduo) confirmou direção e ordem de grandeza, mas não separa decisão de vazão com precisão
   (capacidade em cheia, unidades fora, resolução diária) — ficou como diagnóstico. A/B mesma semente: FD nas horas com
   corte > 1 GW obs 16,6 GW, antes 18,1, agora 16,8; FD global viés +217 → +35, R² 0,904 → 0,910; teste pareado por dia
   neutro (o dia de sobra simulado não é o observado); ENE médio cai 1.435 → 1.130 porque a sobra total do modelo é
   menor que a real (obs: 1,6 GW de corte + ~0,4 de FD vertida) — o gap restante é de vento extremo e térmica, não de FD.
9. Preço, igual com igual: o despacho passa a devolver `cmo` (custo marginal: 0 na sobra, VA, CVU) e `pld` = clip(cmo, piso,
   teto). Antes o PLD simulado (piso 61) era validado contra o CMO do ONS (que vai a zero em 29 % das horas e em 164 dias
   inteiros de 2024-26): 35 % das horas simuladas no piso vs 37 % observadas abaixo dele — a fração acertava, a métrica
   punia. CMO × CMO: MAE 52 → 25, R² 0,67 → 0,71; PLD × clip(CMO): MAE 21, R² 0,75. Teto `pld_maximo` (1.400) novo. Efeito
   colateral esperado: nas premissas placeholder de 2027-28 (carga 97 GW em fevereiro) aparecem ~80 horas/ano de déficit
   (dia quente + vento fraco, 18–21h: térmica toda despachada, PLD no CVU máximo) — `val_erro = 1` nessas horas.

Por que o mínimo técnico e não "reduzir até zero" (2025-26, horas com corte energético > 1 GW = 25 % das horas):
a inflexibilidade fica onde está (4,8 GW), a ordem de mérito cai de 1,95 para 1,09 GW e o **unit commitment sobe de
0,24 para 0,68 GW** — a usina comprometida pelo DECOMP não desliga no vale solar, é reduzida ao mínimo e re-rotulada.
Das usinas comprometidas no dia, 23 % desligam de fato, 40 % ficam abaixo de 40 % da capacidade e 34 % acima de 80 %.
Quem fica ligada é ciclo combinado grande e carvão (Sergipe 1,6 GW a 86 %, Pecém, Itaqui, Parnaíba V, Maranhão 4/5);
quem desliga são motores e ciclos abertos pequenos (Prosperidade, Poraque, Jaraqui) e algumas baratas (Marlim Azul,
Pampa Sul, Aparecida). Correlação entre usinas desligar × CVU = −0,38: o ONS desliga quem *consegue* ciclar, não quem
é cara. O piso P10 por usina (estimado sem usar as horas de sobra, causal) fecha 2/3 do erro: térmica flexível das
comprometidas nas horas de sobra obs 1,9 GW (2025) / 1,5 (2026) vs Σ mínimos 1,6 / 1,2 vs zero.

Por que o fator diário eólico: 91 % do gap de ENE estava nos dias com vento > 1,1× a média do mês (obs ENE 3,8 GW nesses
dias vs 1,15 nos dias < 0,7×; o simulado era flat em ~1,8 porque todo dia tinha a média do mês). A marginal de D é a
empírica do mês e não uma lognormal porque D é limitado pela capacidade instalada (lognormal dava P99 2,6 em fevereiro
contra máximo observado 1,9). Correlação diária eólica × solar +0,29 (0,5–0,6 em fev–abr, ~0 em mai–set): não modelada.
**Testes de coerência dos perfis** (`validar --perfis`, `Output/validacao/perfis_eolica.csv`, obs vs sim 2024-26): forma
média do dia MAE 0,006–0,035; amplitude do perfil por tercil de D 2,5/1,8/1,6 vs 2,3/1,7/1,6 (a forma multiplicativa dava
1,9/1,8/1,9); rampas std 0,073 vs 0,086 e P99 0,18 vs 0,21 (15 % grandes); salto na meia-noite igual ao das outras horas
(0,048 vs 0,055; era 0,20 com D em degrau e demédia por dia); autocorrelação intradiária 0,91/0,56 vs 0,86/0,49;
persistência de D 0,69/0,35/0,14 vs 0,60/0,32/0,15; std horário total por mês 5–15 % abaixo do observado; máximo horário
33,6 GW vs 29,5 antes do teto; com o teto = capacidade instalada o máximo fica na capacidade do mês (33,2 GW em 2025).
O teto só corta a cauda (0,01 % das horas): o máximo agregado observado fica em 0,55–0,87 da instalada por diversidade
espacial, e usar essa razão seria um fator — fica a capacidade, que é o limite físico.

Regimes simulados: hidro marginal 82 %, curtailment 13 %, base reduzida 1 %, extra 3 % (observado: ±50 % do patamar semanal em 78 % das horas; abaixo 16 %, concentradas 8–14h com R ≈ 15,6 GW; acima 6 %, 16–22h com R p90 38,5 GW). **Componente intradiária** (`validacao/metricas_intradiarias.csv`, desvios da média diária): CMO corr 0,55 / R² 0,27 / MAE 27, PLD corr 0,58 / R² 0,32 / MAE 22; hidro R corr 0,93 / R² 0,83; térmica corr 0,37 / MAE 213 (R² −0,6: ainda pior que flat, mas era −4,4); spikes horários (CMO > 1,5× a mediana da semana operativa, mesma definição nos dois lados; obs 3,3 % das horas, sim 0,9 %): precisão 0,60, recall 0,16 — quando o modelo dá degrau ele costuma existir, mas o modelo dá poucos. Qualquer mudança de estrutura horária deve ser julgada por estas métricas em teste pareado por dia, não pelo desvio-padrão.

Comparação dos modos (mesma simulação 2022-25): `valor_agua` com `fonte: pilha` (sem usar o CMO) → PLD R² 0,51, térmica R² 0,76; `exogena` → térmica R² 0,82, carga líquida viés −317, PLD R² 0,51; `residual` (legado) → térmica ≈ 0, carga líquida viés −716, PLD R² ≈ 0. O ganho de R² 0,70 vem do nível do patamar ser premissa; o modelo entrega a modulação.

Por que a base é comprometida o dia inteiro: o "unit commitment" do ONS (27 % da térmica flexível) tem pico às 8–13h e mínimo às 18–20h, com correlação intradiária **negativa** com a carga líquida — são as mesmas unidades da ordem de mérito, rotuladas como UC no vale solar (o preço não as chamaria) e como mérito à noite; a soma é quase flat no dia (CV 0,16). Por que o VA é por subsistema: em mar/2025 o CMO SE/S foi ~350 e N/NE ~10; 1,3 GW de térmicas do N/NE com CVU 111–295 não rodaram. Pilha semanal + VA por subsistema + base comprometida levaram a térmica de R² 0,30 para 0,49 (mensal 0,68 → 0,81) sem nenhum fator de ajuste. `min_hidro_reservatorio` 14,5 GW do legado se sustenta (12 ou 10,5 GW pioram R, carga líquida e curtailment).

Por que a térmica flexível é premissa e não decisão do modelo: o despacho herdado só chamava térmica quando a
hidro batia no limite (térmica ≈ 0 em 99,7 % das horas vs 48 % observado), e nenhuma variável disponível a
prevê — o valor da água implícito (CVU marginal despachado) correlaciona só 0,5 com o CMO, e `flex ~ EAR + ENA + mês`
dá R² 0,5 (mudança de regime em 2025-26). Já `CMO ~ térmica_flex` dá R² 0,82 mensal. Ver `Output/modelo/valor_agua_implicito.parquet`.

Limitações restantes: o curtailment energético simulado fica ~25 % abaixo do observado (P90 4,3 vs 6,0 GW) — o terço do
erro de térmica que o mínimo técnico não fecha (usinas que nem ao mínimo vão: inflexibilidade real maior que a declarada,
não está em dado público) e a correlação eólica × solar no verão; o corte de rede é premissa, não previsão; o PLD tem piso 61 (CMO observado chega a 0) e subestima picos (out/2024: 360 vs 516).

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
  `baterias/` (37,2 TWh em 2025), separado em energético (ENE) e de rede (CNF/REL). Até 2024-12 o ONS marca
  "sem restrição" com `''` (não `NaN`); tratar `''` como restrição inflava o potencial em ~0,5 GW médios.
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
- **Corte de rede como premissa** (`curtailment_rede`): o legado (e o despacho) só produz corte energético; o de rede
  (CNF/REL, 2 GW médios em 2025) entra como premissa mensal com perfil horário observado, no padrão da térmica flexível.
- **Fator diário eólico** (`eolica_fator_diario`): o legado renormalizava cada dia simulado à média do mês; agora a
  média do dia segue a distribuição observada (cópula gaussiana AR(1), aditiva ao perfil) e só o mês é renormalizado.
  `samplers/_diario.py`; testes em `validacao/perfis.py`.
- **Mínimo técnico na sobra** (`pilha_minimo_quantil`): a base comprometida reduz até o piso de cada usina, não até zero;
  a ordem continua da mais cara para a mais barata (na realidade o ONS desliga quem consegue ciclar, mas o total é o que
  fecha o balanço). `0` volta ao comportamento antigo.
- **Despacho por valor da água** (`termica_flexivel: valor_agua`, estrutura DECOMP → DESSEM) com preço horário pelo recurso
  marginal, VA semanal por subsistema e base comprometida; `exogena` (térmica base mensal) e `residual` (legado) continuam
  como opções. **Testado e descartado (sem ganho nas métricas ou reprovado no teste intradiário):** fator de despacho; proxy
  de disponibilidade por geração recente (k < 52 semanas); disponibilidade operacional declarada do ONS como capacidade
  (`disponibilidade_usina_ho`: métricas iguais — o sub-despacho residual é restrição de combustível, invisível nela);
  preço-base por patamar DU/FDS (métricas iguais); comprometimento pela média ou P75 do CMO (a mediana é a estatística
  certa); R mínimo abaixo de 14,5 GW; teto fixo de 38–40 GW; teto por modulação semanal `24,3 + 0,54·R_médio` (aproxima a
  dispersão intradiária do PLD mas nas horas erradas: MAE intradiário 20,8 → 22,8, térmica 306 → 365, spikes precisão 0). **Pilha só com capacidade flexível**
  (`pld_offset_mw: 0`; o legado somava 3.500 MW, que compensava a nuclear na base da pilha).
- `data.py` (dicionários manuais) → `premissas.py` (dados) + `projecoes.yaml`; feriados calculados em vez de tabela 2023-25.

- **Pilha térmica** montada dos dados ONS (`cvu_usitermica_se` + despacho térmico) em vez das planilhas manuais
  do módulo CVU térmicas (equivalência de nomes, indisponibilidade, exceções); ficam de fora ~0,8 GW sem CVU
  (Norte Fluminense, despacho contratual). Um xlsx em `config.modelo.pilha_termica_xlsx` ainda pode substituir.

## Pendências

- Fontes das projeções 2026-28 em `projecoes.yaml` (herdadas sem documentação).
- 5 UHEs pequenas sem classificação R/FD no cadastro (~50 MW): Alto Jatapu, Conj. Barreiras, Eng. Dreher,
  Eng. Kotzian, Juruena.
- Premissa de preço-base / térmica flexível 2026-28 em `projecoes.yaml` (hoje: placeholder = térmica observada de 2025).
- Calibrar `limite_hidro_reservatorio` (teto efetivo da hidro) pelo regime de degrau observado (~38–40 GW?).
- **Sub-despacho térmico de ~200 MW (~20 %)**: usinas disponíveis (dataset `disponibilidade_usina_ho`) e no dinheiro que o ONS
  não despacha — Santa Cruz e Baixada Fluminense (gás Petrobras, SE), Maranhão III e Parnaíba V (gás Parnaíba), Itaqui e
  Pampa Sul (carvão): restrição de suprimento de combustível, invisível nos dados públicos. Só entra como premissa por usina.
- Regime de degrau em 3,7 % das horas vs 6 % observado: parte dos spikes ocorre com R ≈ 34 GW, por rampa/unit
  commitment do DESSEM, abaixo de qualquer teto de energia — não modelado.
