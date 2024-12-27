import instaloader
import json
import time
import random
from instabot import Bot

# Initialiser Instaloader
L = instaloader.Instaloader()

# Fonction pour récupérer les abonnés et les enregistrer dans un fichier JSON
def create_bots_json(public_username, filename='bots.json'):
    # Charger le profil public
    profile = instaloader.Profile.from_username(L.context, public_username)
    
    # Récupérer les abonnés
    followers = profile.get_followers()

    # Créer une liste d'abonnés
    bots = []
    for follower in followers:
        bots.append(follower.username)

    # Enregistrer la liste dans un fichier JSON
    with open(filename, 'w') as file:
        json.dump({"bots": bots}, file, indent=4)
    
    print(f"Les abonnés de {public_username} ont été enregistrés dans {filename}")

# Fonction pour charger la liste des comptes bots à partir d'un fichier JSON
def load_bots(filename='bots.json'):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data['bots']

# Fonction pour utiliser chaque bot pour suivre un utilisateur cible
def send_followers_to_target(target_username, number_of_followers, bot_credentials):
    followed_count = 0
    for bot_cred in bot_credentials:
        if followed_count >= number_of_followers:
            break

        # Initialiser et connecter le bot
        bot = Bot()
        bot.login(username=bot_cred['username'], password=bot_cred['password'])

        # Suivre l'utilisateur cible
        bot.follow(target_username)
        print(f"L'utilisateur {bot_cred['username']} suit {target_username}")
        followed_count += 1

        # Déconnecter le bot
        bot.logout()

        # Attendre entre 1 et 3 secondes pour imiter un comportement humain
        time.sleep(random.randint(1, 3))

    print(f"Nombre total de followers envoyés à {target_username} : {followed_count}")

# Charger les bots depuis le fichier
bots = load_bots()

# Demander l'identifiant de l'utilisateur public
public_username = input("Entrez l'identifiant de l'utilisateur public : ")

# Créer le fichier JSON avec les abonnés
create_bots_json(public_username)

# Charger les identifiants des bots (à partir d'un fichier ou entrer manuellement)
bot_credentials = [
    {"username": "bot_user_1", "password": "password1"},
    {"username": "bot_user_2", "password": "password2"},
    {"username": "bot_user_3", "password": "password3"}
    # Ajoutez autant de comptes que nécessaire
]

# Demander l'identifiant de l'utilisateur cible
target_username = input("Entrez l'identifiant de l'utilisateur cible : ")
# Demander le nombre de followers à envoyer
number_of_followers = int(input("Entrez le nombre de followers à envoyer : "))

# Envoyer les followers au compte cible
send_followers_to_target(target_username, number_of_followers, bot_credentials)
