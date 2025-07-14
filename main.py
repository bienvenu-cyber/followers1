import os
import json
import time
import random
from instaloader import Instaloader, Profile
from instabot import Bot
from dotenv import load_dotenv

# Charger les variables d'environnement si besoin
load_dotenv()

CONFIG_PATH = 'config/bots_credentials.json'
FOLLOWERS_DIR = 'followers/'

# Charger les identifiants des bots depuis le fichier JSON
def load_bot_credentials(path=CONFIG_PATH):
    with open(path, 'r') as f:
        data = json.load(f)
    return data['bots']

# Extraire les followers d'un compte public et les stocker dans un fichier JSON
def extract_followers(public_username, output_path):
    L = Instaloader()
    profile = Profile.from_username(L.context, public_username)
    followers = [f.username for f in profile.get_followers()]
    with open(output_path, 'w') as f:
        json.dump({"followers": followers}, f, indent=4)
    print(f"Followers de {public_username} enregistrés dans {output_path}")
    return followers

# Charger la liste des followers depuis un fichier JSON
def load_followers(path):
    with open(path, 'r') as f:
        data = json.load(f)
    return data['followers']

# Utiliser chaque bot pour suivre un utilisateur cible
def send_followers_to_target(target_username, number_of_followers, bot_credentials):
    followed_count = 0
    for bot_cred in bot_credentials:
        if followed_count >= number_of_followers:
            break
        bot = Bot()
        try:
            bot.login(username=bot_cred['username'], password=bot_cred['password'])
            bot.follow(target_username)
            print(f"{bot_cred['username']} suit {target_username}")
            followed_count += 1
            bot.logout()
            time.sleep(random.randint(2, 5))
        except Exception as e:
            print(f"Erreur avec {bot_cred['username']}: {e}")
    print(f"Total followers envoyés à {target_username}: {followed_count}")

if __name__ == "__main__":
    # Demander le nom d'utilisateur public à analyser
    public_username = input("Entrez le nom d'utilisateur public à analyser: ")
    followers_file = os.path.join(FOLLOWERS_DIR, f"followers_{public_username}.json")
    
    # Extraire et sauvegarder les followers
    followers = extract_followers(public_username, followers_file)

    # Charger les identifiants bots
    bot_credentials = load_bot_credentials()

    # Demander le nom d'utilisateur cible
    target_username = input("Entrez le nom d'utilisateur cible à suivre: ")
    # Demander le nombre de followers à envoyer
    number_of_followers = int(input("Entrez le nombre de followers à envoyer: "))

    # Envoyer les followers au compte cible
    send_followers_to_target(target_username, number_of_followers, bot_credentials) 