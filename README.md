# Problema

Queremos que cada vez que se cree un repositorio en Gitea este venga con
una configuración por defecto en cuanto a ramas, grupos y permisos.

# Solución

La idea general es usar [la api gitea](https://try.gitea.io/api/swagger) para configurar los repositorios.

A fines didácticos y de prueba se ha creado un script `cli.py` que realiza el ciclo completo (crear y configurar repositorio),
pero el objetivo final no es que haya una persona encargada de lanzar `cli.py` para crear (y configurar) los repositorios
y todo tenga que pasar por ella. Si no que los repositorios puedan ser creados como siempre (desde la web, por api, etc)
y por cualquier usuario, y sea el sistema quien capture este evento y aplique la configuración de manera transparente
y automática. Para ello se usarán webhook.

## Configuración

La configuración se divide en los siguientes archivos:

1. [`config/org.json`](config/org.json) configuración para las organizaciones que se creen
2. [`config/repo.json`](config/org.json) configuración para los repositorios que se creen
5. [`config/limits.json`](config/limits.json) configuración para segurizar ramas

Los grupos y ramas que aparezcan en [`config/limits.json`](config/limits.json) serán creados automáticamente de la siguiente manera:

* Las ramas será una bifurcación de la rama principal
* Los grupos estarán vacíos (*) y tendrán la configuración [`config/teams/*.json`](config/teams/) si existe un json cuyo nombre en minúsculas
coincida con el grupo, en caso contrarío se usará [`config/teams/default.json`](config/teams/default.json).

Para los `webhook` realmente solo será necesario [`config/limits.json`](config/limits.json) y [`config/teams/*.json`](config/teams/).

\* esto se puede cambiar mejorando el script.

## cli.py

`cli.py` es un script para crear repositorios que realiza las siguientes tareas (siendo `org/repo` el repositorio a crear);

1. Si no existe la organización `org` la crea con la configuración [`config/org.json`](config/org.json)
2. Si existe el repositorio `org/repo`:
   * y no se usa el parámetro `--force` lanza un error y aborta
   * y se usa el parámetro `--force`, lo elimina y continua 
3. Crea el repositorio `org/repo` con la configuración [`config/repo.json`](config/org.json), que usa `auto_init = true`
4. Configura el repositorio `org/repo` con [`config/limits.json`](config/limits.json), lo que implica la creación de ramas y grupos

La clave de todo está en el `auto_init = true`, ya que si un repositorio no está inicializado no se le puede
crear ramas ni configurarlas.

## docker/webhook.py

`webhook.py` es una aproximación para configurar repositorios por medio de [`system webhook`](https://docs.gitea.io/en-us/webhooks/).

Consistiría en configurar [localhost:3000/admin/system-hooks](http://localhost:3000/admin/system-hooks)
(cambiar `localhost:3000` por donde esté la instalación de gitea) para que ciertos eventos realicen peticiones
http a un servidor donde este el código que va a llamar a la api de gitea y configurar el repositorio.

NOTA: `webhook.py` está implementado con un servidor `flask` de pruebas, una implementación real debería ir en otro tipo
de servidor.

Hay dos posibilidades:

1. Capturar el evento de creación de un repositorio para configurarlo
2. Capturar cuando se crea una rama `develop` o `production` para configurar el repositorio sobre el que se ha creado la rama

La 1º opción tiene el problema de que si el repositorio se crea sin `auto_init = true` la configuración fallará
porque no se podrán crear las ramas. Sin embargo, si se encuentra una manera programatica de inicializar repositorios
vacíos, o de forzar que `auto_init` sea siempre `true`, esta opción sería la más transparente y no haría falta nada más.

La 2º opción tiene la ventaja de que nos asegura que el repositorio está inicializado, por lo tanto la
configuración funcionara. La desventaja es que es menos inmediato y que si la rama no es creada manualmente,
si no a raíz de la creación con de un repositorio con `auto_init = true` el evento no se lanza.

Por lo tanto, hasta que no se descubra una manera de forzar `auto_init = true` como un parámetro global, habrá que
habilitar los dos `system webhook` para que operen de la siguiente manera:

1. Cuando se cree un repositorio con `auto_init = true` el `webhook` de creación de repositorio lo configurará
2. Cuando se cree una rama `develop` o `production` se repetirá la configuración (si el repositorio fue creado con `auto_init = true` este paso será redundante, en caso contrario será necesario)

NOTA: Si se quiere probar esto en local ver [docker/README.md](docker/README.md).