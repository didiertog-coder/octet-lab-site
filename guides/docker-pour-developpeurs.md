---
title: Docker pour les développeurs solo : conteneuriser ses projets en 30 minutes
description: Isolez vos environnements de développement, évitez les conflits de versions et déployez en un seul fichier.
category: Développement
---
Docker résout un problème universel : « ça marche sur ma machine ». En encapsulant une application et toutes ses dépendances dans une image portable, vous garantissez un comportement identique du développement à la production.

## Les concepts en deux minutes

- **Image** : un snapshot en lecture seule de votre application + ses dépendances.
- **Conteneur** : une instance en cours d'exécution d'une image, isolée du reste du système.
- **Dockerfile** : le script qui décrit comment construire une image.
- **docker-compose.yml** : orchestre plusieurs conteneurs ensemble (app + base de données, par exemple).

## Installer Docker

Sur Linux (Debian/Ubuntu) :
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # évite sudo à chaque commande
```

Sur Windows/Mac : téléchargez **Docker Desktop** sur [docker.com](https://www.docker.com/products/docker-desktop).

## Un Dockerfile minimal pour une app Python

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t mon-api .
docker run -p 8000:8000 mon-api
```

## Composer une stack complète

```yaml
# docker-compose.yml
services:
  app:
	build: .
	ports: ["8000:8000"]
	environment:
	  DATABASE_URL: postgresql://user:pass@db/mabase
	depends_on: [db]
  db:
	image: postgres:16-alpine
	volumes: [pgdata:/var/lib/postgresql/data]
	environment:
	  POSTGRES_USER: user
	  POSTGRES_PASSWORD: pass
	  POSTGRES_DB: mabase
volumes:
  pgdata:
```

```bash
docker compose up -d      # démarre tout en arrière-plan
docker compose logs -f    # suit les logs
docker compose down       # arrête et supprime les conteneurs
```

## Bonnes pratiques

- **Images légères** : préférez les variantes `-slim` ou `-alpine`. Une image Python slim fait ~70 Mo contre ~900 Mo pour l'image complète.
- **Ne pas stocker de secrets dans l'image** : utilisez des variables d'environnement ou des fichiers `.env` hors dépôt git.
- **Un processus par conteneur** : ne mélangez pas app et base de données dans la même image.
- **Volumes pour la persistance** : toute donnée écrite dans un conteneur sans volume est perdue à l'arrêt.
- **`.dockerignore`** : excluez `node_modules`, `.git`, `__pycache__` pour accélérer le build et alléger l'image.

## Surveiller ses conteneurs

```bash
docker ps                    # conteneurs en cours
docker stats                 # CPU/RAM en temps réel
docker exec -it mon-api sh   # shell dans le conteneur
docker system prune -f       # nettoyage des images et conteneurs inutiles
```
