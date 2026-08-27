import argparse
from catalogo import ETLS

def main() -> None:
    parser = argparse.ArgumentParser(description='Executa os etls do siger -> snowflake')
    parser.add_argument(
        "etl", nargs="?", choices=list(ETLS) + ["all"], default="all",
        help="nome do ETL a rodar, ou 'all' pra rodar todos",
    )
    args = parser.parse_args()

    if args.etl == "all":
        for nome, funcao in ETLS.items():
            print(f"\n=== {nome} ===")
            funcao()
    else:
        ETLS[args.etl]()

if __name__ == "__main__":
    main()