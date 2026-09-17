"""Interface de linha de comando (ver run.py)."""
import argparse

from .config import get_logger, load_config, output_dir

logger = get_logger("cli")

ANALISES = ("hidro", "cmo", "diarios", "curtailment")
TREINOS = ("eolica", "solar", "carga", "termica", "curtailment_rede", "hidro_fd", "pilha")


def _validar(valores, validos, rotulo):
    invalidos = [v for v in (valores or []) if v not in validos]
    if invalidos:
        raise SystemExit(f"{rotulo}(s) inválido(s): {invalidos}. Válidos: {list(validos)}")


def cmd_baixar(args):
    from .dados import temperatura
    from .dados.download import OnsDownloader
    nomes = list(load_config()["datasets"]) + ["temperatura"]
    _validar(args.datasets, nomes, "dataset")
    pedidos = args.datasets or nomes
    ons = [n for n in pedidos if n != "temperatura"]
    if ons:
        OnsDownloader().download(ons, force=args.force)
    if "temperatura" in pedidos:
        temperatura.baixar(force=args.force)


def cmd_processar(args):
    from .dados import temperatura
    from .observado import carga_liquida
    carga_liquida.processar()
    try:
        temperatura.processar_temperatura()
    except FileNotFoundError as e:
        logger.warning(str(e))


def cmd_treinar(args):
    from .modelo import hidro_fd, pilha_termica
    from .modelo.samplers import carga, curtailment_rede, eolica, solar, termica
    _validar(args.samplers, TREINOS, "sampler")
    fn = {"eolica": eolica.treinar, "solar": solar.treinar, "carga": carga.treinar, "termica": termica.treinar,
          "curtailment_rede": curtailment_rede.treinar, "hidro_fd": hidro_fd.calibrar,
          "pilha": lambda: pilha_termica.montar_todas(rebuild=True)}
    for nome in args.samplers or list(TREINOS):
        logger.info(f"=== treinar: {nome}")
        fn[nome]()


def cmd_simular(args):
    from .modelo import simulacao
    simulacao.simular(anos=args.anos, meses=args.meses, num_simulacoes=args.n, seed=args.seed)


def cmd_validar(args):
    from .validacao import comparar, perfis
    if getattr(args, "perfis", False):
        out = perfis.testar_eolica()
        out.to_csv(output_dir("validacao") / "perfis_eolica.csv", index=False)
        return
    comparar.validar()


def cmd_analisar(args):
    from .observado import analises
    _validar(args.analises, ANALISES, "análise")
    quais = args.analises or list(ANALISES)
    for nome in quais:
        logger.info(f"=== análise: {nome}")
        try:
            getattr(analises, nome)()
        except FileNotFoundError as e:
            logger.error(f"[{nome}] {e}")


def cmd_tudo(args):
    args.datasets, args.force, args.analises, args.samplers = None, False, None, None
    args.anos = args.meses = args.n = args.seed = None
    cmd_baixar(args)
    cmd_processar(args)
    cmd_analisar(args)
    cmd_treinar(args)
    cmd_simular(args)
    cmd_validar(args)


def main(argv=None):
    p = argparse.ArgumentParser(prog="carga_liquida", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("baixar", help="baixa/atualiza os dados do ONS (só o que falta)")
    s.add_argument("datasets", nargs="*", metavar="DATASET",
                   help=f"datasets (default: todos): {', '.join(list(load_config()['datasets']) + ['temperatura'])}")
    s.add_argument("--force", action="store_true", help="re-baixa arquivos existentes")
    s.set_defaults(func=cmd_baixar)

    s = sub.add_parser("processar", help="calcula a carga líquida histórica a partir dos brutos")
    s.set_defaults(func=cmd_processar)

    s = sub.add_parser("analisar", help="gera gráficos/tabelas a partir do processado")
    s.add_argument("analises", nargs="*", metavar="ANALISE", help=f"quais (default: todas): {', '.join(ANALISES)}")
    s.set_defaults(func=cmd_analisar)

    s = sub.add_parser("treinar", help="treina os samplers (eólica, solar, carga v6), calibra a regressão hidro FD e monta as pilhas térmicas")
    s.add_argument("samplers", nargs="*", metavar="SAMPLER", help=f"quais (default: todos): {', '.join(TREINOS)}")
    s.set_defaults(func=cmd_treinar)

    s = sub.add_parser("simular", help="simulação Monte Carlo horária -> Output/modelo/")
    s.add_argument("--anos", nargs="+", type=int, help="anos (default: config.modelo.anos)")
    s.add_argument("--meses", nargs="+", type=int, help="meses (default: 1-12)")
    s.add_argument("-n", type=int, help="cenários por mês/ano (default: config.modelo.num_simulacoes)")
    s.add_argument("--seed", type=int, help="semente para reprodutibilidade")
    s.set_defaults(func=cmd_simular)

    s = sub.add_parser("validar", help="observado vs simulado -> Output/validacao/")
    s.add_argument("--perfis", action="store_true", help="só os testes de coerência dos perfis diários eólicos (validacao/perfis.py)")
    s.set_defaults(func=cmd_validar)

    s = sub.add_parser("tudo", help="baixar + processar + analisar + treinar + simular + validar")
    s.set_defaults(func=cmd_tudo)

    args = p.parse_args(argv)
    args.func(args)
