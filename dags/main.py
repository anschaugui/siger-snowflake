import argparse
from catalogo import ETLS


def main() -> None:
    parser = argparse.ArgumentParser(description='Executa os etls do siger -> destinos configurados')
    parser.add_argument(
        "etl", nargs="?", choices=list(ETLS) + ["all"], default="all",
        help="nome do ETL a rodar, ou 'all' pra rodar todos",
    )
    args = parser.parse_args()

    # ⚠ O CATALOGO GUARDA TUPLAS (funcao, cron). Desempacotar como se fosse so a
    #   funcao dava `TypeError: 'tuple' object is not callable` - o main inteiro
    #   parou de rodar no dia em que o schedule entrou no catalogo.py.
    if args.etl == "all":
        for nome, (funcao, _cron) in ETLS.items():
            print()
            print(f"=== {nome} ===")
            funcao()
    else:
        funcao, _cron = ETLS[args.etl]
        funcao()


if __name__ == "__main__":
    main()
