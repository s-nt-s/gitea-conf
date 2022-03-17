# Problema

Queremos que cada vez que se cree un repositorio en Gitea este venga con
una configuración por defecto en cuanto a ramas, grupos y permisos.

# Solución

La idea general es usar [la api gitea](https://try.gitea.io/api/swagger) para crear y/o configurar los repositorios.

## Configuración

La configuración se divide en los siguientes archivos:

1. [`config/org.json`](config/org.json) configuración para las organizaciones que se creen
2. [`config/repo.json`](config/org.json) configuración para los repositorios que se creen
5. [`config/limits.json`](config/limits.json) configuración para segurizar ramas

Los grupos y ramas que aparezcan en [`config/limits.json`](config/limits.json) serán creados automáticamente de la siguiente manera:

* Las ramas será una bifurcación de la rama principal
* Los grupos tendrán la configuración [`config/teams/*.json`](config/teams/) si existe un json cuyo nombre en minúsculas
coincida con el grupo, en caso contrarío se usará [`config/teams/default.json`](config/teams/default.json)

## cli.py

`cli.py` es un script para crear repositorios que realiza las siguientes tareas (siendo `org/repo` el repositorio a crear);

1. Si no existe la organización `org` la crea con la configuración [`config/org.json`](config/org.json)
2. Si existe el repositorio `org/repo` lanza un error, o lo elimina si se usa el parámetro `--force`
3. Crea el repositorio `org/repo` con la configuración [`config/repo.json`](config/org.json), que usa `auto_init = true`
4. Configura el repositorio `org/repo` con [`config/limits.json`](config/limits.json), lo que implica la creación de ramas (bifurcadas de la principal) y grupos (vacíos)

La clave de todo está en el `auto_init = true`, ya que si un repositorio no está inicializado no se le puede
crear ramas ni configurarlas.

## docker/webhook.py

`webhook.py` es una aproximación para configurar repositorios por medio de [`system webhook`](https://docs.gitea.io/en-us/webhooks/).

Consistiría en configurar [localhost:3000/admin/system-hooks](http://localhost:3000/admin/system-hooks) para que ciertos
eventos realicen peticiones http a un servidor donde este el código que va a llamar a la api de gitea y configurar el
repositorio.

NOTA: `webhook.py` está implementado con un servidor `flask` de pruebas, una implementación real debería ir en otro tipo
de servidor.

Hay dos aproximaciones posibles:

1. Capturar el evento de creación de un repositorio para configurarlo
2. Capturar cuando se crea una rama `develop` o `production` para configurar el repositorio sobre el que se ha creado la rama

La 1º aproximación tiene el problema de que si el repositorio se crea sin `auto_init = true` la configuración fallará
porque no se podrán crear las ramas. Sin embargo, si se encuentra una manera programatica de inicializar repositorios
vacíos, o de forzar que `auto_init` sea siempre `true`, esta aproximación sería la más transparente.

La 2º aproximación tiene la ventaja de que nos asegura que el repositorio está inicializado, por lo tanto la
configuración funcionara. La desventaja es que es menos inmediato y que si la rama no es creada manualmente,
si no a raíz de la creación con de un repositorio con `auto_init = true` el evento no se lanza.

Por lo tanto, hasta que no se descubra una manera de forzar `auto_init = true` como un parámetro global, habré que
habilitar los dos `system webhook` para que operen de la siguiente manera:

1. Cuando se cree un repositorio con `auto_init = true` el `webhook` de creación de repositorio lo configurará
2. Cuando se cree una rama `develop` o `production` se repetirá la configuración (si el repositorio fue creado con `auto_init = true` este paso será redundante, en caso contrario será necesario)