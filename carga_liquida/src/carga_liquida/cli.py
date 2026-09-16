"""Interface de linha de comando (ver run.py)."""
import argparse

from .config import get_logger, load_config

logger = get_logger("cli")

ANALISES = ("hidro", "cmo", "diarios", "curtailment")


def _validar(valores, validos, rotulo):
    invalidos = [v for v in (valores or []) if v not in validos]
    if invalidos:
        raise SystemExit(f"{rotulo}(s) inválido(s): {invalidos}. Válidos: {list(validos)}")


def cmd_baixar(args):
    from .dados.download import OnsDownloader
    _validar(args.datasets, load_config()["datasets"], "dataset")
    OnsDownloader().download(args.datasets or None, force=args.force)


def cmd_processar(args):
    from .observado import carga_liquida
    carga_liquida.processar()


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
    args.datasets, args.force, args.analises = None, False, None
    cmd_baixar(args)
    cmd_processar(args)
    cmd_analisar(args)


def main(argv=None):
    p = argparse.ArgumentParser(prog="carga_liquida", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("baixar", help="baixa/atualiza os dados do ONS (só o que falta)")
    s.add_argument("datasets", nargs="*", metavar="DATASET",
                   help=f"datasets (default: todos): {', '.join(load_config()['datasets'])}")
    s.add_argument("--force", action="store_true", help="re-baixa arquivos existentes")
    s.set_defaults(func=cmd_baixar)

    s = sub.add_parser("processar", help="calcula a carga líquida histórica a partir dos brutos")
    s.set_defaults(func=cmd_processar)

    s = sub.add_parser("analisar", help="gera gráficos/tabelas a partir do processado")
    s.add_argument("analises", nargs="*", metavar="ANALISE", help=f"quais (default: todas): {', '.join(ANALISES)}")
    s.set_defaults(func=cmd_analisar)

    s = sub.add_parser("tudo", help="baixar + processar + analisar")
    s.set_defaults(func=cmd_tudo)

    args = p.parse_args(argv)
    args.func(args)
