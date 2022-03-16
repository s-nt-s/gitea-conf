from core.git import Gitea
import argparse
import logging
import sys
import re
import json
from os.path import isfile


def read_js(file):
    if isfile(file):
        with open(file, "r") as f:
            return json.load(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Crea repositorios")
    parser.add_argument('repo', help='Repositorio en formato org/repo')
    parser.add_argument('--api', help='Url a la api ej: http://localhost:3000/api/v1')
    parser.add_argument('--token', help='Token para la api')
    parser.add_argument('--force', action='store_true', help='Fuerza recrear el repositorio')
    pargs = parser.parse_args()
    if not re.match(r"^[^/ ]+/[^/ ]+$", pargs.repo):
        sys.exit("No cumple el formato: %s" % pargs.repo)
    org, repo = pargs.repo.split("/")

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(message)s',
        datefmt='%Y-%M-%d %H:%M:%S'
    )
    gitea = Gitea(pargs.api, pargs.token)
    gitea.new_org(org, if_exists ='reuse')
    gitea.new_repo(org, repo, if_exists='overwrite' if pargs.force else 'fail')
    gitea.config_repo(org, repo)
