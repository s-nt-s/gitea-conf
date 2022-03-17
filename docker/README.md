Instalación gitea en docker para hacer pruebas

* Levantar: `docker-compose up -d`
* Parar: `docker-compose down`
* Borrar: `docker-compose stop && docker-compose rm --force && sudo rm -R data/*`
* Ver ip host en contenedor: `docker exec $(docker ps | grep "gitea/gitea" | cut -d' ' -f1) /sbin/ip route|awk '/default/ { print $3 }'`
* Entrar a gitea: [localhost:3000](http://localhost:3000/)
* Reiniciar: `docker-compose down && docker-compose up -d && sleep 5 && docker exec $(docker ps | grep "gitea/gitea" | cut -d' ' -f1) /sbin/ip route|awk '/default/ { print $3 }'`
* Arrancar webhooks: python -m docker.webhook
* Configurar [localhost:3000/admin/system-hooks](http://localhost:3000/admin/system-hooks) usando la ip host obtenida más arriba