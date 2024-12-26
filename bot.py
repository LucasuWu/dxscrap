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
}

# Charger les données précédentes depuis le fichier JSON
def load_previous_data():
    try:
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}  # Retourne un dictionnaire vide si le fichier n'existe pas
    except json.JSONDecodeError:
        return {}  # Retourne un dictionnaire vide si le fichier est corrompu

# Sauvegarder les données actuelles dans un fichier JSON
def save_previous_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file)

# Échapper les caractères réservés de MarkdownV2
def escape_markdown_v2(text):
    if not text:
        return "N/A"
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(rf"([{re.escape(escape_chars)}])", r"\\\1", text)

# Initialisation
previous_data = load_previous_data()

# Fonction pour vérifier les mises à jour
async def check_updates():
    global previous_data

    try:
        response = requests.get(DEXSCREENER_API_URL)
        response.raise_for_status()
        data = response.json()

        # Identifier si la réponse est une liste ou un objet contenant une liste
        if isinstance(data, list):
            tokens = data  # La réponse est directement une liste
        elif isinstance(data, dict) and "tokens" in data:
            tokens = data["tokens"]  # La liste est sous la clé "tokens"
        else:
            logging.error("Format de réponse inconnu :", data)
            return

        for token_data in tokens:  # Parcourir chaque token
            token_id = token_data.get("tokenAddress")

            # Préparer les données actuelles
            current_data = {
                "url": token_data.get("url"),
                "chainId": token_data.get("chainId"),  # Utilisé pour déterminer le topic
                "tokenAddress": token_data.get("tokenAddress"),
                "icon": token_data.get("icon"),
                "description": token_data.get("description"),
                "links": [
                    f"{link.get('label', 'N/A')}: {link.get('url')}"
                    for link in token_data.get("links", [])
                ],
            }

            # Vérifier si ce token a changé
            if previous_data.get(token_id) != current_data:
                logging.info(f"Changement détecté pour le token {token_id}")
                await send_telegram_message(current_data)
                previous_data[token_id] = current_data  # Mettre à jour les données précédentes
            else:
                logging.info(f"Aucun changement détecté pour le token {token_id}")

        save_previous_data(previous_data)  # Sauvegarder toutes les données

    except Exception as e:
        logging.error(f"Erreur lors de la vérification des mises à jour : {e}")

# Fonction pour envoyer un message Telegram
async def send_telegram_message(data):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    message = (
        f"{escape_markdown_v2(data['url'])}\n"
        f"🌐 Blockchain: {escape_markdown_v2(data['chainId'])}\n"
        f"📜 Contract: {escape_markdown_v2(data['tokenAddress'])}\n"
        f"📝 Description: {escape_markdown_v2(data['description'])}\n\n\n"
        f"🔗 Liens:\n" + "\n".join(escape_markdown_v2(link) for link in data["links"])
    )
    
    # Trouver le bon topic en fonction de la blockchain
    topic_id = TOPIC_IDS.get(data['chainId'].lower(), TOPIC_IDS.get("others"))
    if topic_id:
        try:
            if data["icon"]:  # Check if icon exists before sending
                await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, message_thread_id=topic_id, photo=data["icon"], caption=message, parse_mode="MarkdownV2")
            else:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, message_thread_id=topic_id, text=message, parse_mode="MarkdownV2")
        except Exception as e:
            logging.error(f"Error sending message to topic {topic_id}: {e}")
    else:
        logging.warning(f"Pas de topic correspondant pour la blockchain {data['chainId']}")

# Boucle principale
async def main():
    while True:
        await check_updates()
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())