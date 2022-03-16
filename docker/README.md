Instalación gitea en docker para hacer pruebas

* Levantar: `docker-compose up -d`
* Parar: `docker-compose down`
* Borrar: `docker-compose stop && docker-compose rm --force && sudo rm -R data/*`
* Ver ip host en contenedor: docker exec $(docker ps | grep "gitea/gitea" | cut -d' ' -f1) /sbin/ip route|awk '/default/ { print $3 }'
* Entrar a gitea: http://localhost:3000/