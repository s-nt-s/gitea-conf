import json
import logging
import time
import base64

from requests.exceptions import JSONDecodeError

import requests
from os.path import isfile


def read_js(file):
    if isfile(file):
        with open(file, "r") as f:
            return json.load(f)


logger = logging.getLogger(__name__)


class GitException(Exception):
    pass


class ExAlreadyExist(GitException):
    pass


class ExNotFound(GitException):
    pass


class ExRepoEmpty(GitException):
    pass


class ExOrgIsUser(GitException):
    pass


class ExRepoIsUser(GitException):
    pass


class NoBranch(GitException):
    pass


def new_content(name, email, dt, content, message='INIT', branch='develop', new_branch=None):
    if new_branch is None:
        new_branch = branch
    content = content.encode('utf-8')
    content = base64.b64encode(content)
    content = content.decode('utf-8')
    data = {
        "author": {
            "email": email,
            "name": name,
        },
        "branch": branch,
        "committer": {
            "email": email,
            "name": name,
        },
        "content": content,
        "dates": {
            "author": dt,
            "author": dt,
        },
        "message": message,
        "new_branch": new_branch
    }
    return data


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
        self.last_response = None

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
        self.last_response = requests.request(verb, url, *args, headers=self.headers, **kwargs)
        if len(self.last_response.text.strip()) == 0:
            return None
        logger.log(log, self.last_response.text + "\n")
        if verb in ('POST', 'PATCH', 'DELETE'):
            time.sleep(2)
        return safe_json(self.last_response)

    def get(self, *args, **kwargs):
        return self.rqs('GET', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.rqs('POST', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.rqs('DELETE', *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.rqs('PATCH', *args, **kwargs)

    def get_list(self, url, *args, **kwargs):
        rt = []
        count = -1
        while True:
            count = count + 1
            page = self.rqs('GET', url+"?page="+str(count), *args, **kwargs)
            rt.extend(page)
            if len(page) == 0 or str(len(rt)) == self.last_response.headers['X-Total-Count']:
                return rt
        return rt

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
        logger.debug("# Verificar si existe la organización %s", org)
        r = self.get('/orgs/{}'.format(org))
        if r.get('message') == 'Not Found':
            logger.info("# Crear organización %s", org)
        else:
            if if_exists == 'fail':
                raise ExAlreadyExist("org {} ya existe".format(org))
            if if_exists == 'reuse':
                logger.info("# Reusar organización %s", org)
                return r
            if if_exists == 'overwrite':
                logger.info("# Recrear organización %s", org)
                # TODO: Implementar borrar organización con cuidado de no borrar usuarios
                raise Exception("overwrite no implementado aún")
            else:
                raise Exception("valor inadecuado para if_exists: %s" % if_exists)

        cfg_org = read_js("config/org.json")
        cfg_org['full_name'] = org
        cfg_org['username'] = org
        r = self.post('/orgs', data=cfg_org)
        if r.get('message', '').startswith('user already exists'):
            raise ExOrgIsUser("No se puede crear la organización {} porque es un usuario".format(org))
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
        logger.debug("# Verificar si existe el repositorio %s/%s", org, repo)
        r = self.get('/repos/{}/{}'.format(org, repo))
        if r.get('message') == 'Not Found':
            logger.info("# Crear repositorio %s/%s", org, repo)
        else:
            if if_exists == 'fail':
                raise ExAlreadyExist("repo {} ya existe".format(org))
            if if_exists == 'reuse':
                logger.info("# Reusar repositorio %s/%s", org, repo)
                return r
            if if_exists == 'overwrite':
                logger.info("# Recrear repositorio %s/%s", org, repo)
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

    def get_repos(self, org, repo) -> list:
        """
        Obtiene una lista de repositorios, admitiendo org=* o repo=*
        :param org: Si es '' busca en todas las organizaciones
        :param repo: Si es '' obtiene todos los repositorios de la organización
        """
        if "" not in (org, repo):
            r = self.get('/repos/{}/{}'.format(org, repo))
            if r.get('message') == 'Not Found':
                return []
            return [r]
        orgs = [org]
        if org == "":
            orgs = [i["username"] for i in self.get_list('/orgs')]
        repos = []
        for org in orgs:
            if repo == "":
                repos.extend(self.get_list("/orgs/{}/repos".format(org)))
            else:
                r = self.get('/repos/{}/{}'.format(org, repo))
                if r.get('message') == 'Not Found':
                    repos.append(r)
        return repos

    def config_repo(self, org, repo):
        """
        Configura un repositorio existente
        :param org: Nombre de la organización
        :param repo: Nombre del repositorio
        """
        logger.debug("# Verificar si el repositorio %s es un usuario o una organización", org)
        r = self.get('/orgs/{}'.format(org))
        if r.get('message') == 'Not Found':
            # Es un repositorio de usuario, no de una organización
            # TODO: ¿Qué hacer con los repositorios de usuarios?
            raise ExRepoIsUser("{}/{} es un repositorio de usuario".format(org, repo))
        logger.debug("# Verificar si existe el repositorio %s/%s", org, repo)
        r = self.get('/repos/{}/{}'.format(org, repo))
        if r.get('message') == 'Not Found':
            raise ExNotFound("{}/{} no existe".format(org, repo))

        # Comprobar que la rama por defecto debe ser la definida en config/repo.json
        default_config = read_js("config/repo.json")
        mustdef_branch = default_config['default_branch']
        default_branch = r['default_branch']
        if default_branch != mustdef_branch:
            logger.info("# Corregir rama por defecto: %s/%s %s -> %s", org, repo, default_branch, mustdef_branch)
            self.patch("/repos/{}/{}".format(org, repo), data={"default_branch": mustdef_branch})
            default_branch = mustdef_branch

        logger.debug("# Verificar si existe la rama %s/%s %s", org, repo, default_branch)
        br = self.get("/repos/{}/{}/branches/{}".format(org, repo, default_branch))
        if isinstance(br, dict) and br.get('errors') and len(br['errors']) > 0:
            # TODO: Evitar error inicializando el repositorio
            # https://github.com/go-gitea/gitea/issues/10993
            # https://github.com/go-gitea/gitea/issues/10982
            # self.post("/repos/{}/{}/contents/{}".format(org, repo, "README.md"), data=new_content(
            #     r['owner']['login'],
            #     r['owner']['email'],
            #     r['updated_at'],
            #     r['full_name']
            # ))
            raise NoBranch("\n".join(br['errors']))

        all_limits = read_js("config/limits.json")
        if isinstance(all_limits, dict):
            all_limits = [all_limits]

        branches = set()
        teams = set()
        for limits in all_limits:
            branches.add(limits['branch_name'])
            for k, v in limits.items():
                if k.endswith("_teams") and v:
                    teams = teams.union(v)
        logger.debug("# Obtener grupos de %s", org)
        teams = sorted(teams - set(t['name'] for t in self.get('/orgs/{}/teams'.format(org))))
        branches = sorted(branches)

        for branch in branches:
            logger.debug("# Verificar si existe la rama %s/%s %s", org, repo, branch)
            br = self.get("/repos/{}/{}/branches/{}".format(org, repo, branch))
            if isinstance(br, dict) and br.get('errors') and len(br['errors']) > 0:
                logger.info("# Crear rama %s/%s %s", org, repo, branch)
                # Si no existe la rama, se crea a partir de default_branch
                self.post(
                    '/repos/{}/{}/branches'.format(org, repo),
                    data={
                        "new_branch_name": branch,
                        "old_branch_name": default_branch
                    }
                )

        for team in teams:
            logger.info("# Crear grupo %s %s", org, team)
            data = read_js("config/teams/{}.json".format(team.lower())) or read_js("config/teams/default.json")
            data['name'] = team
            self.post('/orgs/{}/teams'.format(org), data=data)

        logger.info("# Aplicar permisos en %s/%s: %s", org, repo, ", ".join(branches))
        for limits in all_limits:
            self.post('/repos/{}/{}/branch_protections'.format(org, repo), data=limits)
