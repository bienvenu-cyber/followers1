# Requirements Document

## Introduction

Ce projet vise à moderniser et optimiser le système de création automatique de comptes Instagram pour maximiser le taux de succès et la vitesse de création. L'objectif est de créer le maximum de comptes possibles toutes les 5 minutes en contournant les mesures de détection d'Instagram.

## Requirements

### Requirement 1

**User Story:** En tant qu'utilisateur du système, je veux créer automatiquement des comptes Instagram en masse, afin de disposer d'un pool de comptes bots pour mes opérations.

#### Acceptance Criteria

1. WHEN le système est lancé THEN il SHALL créer des comptes Instagram de manière continue
2. WHEN un cycle de création est terminé THEN le système SHALL attendre 5 minutes avant le prochain cycle
3. WHEN un compte est créé avec succès THEN les identifiants SHALL être sauvegardés dans le fichier de configuration
4. WHEN le système rencontre une erreur THEN il SHALL passer au service suivant sans arrêter le processus

### Requirement 2

**User Story:** En tant qu'utilisateur, je veux que le système évite la détection par Instagram, afin de maximiser le taux de succès des créations de comptes.

#### Acceptance Criteria

1. WHEN le système navigue sur Instagram THEN il SHALL simuler un comportement humain réaliste
2. WHEN le système remplit les formulaires THEN il SHALL utiliser des délais aléatoires entre les frappes
3. WHEN le système fait des requêtes THEN il SHALL utiliser des user-agents rotatifs et des proxies
4. WHEN le système détecte un CAPTCHA THEN il SHALL implémenter des stratégies de contournement
5. WHEN le système est bloqué THEN il SHALL changer automatiquement de proxy et d'identité

### Requirement 3

**User Story:** En tant qu'utilisateur, je veux que le système utilise des services d'email temporaire fiables, afin de recevoir les codes de validation Instagram.

#### Acceptance Criteria

1. WHEN un service d'email échoue THEN le système SHALL basculer automatiquement vers le service suivant
2. WHEN un domaine email est blacklisté THEN le système SHALL l'éviter pour les prochaines tentatives
3. WHEN un code de validation est reçu THEN il SHALL être extrait automatiquement du contenu de l'email
4. WHEN aucun code n'est reçu après 2 minutes THEN le système SHALL passer au service suivant
5. WHEN tous les services d'email échouent THEN le système SHALL implémenter des services de fallback

### Requirement 4

**User Story:** En tant qu'utilisateur, je veux que le système gère intelligemment les erreurs et les échecs, afin de maintenir une création continue sans intervention manuelle.

#### Acceptance Criteria

1. WHEN une erreur Selenium survient THEN le système SHALL redémarrer le navigateur et réessayer
2. WHEN un élément n'est pas trouvé THEN le système SHALL utiliser des sélecteurs alternatifs
3. WHEN Instagram change son interface THEN le système SHALL s'adapter automatiquement
4. WHEN un proxy ne fonctionne pas THEN il SHALL être marqué comme invalide et évité
5. WHEN le taux d'échec dépasse 80% THEN le système SHALL ajuster ses stratégies automatiquement

### Requirement 5

**User Story:** En tant qu'utilisateur, je veux surveiller les performances du système en temps réel, afin d'optimiser les paramètres et identifier les problèmes.

#### Acceptance Criteria

1. WHEN le système fonctionne THEN il SHALL afficher des statistiques en temps réel
2. WHEN un compte est créé THEN le système SHALL incrémenter les compteurs de succès
3. WHEN une erreur survient THEN elle SHALL être loggée avec tous les détails pertinents
4. WHEN un cycle se termine THEN le système SHALL afficher un résumé des performances
5. WHEN le système détecte des patterns d'échec THEN il SHALL suggérer des optimisations

### Requirement 6

**User Story:** En tant qu'utilisateur, je veux que le système soit configurable et extensible, afin de pouvoir ajuster les paramètres selon les besoins.

#### Acceptance Criteria

1. WHEN je modifie la configuration THEN les changements SHALL être appliqués sans redémarrage
2. WHEN j'ajoute de nouveaux services d'email THEN ils SHALL être intégrés automatiquement
3. WHEN j'ajoute de nouveaux proxies THEN ils SHALL être testés et validés automatiquement
4. WHEN je change les délais THEN le système SHALL s'adapter immédiatement
5. WHEN j'active le mode debug THEN le système SHALL fournir des informations détaillées

### Requirement 7

**User Story:** En tant qu'utilisateur, je veux que le système optimise automatiquement ses performances, afin de maintenir le meilleur taux de succès possible.

#### Acceptance Criteria

1. WHEN le système détecte des patterns de succès THEN il SHALL privilégier ces stratégies
2. WHEN un service d'email a un bon taux de succès THEN il SHALL être utilisé en priorité
3. WHEN certains user-agents fonctionnent mieux THEN ils SHALL être favorisés
4. WHEN des horaires sont plus favorables THEN le système SHALL s'adapter
5. WHEN Instagram met à jour ses défenses THEN le système SHALL ajuster ses techniques automatiquement