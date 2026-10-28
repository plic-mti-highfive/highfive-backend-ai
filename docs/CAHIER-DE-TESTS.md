# Cahier de tests — backend IA

Service FastAPI de recommandation (embeddings pgvector, files BullMQ). Ce cahier recense les
scénarios de test par module. Légende des statuts : ✅ existant, 🆕 ajouté en T10, 🐞 bug trouvé.

## Types de tests et exécution

| Type | Emplacement | Dépendances |
| --- | --- | --- |
| Unitaire | `tests/unit/` | Majoritairement mocks ; certains tests de repository/service utilisent la base |
| Intégration | `tests/integration/` | PostgreSQL pgvector + Redis réels, vrais handlers, provider factice (`scripts/fake_provider.py`), vrai JWT |
| Charge | `load/` (Locust) | Base seedée, API, worker de charge factice, passerelle de file (voir `load/README.md`) |

Aucun test n'appelle OpenAI : le provider factice est déterministe et sans réseau.

### Lancer les tests

```bash
scripts/test.sh                      # toute la suite
scripts/test.sh tests/unit -q        # arguments transmis à pytest
scripts/test.sh --cov=src --cov-report=term
```

### Stratégie : bases jetables

`scripts/test.sh` démarre un `pgvector/pgvector:pg16` (base `highfive_test`, tmpfs) et un
`redis:7-alpine` sur des ports aléatoires (conteneurs `hf-ai-test-*`), applique les migrations,
lance pytest, puis supprime les conteneurs (`trap` : succès, échec, Ctrl-C ou SIGTERM). Si
`DATABASE_URI` est déjà fourni (CI GitHub Actions, avec ses `services:` jetables), rien n'est démarré.
Garde-fou : `tests/conftest.py` interrompt la session si le nom de la base ne contient pas `test`,
pour ne jamais polluer une base de développement.

## Couverture

| | Tests collectés | Couverture `src/` |
| --- | --- | --- |
| Avant T10 | 149 | 91 % |
| Après T10 | 176 | 96 % |

Gains principaux : `worker/main.py` 0 % → 100 %, `infrastructure/database.py` 73 % → 100 %,
`embedding_repository.py` 86 % → 99 %.

## Scénarios par module

### Matchmaking (API /matchmaking/*)

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-MATCH-01 | Reco de projets classées par similarité, positions 0..n | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-02 | Items exposés avec métadonnées, sans le vecteur | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-03 | Le paramètre `limit` est respecté | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-04 | `limit` invalide : 422 et non 500 | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-05 | Filtre `tags` sur le thème | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-06 | Utilisateur inconnu : repli sur le trending | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-07 | Les interactions (like/apply) font évoluer les recommandations | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-08 | Isolation tenant : un autre tenant obtient des listes vides | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-09 | Utilisateurs recommandés pour un projet, triés et filtrés par similarité | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-10 | Projet inconnu : liste vide | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-11 | Trending trié par likes, `limit` respecté | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-12 | Trending exclut les utilisateurs | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-13 | Authentification requise (aucun jeton, jeton invalide, tenant invalide) sur les 3 routes | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-14 | Jeton sans `tenantId` : 401 | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-15 | UUID invalide dans le chemin : 422 | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-16 | Vecteurs d'identité présents après seed | intégration | `tests/integration/test_matchmaking_endpoints.py` | ✅ existant |
| AI-MATCH-17 | Jeton expiré : 401 « Expired token » (3 routes) | intégration | `tests/integration/test_matchmaking_endpoints.py` | 🆕 ajouté T10 |
| AI-MATCH-18 | Mauvaise signature : 401 (3 routes) | intégration | `tests/integration/test_matchmaking_endpoints.py` | 🆕 ajouté T10 |
| AI-MATCH-19 | Jeton `alg=none` non signé : 401 (3 routes) | intégration | `tests/integration/test_matchmaking_endpoints.py` | 🆕 ajouté T10 |
| AI-MATCH-20 | Jeton sans `sub` : 401 (3 routes) | intégration | `tests/integration/test_matchmaking_endpoints.py` | 🆕 ajouté T10 |
| AI-MATCH-21 | Claim `tenantId` absent : 401 « Missing tenantId » (3 routes) | intégration | `tests/integration/test_matchmaking_endpoints.py` | 🆕 ajouté T10 |
| AI-MATCH-22 | Schéma d'autorisation non Bearer / vide : 401 ou 403 | intégration | `tests/integration/test_matchmaking_endpoints.py` | 🆕 ajouté T10 |
| AI-MATCH-23 | Un tenant étranger ne voit jamais les embeddings d'un autre (et réciproquement) | intégration | `tests/integration/test_matchmaking_endpoints.py` | 🆕 ajouté T10 |

### Matchmaking (compléments)

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-MATCH-24 | Projets recommandés pour un utilisateur via l'API avec auth surchargée et RLS | intégration | `tests/integration/test_matchmaking_api.py` | ✅ existant |

### Matchmaking (service)

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-MATCH-25 | Recommandations de projets pour un utilisateur (service + base réelle) | unitaire | `tests/unit/test_matchmaking_service.py` | ✅ existant |

### Repository d'embeddings et RLS

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-REPO-01 | Création puis lecture d'un embedding | unitaire | `tests/unit/test_embedding_repo.py` | ✅ existant |
| AI-REPO-02 | Isolation RLS par tenant (rôle restreint) | unitaire | `tests/unit/test_embedding_repo.py` | ✅ existant |
| AI-REPO-03 | `update` remplace vecteur et métadonnées | unitaire | `tests/unit/test_embedding_repo.py` | 🆕 ajouté T10 |
| AI-REPO-04 | `update` sur embedding inconnu : ValueError | unitaire | `tests/unit/test_embedding_repo.py` | 🆕 ajouté T10 |
| AI-REPO-05 | `get_all` ne renvoie que le tenant courant | unitaire | `tests/unit/test_embedding_repo.py` | 🆕 ajouté T10 |
| AI-REPO-06 | Lectures et plus proches voisins d'un autre tenant : vides | unitaire | `tests/unit/test_embedding_repo.py` | 🆕 ajouté T10 |

### Contexte tenant en base

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-REPO-07 | `get_db_with_tenant` pose `app.current_tenant_id` | unitaire | `tests/unit/test_database_tenant.py` | 🆕 ajouté T10 |
| AI-REPO-08 | Contexte nettoyé à la sortie, même sur exception | unitaire | `tests/unit/test_database_tenant.py` | 🆕 ajouté T10 |

### Sécurité JWT

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-AUTH-01 | Décodage d'un jeton valide | unitaire | `tests/unit/test_security.py` | ✅ existant |
| AI-AUTH-02 | Jeton expiré rejeté | unitaire | `tests/unit/test_security.py` | ✅ existant |
| AI-AUTH-03 | Jeton illisible rejeté | unitaire | `tests/unit/test_security.py` | ✅ existant |
| AI-AUTH-04 | Mauvais secret rejeté | unitaire | `tests/unit/test_security.py` | ✅ existant |
| AI-AUTH-05 | `get_current_user` exige `sub` | unitaire | `tests/unit/test_security.py` | ✅ existant |
| AI-AUTH-06 | `get_current_tenant_id` : extraction et formats invalides | unitaire | `tests/unit/test_security.py` | ✅ existant |

### Santé, statut et chat

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-HEALTH-01 | `/livez` | intégration | `tests/integration/test_health_api.py` | ✅ existant |
| AI-HEALTH-02 | `/readyz` OK | intégration | `tests/integration/test_health_api.py` | ✅ existant |
| AI-HEALTH-03 | `/readyz` 503 si base HS | intégration | `tests/integration/test_health_api.py` | ✅ existant |
| AI-HEALTH-04 | `/status` tout up | intégration | `tests/integration/test_health_api.py` | ✅ existant |
| AI-HEALTH-05 | `/status` dégradé si Redis HS (200) | intégration | `tests/integration/test_health_api.py` | ✅ existant |
| AI-HEALTH-06 | `/status` dégradé si workers en difficulté | intégration | `tests/integration/test_health_api.py` | ✅ existant |
| AI-HEALTH-07 | `/status` 503 si base HS | intégration | `tests/integration/test_health_api.py` | ✅ existant |
| AI-HEALTH-08 | `/workers/status` liste les files du contrat | intégration | `tests/integration/test_health_api.py` | ✅ existant |
| AI-HEALTH-09 | `/chat/generate` exige l'auth | intégration | `tests/integration/test_health_api.py` | ✅ existant |
| AI-HEALTH-10 | `/chat/generate` répond et valide le prompt | intégration | `tests/integration/test_health_api.py` | ✅ existant |

### Contrat de files Redis / BullMQ

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-QUEUE-01 | `workers.yaml` conforme au contrat documenté | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |
| AI-QUEUE-02 | Job `update_user_identity` | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |
| AI-QUEUE-03 | Job `update_project_identity` | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |
| AI-QUEUE-04 | Job d'identité rejoué : idempotent | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |
| AI-QUEUE-05 | `project_stats_updated` conserve les métadonnées d'identité | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |
| AI-QUEUE-06 | `user_interaction` crée puis déplace le vecteur d'intérêt | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |
| AI-QUEUE-07 | Likes concurrents tous comptés | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |
| AI-QUEUE-08 | Job inconnu : échec sans tuer le worker | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |
| AI-QUEUE-09 | Job malformé ne bloque pas les suivants | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |
| AI-QUEUE-10 | Interaction arrivée avant les identités : appliquée ensuite | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |
| AI-QUEUE-11 | Bout en bout : job puis recommandation HTTP | intégration | `tests/integration/test_queue_contract.py` | ✅ existant |

### Handlers de worker (intégration)

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-WORK-01 | Identité utilisateur persistée | intégration | `tests/integration/test_worker_handlers.py` | ✅ existant |
| AI-WORK-02 | Identité projet persistée | intégration | `tests/integration/test_worker_handlers.py` | ✅ existant |
| AI-WORK-03 | Payload utilisateur vide | intégration | `tests/integration/test_worker_handlers.py` | ✅ existant |
| AI-WORK-04 | Payload projet vide | intégration | `tests/integration/test_worker_handlers.py` | ✅ existant |
| AI-WORK-05 | Plusieurs utilisateurs, même tenant | intégration | `tests/integration/test_worker_handlers.py` | ✅ existant |

### Handlers de worker (unitaire)

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-WORK-06 | Identité utilisateur : succès | unitaire | `tests/unit/test_handlers.py` | ✅ existant |
| AI-WORK-07 | Identité utilisateur : payload vide | unitaire | `tests/unit/test_handlers.py` | ✅ existant |
| AI-WORK-08 | Identité projet : succès | unitaire | `tests/unit/test_handlers.py` | ✅ existant |
| AI-WORK-09 | Identité projet : payload vide | unitaire | `tests/unit/test_handlers.py` | ✅ existant |
| AI-WORK-10 | UUID passés en chaînes (utilisateur) | unitaire | `tests/unit/test_handlers.py` | ✅ existant |
| AI-WORK-11 | UUID passés en chaînes (projet) | unitaire | `tests/unit/test_handlers.py` | ✅ existant |
| AI-WORK-12 | Repositories créés avec le bon tenant | unitaire | `tests/unit/test_handlers.py` | ✅ existant |

### Dispatcher

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-WORK-13 | Initialisation | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |
| AI-WORK-14 | Job valide | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |
| AI-WORK-15 | Job inconnu | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |
| AI-WORK-16 | Erreur de handler | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |
| AI-WORK-17 | Job d'identité projet | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |
| AI-WORK-18 | Registre des handlers attendu | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |
| AI-WORK-19 | Gestion de session | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |
| AI-WORK-20 | Données de job vides | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |
| AI-WORK-21 | Retry en processus puis succès | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |
| AI-WORK-22 | Échec après le maximum de tentatives | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |
| AI-WORK-23 | Pas de retry par défaut | unitaire | `tests/unit/test_dispatcher.py` | ✅ existant |

### Factory de workers

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-WORK-24 | Initialisation | unitaire | `tests/unit/test_worker_factory.py` | ✅ existant |
| AI-WORK-25 | Création des workers | unitaire | `tests/unit/test_worker_factory.py` | ✅ existant |
| AI-WORK-26 | Noms des workers | unitaire | `tests/unit/test_worker_factory.py` | ✅ existant |
| AI-WORK-27 | Noms avec liste vide | unitaire | `tests/unit/test_worker_factory.py` | ✅ existant |
| AI-WORK-28 | Worker unique | unitaire | `tests/unit/test_worker_factory.py` | ✅ existant |
| AI-WORK-29 | Configuration de retry | unitaire | `tests/unit/test_worker_factory.py` | ✅ existant |

### Moniteur de workers

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-WORK-30 | Initialisation | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-31 | Stats d'une file | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-32 | Erreur de stats gérée | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-33 | File fermée même en erreur | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-34 | Stats de toutes les files | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-35 | Stats mixtes (une en erreur) | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-36 | Workers sains | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-37 | Une file malsaine | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-38 | Aucune file | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-39 | Beaucoup d'attente, peu d'actifs | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-40 | Seuil exact | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-41 | Seuil dépassé avec actifs | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |
| AI-WORK-42 | File vide | unitaire | `tests/unit/test_worker_monitor.py` | ✅ existant |

### Bootstrap du worker (`worker/main.py`)

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-WORK-43 | Démarre les workers puis les ferme proprement sur SIGTERM (mocks) | unitaire | `tests/unit/test_worker_main.py` | 🆕 ajouté T10 |
| AI-WORK-44 | Échec immédiat si la config des workers est absente | unitaire | `tests/unit/test_worker_main.py` | 🆕 ajouté T10 |

### Service d'embeddings

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-EMB-01 | Identité utilisateur (provider mocké) | unitaire | `tests/unit/test_embedding_service.py` | ✅ existant |
| AI-EMB-02 | Identité projet | unitaire | `tests/unit/test_embedding_service.py` | ✅ existant |
| AI-EMB-03 | Contenu inchangé : le provider n'est pas rappelé | unitaire | `tests/unit/test_embedding_service.py` | ✅ existant |
| AI-EMB-04 | Extraction de métadonnées échouée : retentée | unitaire | `tests/unit/test_embedding_service.py` | ✅ existant |
| AI-EMB-05 | Interaction utilisateur met à jour le vecteur d'intérêt | unitaire | `tests/unit/test_embedding_service.py` | ✅ existant |

### Batcher d'embeddings

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-EMB-06 | Cache LRU évince le plus ancien | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |
| AI-EMB-07 | Requêtes concurrentes : un appel, dédoublonnage | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |
| AI-EMB-08 | Cache hit sans appel | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |
| AI-EMB-09 | Taille max de lot : flush immédiat | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |
| AI-EMB-10 | Erreur propagée et non mise en cache | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |
| AI-EMB-11 | Le provider groupe en lots et garde l'ordre | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |
| AI-EMB-12 | Fenêtre : flush d'un lot partiel | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |
| AI-EMB-13 | Namespaces isolent les clés | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |
| AI-EMB-14 | Mauvais nombre de résultats : tous les appelants échouent | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |
| AI-EMB-15 | Appelant annulé n'impacte pas les autres | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |
| AI-EMB-16 | Un `get` rafraîchit la récence LRU | unitaire | `tests/unit/test_embedding_batcher.py` | ✅ existant |

### Provider OpenAI (client simulé)

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-EMB-17 | Texte vide refusé | unitaire | `tests/unit/test_openai_provider.py` | ✅ existant |
| AI-EMB-18 | Embedding mis en cache par contenu | unitaire | `tests/unit/test_openai_provider.py` | ✅ existant |
| AI-EMB-19 | Erreur fournisseur encapsulée | unitaire | `tests/unit/test_openai_provider.py` | ✅ existant |
| AI-EMB-20 | Embeddings en un appel, ordre conservé | unitaire | `tests/unit/test_openai_provider.py` | ✅ existant |
| AI-EMB-21 | Métadonnées JSON, température 0, cache | unitaire | `tests/unit/test_openai_provider.py` | ✅ existant |
| AI-EMB-22 | Réponse invalide : repli, pas de cache | unitaire | `tests/unit/test_openai_provider.py` | ✅ existant |
| AI-EMB-23 | Erreur API ou texte vide : repli | unitaire | `tests/unit/test_openai_provider.py` | ✅ existant |

### Traitement du texte

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-NLP-01 | Nettoyage HTML | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |
| AI-NLP-02 | Nettoyage vide | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |
| AI-NLP-03 | Lemmatisation, stop words, ponctuation | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |
| AI-NLP-04 | Minuscules et HTML ignoré | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |
| AI-NLP-05 | Normalisation vide | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |
| AI-NLP-06 | Normalisation idempotente | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |
| AI-NLP-07 | Gabarits de schéma, champs vides ignorés | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |
| AI-NLP-08 | Ordre du schéma conservé | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |
| AI-NLP-09 | Payload vide | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |
| AI-NLP-10 | Version async identique à la sync | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |
| AI-NLP-11 | Initialisation requise | unitaire | `tests/unit/test_nlp_processor.py` | ✅ existant |

### Maths vectorielles et hash

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-VEC-01 | EMA : moyenne pondérée normalisée | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-02 | EMA : poids 0 et 1 | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-03 | EMA : apply plus fort que like | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-04 | EMA converge vers la cible | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-05 | EMA : magnitude nulle | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-06 | EMA : poids valides | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-07 | Combinaison 80/20 | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-08 | Combinaison nulle | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-09 | Hash stable SHA-256 | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-10 | Hash ignore champs hors schéma et ordre des clés | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-11 | Hash sensible au contenu, modèle, version | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-12 | Hash champ manquant vs vide | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |
| AI-VEC-13 | Expression de score trending | unitaire | `tests/unit/test_vector_math.py` | ✅ existant |

### Charge (Locust, `load/locustfile.py`)

| ID | Scénario | Type | Fichier | Statut |
| --- | --- | --- | --- | --- |
| AI-LOAD-01 | Reco de projets pour un utilisateur (poids 55) | charge | `load/locustfile.py` | ✅ existant |
| AI-LOAD-02 | Reco filtrée par thème (10) | charge | `load/locustfile.py` | ✅ existant |
| AI-LOAD-03 | Trending (12) | charge | `load/locustfile.py` | ✅ existant |
| AI-LOAD-04 | Utilisateurs pour un projet (8) | charge | `load/locustfile.py` | ✅ existant |
| AI-LOAD-05 | Sonde `/livez` (2) | charge | `load/locustfile.py` | ✅ existant |
| AI-LOAD-06 | Like / apply via file BullMQ (6) | charge | `load/locustfile.py` | ✅ existant |
| AI-LOAD-07 | Mise à jour de bio (2) | charge | `load/locustfile.py` | ✅ existant |
| AI-LOAD-08 | Mise à jour de projet (1) | charge | `load/locustfile.py` | ✅ existant |

## Bugs trouvés (🐞)

Aucun bug dans `src/` n'a été mis en évidence par les nouveaux tests (jeton `alg=none`, jeton sans
`sub`/`tenantId`, isolation tenant : tous conformes).

## Non couvert / à faire

- `src/worker/cli.py` (point d'entrée `asyncio.run`, 0 %).
- `src/infrastructure/llm_provider.py` (interface abstraite, 67 %).
- `src/services/matchmaking_service.py` (~80 %) : branches de repli (trending, filtres) partiellement testées via l'API seulement.
- `src/server.py`, `api/v1/health.py`, `api/v1/matchmaking.py` : quelques branches d'erreur.
- Test e2e inter-dépôts : hors périmètre (vit dans `highfive-infra`).
- Les scénarios de charge ne sont pas exécutés en CI.
