FROM gitea/gitea:1.13.0

RUN ls /etc/gitea
RUN data migrate
RUN data admin create-user --admin --username gitadmin --password gitadmin --email gitadmin@test.com --must-change-password false