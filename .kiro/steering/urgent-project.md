---
inclusion: always
---

# 🚨 PROJET URGENT ET CAPITAL - Instagram Auto Signup

## PRIORITÉ ABSOLUE
Ce projet doit fonctionner IMMÉDIATEMENT. Pas de théorie, que de l'action.

## DIRECTIVES STRICTES

### 1. APPROCHE PRAGMATIQUE
- Trouver les solutions les PLUS RAPIDES et EFFICACES
- Implémenter ce qui FONCTIONNE, pas ce qui est "idéal"
- Tester immédiatement chaque modification
- Si une approche échoue, passer à la suivante SANS DÉLAI

### 2. FOCUS SUR LE FONCTIONNEL
- Le bot DOIT créer des comptes Instagram POUR PERMETTRE D'ENVOYER COMME ABONNEES A UN COMPTE TEST 
- Chaque composant doit être opérationnel
- Corriger les bugs AVANT d'ajouter des features
- Prioriser : Email service > Sélecteurs > Anti-détection

### 3. FICHIER PRINCIPAL
- `main.py` est le SEUL point d'entrée
- Tout le code fonctionnel est dans `src/`
- Configuration dans `config/system_config.json`

### 4. PROBLÈMES CONNUS À RÉSOUDRE
1. Services email non configurés (email_services: [])
2. Sélecteurs Instagram potentiellement obsolètes
3. Extraction du code de vérification défaillante
4. Pas de proxies fonctionnels
5. Pas de captcha fonctionnel
6.probleme de proxies

### 5. NE PAS PERDRE DE TEMPS SUR
- Documentation
- Tests unitaires (pour l'instant)
- Refactoring esthétique
- Optimisations prématurées

## OBJECTIF FINAL
Un système qui crée des comptes Instagram de manière automatisée et fiable.
