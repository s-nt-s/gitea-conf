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