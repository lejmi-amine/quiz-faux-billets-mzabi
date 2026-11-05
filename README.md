# Test candidats — signes de sécurité des billets

Trois tests (euro, dollar, livre sterling — 5 questions chacun) et un classement en direct,
pour la formation « Détection et identification des faux billets de banque étrangers ».

- `index.html` — le test (mobile d’abord)

## Les questions

19 questions au total : 9 pour l’euro, 5 pour le dollar, 5 pour la livre.
Deux formes de question coexistent :

- **zone à toucher** — un billet s’affiche, le candidat touche l’endroit du signe demandé ;
- **choix d’image** (`type: "pick"`) — plusieurs billets côte à côte, le candidat
  désigne l’authentique. Chaque question déclare `genuine` (le billet authentique),
  `fakes` (le vivier de faux) et `show` (le nombre de vignettes). À chaque affichage,
  le billet authentique est tiré avec un sous-ensemble aléatoire des faux, puis
  l’ordre est mélangé : avec plus de faux que de vignettes, la série change d’une
  tentative à l’autre.

Les trois questions UV et infrarouge utilisent les images officielles de la brochure
*The Europa series of banknotes* de la Banque centrale européenne (© BCE 2019).

### Photos de faux billets à fournir

Les neuf vignettes encore marquées **IMAGE À FOURNIR** attendent les photos de faux billets.
Pour les intégrer : ajouter chaque photo dans `IMGS` (`index.html`) sous une clé propre,
puis remplacer les `"todo"` correspondants dans le tableau `fakes` de la question.
Tant que ces images restent des marques de réservation, la bonne réponse se devine
au premier coup d’œil : ces trois questions ne comptent pas réellement.

> Si le nombre de questions change, mettre à jour `MAX` dans `api/scores.js`
> (`{ eur, usd, gbp }`), sinon les scores valides seront refusés — et remettre
> le classement à zéro, pour ne pas mélanger des scores sur 15, sur 18 et sur 19.
- `api/scores.js` — l’API du classement (fonction Vercel, base Redis via `REDIS_URL`)
- `admin.html` — remise à zéro du classement entre deux sessions

## Vérifier que le classement fonctionne

Ouvrez `https://<votre-site>.vercel.app/api/scores` dans un navigateur :

| Réponse | Signification |
| --- | --- |
| `{"rows":[],"count":0}` | tout fonctionne, aucun score pour l’instant |
| `{"error":"storage_not_configured"}` | `REDIS_URL` absente — base non reliée au projet, ou pas de redéploiement |
| `{"error":"storage_error"}` | base joignable mais la connexion échoue (voir `detail`) |
| `The page could not be found` | le dossier `api` n’est pas dans le dépôt GitHub |

## Mise en ligne (une seule fois, ~10 minutes)

1. **GitHub** — créez un dépôt nommé exactement `quiz-faux-billets-mzabi`,
   puis « uploading an existing file » : déposez tout le contenu de ce dossier
   (y compris le dossier `api`) et validez (*Commit changes*).
2. **Vercel** — *Add New… → Project*, importez le dépôt, gardez les réglages
   par défaut (aucun framework, aucune commande de build) et cliquez *Deploy*.
3. **Base de données du classement** — dans le projet Vercel : onglet *Storage* →
   *Create Database* → une base **Redis** du Marketplace (offre gratuite) →
   *Connect to Project* pour la relier à ce projet. La variable `REDIS_URL` est
   ajoutée automatiquement ; c’est la seule dont l’API a besoin.
4. *(Recommandé)* *Settings → Environment Variables* : ajoutez `ADMIN_KEY` avec un mot
   de passe de votre choix (il sert à remettre le classement à zéro).
5. **Redéployez** (*Deployments → … → Redeploy*) pour que les étapes 3 et 4 soient prises en compte.

## Vérifier l’adresse

Le QR code de la présentation pointe vers **https://quiz-faux-billets-mzabi.vercel.app**.
Vercel donne cette adresse si le projet porte ce nom. Si l’adresse affichée par Vercel
est différente, renommez le projet (*Settings → General → Project Name*) ou faites
regénérer le QR code avec la bonne adresse.

## Pendant la formation

- Les candidats scannent le QR code, saisissent leur nom et font les trois tests.
- Classement sur le projecteur : **https://quiz-faux-billets-mzabi.vercel.app/#classement**
  (se met à jour toutes les 5 secondes).
- Seule la meilleure tentative de chaque candidat (par téléphone) est conservée.
- Remise à zéro : **/admin.html** et la clé `ADMIN_KEY`.

## Limites à connaître

Pas de comptes : un candidat est identifié par son nom et son téléphone. C’est adapté à
une session de formation, pas à un examen certifiant — une personne déterminée pourrait
inscrire un faux score en appelant l’API directement.
