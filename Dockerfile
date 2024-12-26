# Utiliser une image de base pour Python
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY bot.py .

# Installer les dépendances
RUN pip install --no-cache-dir requests python-telegram-bot

# Commande pour démarrer l'application
CMD ["python", "bot.py"]
