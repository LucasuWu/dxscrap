
Voici le code complet avec la modification pour envoyer l'URL du contrat en texte brut :

python
import requests
import asyncio
import json
import re
from telegram import Bot
import logging

# Configurations
DEXSCREENER_API_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
TELEGRAM_BOT_TOKEN = "7430294917:AAG4L-quEtfjxg5dHBUv_FMiAJD3X_syQzk"
TELEGRAM_CHAT_ID = "-1002313694418"  # Remplacez avec l'ID réel du channel où se trouvent les topics
CHECK_INTERVAL = 10  # Vérification toutes les 10 secondes
DATA_FILE = "previous_data.json"  # Nom du fichier pour stocker l'état

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Mapping des blockchains aux IDs des topics
TOPIC_IDS = {
    "polygon": 33,
    "ton": 32,
    "avalanche": 30,
    "solana": 23,
    "ethereum": 25,
    "base": 24,
    "arbitrum": 31,
    "sui": 29,
    "fantom": 28,
    "sonic": 27,
    "bsc": 26,
    "others": 38,
    "hyperliquid": 99,
}

# Charger les données précédentes depuis le fichier JSON
def load_previous_data():
    try:
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.info(f"Chargement des données échoué : {e}")
        return {}  # Retourne un dictionnaire vide si le fichier n'existe pas ou est corrompu

# Sauvegarder les données actuelles dans un fichier JSON
def save_previous_data(data):
    try:
        with open(DATA_FILE, "w") as file:
            json.dump(data, file)
    except IOError as e:
        logging.error(f"Erreur lors de la sauvegarde des données : {e}")

# Échapper les caractères réservés de MarkdownV2
def escape_markdown_v2(text):
    if not text:
        return "N/A"
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(rf"([{re.escape(escape_chars)}])", r"\\\1", text)

# Fonction pour vérifier les mises à jour
async def check_updates(previous_data):
    try:
        response = requests.get(DEXSCREENER_API_URL)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            tokens = data
        elif isinstance(data, dict) and "tokens" in data:
            tokens = data["tokens"]
        else:
            logging.error("Format de réponse inconnu :", data)
            return previous_data

        for token_data in tokens:
            token_id = token_data.get("tokenAddress")

            current_data = {
                "url": token_data.get("url"),
                "chainId": token_data.get("chainId"),
                "tokenAddress": token_data.get("tokenAddress"),
                "icon": token_data.get("icon"),
                "description": token_data.get("description"),
                "links": [
                    f"{link.get('label', 'N/A')}: {link.get('url')}"
                    for link in token_data.get("links", [])
                ],
            }

            if previous_data.get(token_id) != current_data:
                logging.info(f"Changement détecté pour le token {token_id}")
                await send_telegram_message(current_data)
                previous_data[token_id] = current_data
            else:
                logging.debug(f"Aucun changement détecté pour le token {token_id}")

        save_previous_data(previous_data)
        return previous_data

    except requests.RequestException as e:
        logging.error(f"Erreur de requête HTTP : {e}")
        return previous_data
    except Exception as e:
        logging.error(f"Erreur inattendue lors de la vérification des mises à jour : {e}")
        return previous_data

# Fonction pour envoyer un message Telegram
async def send_telegram_message(data):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    message = (
        f"{escape_markdown_v2(data['chainId'].upper())}\n"
        f"Contract: {data['url']}\n\n"  # Modification ici pour envoyer l'URL complète non cliquable
        f"{escape_markdown_v2(data['description'])}\n\n\n"
        f"{chr(10).join(escape_markdown_v2(link) for link in data['links'])}"
    )
    
    topic_id = TOPIC_IDS.get(data['chainId'].lower(), TOPIC_IDS.get("others"))
    if topic_id:
        try:
            if data["icon"]:  
                await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, message_thread_id=topic_id, photo=data["icon"], caption=message, parse_mode="MarkdownV2")
            else:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, message_thread_id=topic_id, text=message, parse_mode="MarkdownV2")
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi du message au topic {topic_id}: {e}")
    else:
        logging.warning(f"Pas de topic correspondant pour la blockchain {data['chainId']}")

# Boucle principale
async def main():
    previous_data = load_previous_data()
    while True:
        previous_data = await check_updates(previous_data)
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
