#!/usr/bin/env python3
from core.git import Gitea, ExAlreadyExist
import argparse
import logging
import sys
import re
import json
from os.path import isfile
from textwrap import dedent
from argparse import RawTextHelpFormatter


def read_js(file):
    if isfile(file):
        with open(file, "r") as f:
            return json.load(f)

def iter_repos(gitea, repos):
    for repo in repos:
        if not re.match(r"^[^/ ]*/[^/ ]*$", repo):
            logging.critical("repo no cumple el formato: %s" % repo)
            continue
        org, repo = repo.split("/")
        if "" not in (org, repo):
            yield org, repo
        else:
            for r in gitea.get_repos(org, repo):
                yield r['full_name'].split("/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Crea y configura repositorios", formatter_class=RawTextHelpFormatter)
    parser.add_argument('--api', help='Url a la api ej: http://localhost:3000/api/v1')
    parser.add_argument('--token', help='Token para la api')
    parser.add_argument('--if-exists', choices=('overwrite', 'reuse', 'fail'), help=dedent('''
                        ¿Qué hacer si el repositorio ya existe?:
                        - fail: lanzar un error
                        - reuse: continuar adelante y volverlo a configurar
                        - overwrite: eliminarlo, volverlo a crear desde 0 y configurar
    ''').strip(), default='fail')
    parser.add_argument('-d', '--debug', help="Imprimir trazas de depuración", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO)
    #parser.add_argument('--yes', help='Responder a las preguntas con yes/si')
    parser.add_argument('repo', nargs='+', help='Repositorio en formato org/repo')
    pargs = parser.parse_args()

    logging.basicConfig(
        level=pargs.loglevel,
        format='%(message)s',
        datefmt='%Y-%M-%d %H:%M:%S'
    )
    logging.getLogger('urllib3').setLevel(logging.INFO)

    gitea = Gitea(pargs.api, pargs.token)
    for org, repo in iter_repos(gitea, pargs.repo):
        try:
            gitea.new_org(org, if_exists='reuse')
            gitea.new_repo(org, repo, if_exists=pargs.if_exists)
            gitea.config_repo(org, repo)
        except ExAlreadyExist as e:
            logging.critical(str(e))
