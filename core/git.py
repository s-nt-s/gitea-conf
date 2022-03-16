import json
import logging
import time

from requests.exceptions import JSONDecodeError

import requests
from os.path import isfile


def read_js(file):
    if isfile(file):
        with open(file, "r") as f:
            return json.load(f)


logger = logging.getLogger(__name__)


def safe_json(r):
    try:
        return r.json()
    except JSONDecodeError:
        if r.text and r.text[0] == "{" and r.text[-1] == "}":
            return json.loads("[" + r.text.replace("}{", "},{") + "]")
        logger.critical(r.text)
    return r.text


class Gitea:
    def __init__(self, root, token):
        self.root = root
        self.token = token
        self.headers = {
            "content-type": "application/json",
            "Authorization": "token " + self.token
        }

    def rqs(self, verb, url, *args, log=logging.DEBUG, **kwargs):
        verb = verb.upper()
        url = self.root + url
        if kwargs.get('data') and isinstance(kwargs['data'], dict):
            kwargs['data'] = json.dumps(kwargs['data'])
        if log:
            curl = "curl -X {} '{}'".format(verb, url)
            if kwargs.get('data'):
                curl = curl + " -d '" + kwargs['data'] + "'"
            logger.log(log, "$ " + curl)
        r = requests.request(verb, url, *args, headers=self.headers, **kwargs)
        if len(r.text.strip()) == 0:
            return None
        logger.log(log, r.text + "\n")
        if verb in ('POST', 'PATCH', 'DELETE'):
            time.sleep(2)
        return safe_json(r)

    def get(self, *args, **kwargs):
        return self.rqs('GET', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.rqs('POST', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.rqs('DELETE', *args, **kwargs)

    def new_org(self, org, if_exists='fail'):
        """
        Crea una organización
        :param org: Nombre de la organización
        :param if_exists:
            - reuse: reusar si existe
            - overwrite: sobreescribir si existe
            - fail: fallar si existe
        :return: Información de la organización
        """
        r = self.get('/orgs/{}'.format(org))
        if r.get('message') != 'Not Found':
            if if_exists == 'fail':
                raise Exception("{} ya existe".format(org))
            if if_exists == 'reuse':
                return r
            if if_exists == 'overwrite':
                # TODO: Implementar borrar organización con cuidado de no borrar usuarios
                raise Exception("overwrite no implementado aún")
            else:
                raise Exception("valor inadecuado para if_exists: %s" % if_exists)
        cfg_org = read_js("config/org.json")
        cfg_org['full_name'] = org
        cfg_org['username'] = org
        r = self.post('/orgs', data=cfg_org)
        if r.get('message', '').startswith('user already exists'):
            raise Exception("No se puede crear la organización {} porque es un usuario".format(org))
        if not (isinstance(r, dict) and "id" in r):
            raise Exception("Salida no esperada %s" % r)
        r = self.get('/orgs/{}'.format(org))
        return r

    def new_repo(self, org, repo, if_exists='fail'):
        """
        Crea un repositorio
        :param org: Nombre de la organización
        :param repo: Nombre del repositorio
        :param if_exists:
            - reuse: reusar si existe
            - overwrite: sobreescribir si existe
            - fail: fallar si existe
        :return: Información del repositorio
        """
        r = self.get('/repos/{}/{}'.format(org, repo))
        if r.get('message') != 'Not Found':
            if if_exists == 'fail':
                raise Exception("{} ya existe".format(org))
            if if_exists == 'reuse':
                return r
            if if_exists == 'overwrite':
                self.delete('/repos/{}/{}'.format(org, repo))
            else:
                raise Exception("valor inadecuado para if_exists: %s" % if_exists)

        cfg_repo = read_js("config/repo.json")
        cfg_repo['name'] = repo
        r = self.post(
            '/orgs/{}/repos'.format(org),
            data=cfg_repo
        )
        if not (isinstance(r, dict) and "id" in r):
            raise Exception("Salida no esperada %s" % r)
        r = self.get('/repos/{}/{}'.format(org, repo))
        return r

    def config_repo(self, org, repo):
        """
        Configura un repositorio existente
        :param org: Nombre de la organización
        :param repo: Nombre del repositorio
        """
        r = self.get('/orgs/{}'.format(org))
        if r.get('message') == 'Not Found':
            # Es un repositorio de usuario, no de una organización
            # TODO: ¿Qué hacer con los repositorios de organizaciones?
            logger.debug("{}/{} es un repositorio de usuario".format(org, repo))
            return
        r = self.get('/repos/{}/{}'.format(org, repo))
        if r.get('message') == 'Not Found':
            raise Exception("{}/{} no existe".format(org, repo))
        # TODO: Devolver error si el repositorio no esta inicializado

        all_limits = read_js("config/limits.json")
        if isinstance(all_limits, dict):
            all_limits = [all_limits]

        branchs = set()
        teams = set()
        for limits in all_limits:
            branchs.add(limits['branch_name'])
            for k, v in limits.items():
                if k.endswith("_teams") and v:
                    teams = teams.union(v)
        teams = teams - set(t['name'] for t in self.get('/orgs/{}/teams'.format(org)))

        for branch in sorted(branchs):
            # TODO: Verificar que la rama por defecto es la que debe ser (en caso contrarío ¿qué hacer? ¿crearla?)
            # TODO: Evitar crear la rama si ya existe
            self.post(
                '/repos/{}/{}/branches'.format(org, repo),
                data={
                    "new_branch_name": branch,
                    "old_branch_name": r['default_branch']
                }
            )

        for team in teams:
            data = read_js("config/teams/{}.json".format(team.lower())) or read_js("config/teams/default.json")
            data['name'] = team
            self.post('/orgs/{}/teams'.format(org), data=data)

        for limits in all_limits:
            self.post('/repos/{}/{}/branch_protections'.format(org, repo), data=limits)
