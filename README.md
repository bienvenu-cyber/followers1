# followers1

## Objectif
Automatiser la récupération des followers d'un compte Instagram public et utiliser des bots pour suivre un compte cible.

## Installation

1. Clonez le dépôt et placez-vous dans le dossier :
   ```bash
   git clone <repo_url>
   cd followers1
   ```
2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Identifiants bots** :
   - Modifiez le fichier `config/bots_credentials.json` pour y placer les identifiants de vos comptes bots Instagram.
   - **Ne partagez jamais ce fichier !**

2. **Dossiers** :
   - Les followers extraits seront stockés dans le dossier `followers/`.

## Utilisation

Lancez le script principal :
```bash
python main.py
```

Vous devrez fournir :
- Le nom d'utilisateur public à analyser (pour extraire ses followers)
- Le nom d'utilisateur cible à suivre
- Le nombre de followers à envoyer

## Dépendances
- instaloader
- instabot
- python-dotenv
- selenium
- webdriver-manager

## Sécurité & Éthique
- **N'utilisez ce script que sur des comptes de test ou avec l'accord des personnes concernées.**
- L'automatisation de followers est contraire aux CGU d'Instagram et peut entraîner des bannissements.
- Ne stockez jamais vos identifiants dans un dépôt public.

## Limites & Conseils
- Ne lancez pas trop d'actions à la suite (risque de blocage).
- Ajoutez des délais aléatoires entre les actions.
- Surveillez les logs pour détecter d'éventuels blocages ou erreurs.

---
**Pour toute question ou amélioration, ouvrez une issue ou contactez le mainteneur.**