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
            curl = f"curl -X {verb} '{url}'"
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

    def get(self, *args, null404=False, **kwargs):
        """
        :param null404: Si es True y la petición da un 404 se devuelve None
        """
        r = self.rqs('GET', *args, **kwargs)
        if null404 and self.last_response.status_code == 404:
            return None
        return r

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
            page = self.rqs('GET', url + "?page=" + str(count), *args, **kwargs)
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
        logger.debug(f"# Verificar si existe la organización {org}")
        r = self.get(f'/orgs/{org}', null404=True)
        if r is None:
            logger.info(f"# Crear organización {org}")
        else:
            if if_exists == 'fail':
                raise ExAlreadyExist(f"org {org} ya existe")
            if if_exists == 'reuse':
                logger.info(f"# Reusar organización {org}")
                return r
            if if_exists == 'overwrite':
                logger.info(f"# Recrear organización {org}")
                # TODO: Implementar borrar organización con cuidado de no borrar usuarios
                raise Exception("overwrite no implementado aún")
            else:
                raise Exception(f"valor inadecuado para if_exists: {if_exists}")

        cfg_org = read_js("config/org.json")
        cfg_org['full_name'] = org
        cfg_org['username'] = org
        r = self.post('/orgs', data=cfg_org)
        if r.get('message', '').startswith('user already exists'):
            raise ExOrgIsUser(f"No se puede crear la organización {org} porque es un usuario")
        if not (isinstance(r, dict) and "id" in r):
            raise Exception("Salida no esperada %s" % r)
        r = self.get(f'/orgs/{org}')
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
        logger.debug(f"# Verificar si existe el repositorio {org}/{repo}")
        r = self.get(f'/repos/{org}/{repo}', null404=True)
        if r is None:
            logger.info(f"# Crear repositorio {org}/{repo}")
        else:
            if if_exists == 'fail':
                raise ExAlreadyExist(f"repo {org}/{repo} ya existe")
            if if_exists == 'reuse':
                logger.info(f"# Reusar repositorio {org}/{repo}")
                return r
            if if_exists == 'overwrite':
                logger.info(f"# Recrear repositorio {org}/{repo}")
                self.delete(f'/repos/{org}/{repo}')
            else:
                raise Exception(f"valor inadecuado para if_exists: {if_exists}")

        cfg_repo = read_js("config/repo.json")
        cfg_repo['name'] = repo
        r = self.post(f'/orgs/{org}/repos', data=cfg_repo)
        if not (isinstance(r, dict) and "id" in r):
            raise Exception("Salida no esperada %s" % r)
        r = self.get(f'/repos/{org}/{repo}')
        return r

    def get_repos(self, org, repo) -> list:
        """
        Obtiene una lista de repositorios, admitiendo org=* o repo=*
        :param org: Si es '' busca en todas las organizaciones
        :param repo: Si es '' obtiene todos los repositorios de la organización
        """
        if "" not in (org, repo):
            r = self.get(f'/repos/{org}/{repo}', null404=True)
            return [r] if r else []
        orgs = [org]
        if org == "":
            orgs = [i["username"] for i in self.get_list('/orgs')]
        repos = []
        for org in orgs:
            if repo == "":
                repos.extend(self.get_list(f"/orgs/{org}/repos"))
            else:
                r = self.get(f'/repos/{org}/{repo}', null404=True)
                if r:
                    repos.append(r)
        return repos

    def config_repo(self, org, repo):
        """
        Configura un repositorio existente
        :param org: Nombre de la organización
        :param repo: Nombre del repositorio
        """
        logger.debug(f"# Verificar si el repositorio {org} es un usuario o una organización")
        if self.get(f'/orgs/{org}', null404=True) is None:
            # Es un repositorio de usuario, no de una organización
            # TODO: ¿Qué hacer con los repositorios de usuarios?
            raise ExRepoIsUser(f"{org}/{repo} es un repositorio de usuario")
        logger.debug(f"# Verificar si existe el repositorio {org}/{repo}")
        r = self.get(f'/repos/{org}/{repo}', null404=True)
        if r is None:
            raise ExNotFound(f"{org}/{repo} no existe")

        # Comprobar que la rama por defecto debe ser la definida en config/repo.json
        default_config = read_js("config/repo.json")
        mustdef_branch = default_config['default_branch']
        default_branch = r['default_branch']
        if default_branch != mustdef_branch:
            logger.info(f"# Corregir rama por defecto: {org}/{repo} {default_branch} -> {mustdef_branch}")
            self.patch(f"/repos/{org}/{repo}", data={"default_branch": mustdef_branch})
            default_branch = mustdef_branch

        logger.debug(f"# Verificar si existe la rama {org}/{repo} {default_branch}")
        br = self.get(f"/repos/{org}/{repo}/branches/{default_branch}")
        if self.last_response.status_code == 404:
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
        teams = sorted(teams)
        branches = sorted(branches)

        for branch in branches:
            logger.debug(f"# Verificar si existe la rama {org}/{repo} {branch}")
            if self.get(f"/repos/{org}/{repo}/branches/{branch}", null404=True) is None:
                logger.info(f"# Crear rama {org}/{repo} {branch}")
                # Si no existe la rama, se crea a partir de default_branch
                self.post(
                    f'/repos/{org}/{repo}/branches',
                    data={
                        "new_branch_name": branch,
                        "old_branch_name": default_branch
                    }
                )

        logger.info(f"# Crear grupos {org}: {', '.join(teams)}")
        self.create_teams(org, *teams)

        logger.info(f"# Aplicar permisos en {org}/{repo}: {', '.join(branches)}")
        self.branch_protections(org, repo, *all_limits)

    def create_teams(self, org, *teams):
        """
        Crea el grupo team en la organización org
        Si el grupo ya existe, actualiza su configuración
        """
        logger.debug("# Obtener grupos de %s", org)
        old_teams = {t['name']: t for t in self.get_list(f'/orgs/{org}/teams')}

        for team in teams:
            confg = read_js(f"config/teams/{team.lower()}.json") or read_js("config/teams/default.json")
            confg['name'] = team
            if team in old_teams:
                logger.debug(f"# Reconfigurar grupo {org}: {team}")
                self.patch(f"/teams/{old_teams[team]['id']}", data=confg)
            else:
                logger.debug(f"# Crear grupo {org}: {team}")
                self.post(f'/orgs/{org}/teams', data=confg)

    def branch_protections(self, org, repo, *limits_list):
        """
        Protege una rama limits['branch_name'] del repositorio org/repo con los límites limits
        Si ya existía una protección, la elimina y la vuelve a crear de cero
        """
        for limits in limits_list:
            branch = limits['branch_name']
            logger.debug(f"# Verificar si existe la protección para la rama {org}/{repo} {branch}")
            if self.get(f'/repos/{org}/{repo}/branch_protections/{branch}', null404=True):
                logger.debug(f"# Crear protección para la rama {org}/{repo} {branch}")
                self.post(f'/repos/{org}/{repo}/branch_protections/', data=limits)
            else:
                logger.debug(f"# Borrar protección para la rama {org}/{repo} {branch}")
                self.delete(f'/repos/{org}/{repo}/branch_protections/')
                logger.debug(f"# Recrear protección para la rama {org}/{repo} {branch}")
                self.patch(f'/repos/{org}/{repo}/branch_protections/{branch}', data=limits)
