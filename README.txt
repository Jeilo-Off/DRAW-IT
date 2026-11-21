DRAW IT! - VERSION SERVEUR EN LIGNE

1. Publie le dossier sur un dépôt GitHub.
2. Sur Render, crée un nouveau Blueprint depuis ce dépôt et applique render.yaml.
3. Quand Render a créé le service, copie son domaine (ex: draw-it-server.onrender.com).
4. Dans main.py, remplace REMPLACE-PAR-TON-SERVEUR par ce domaine.
   Exemple : wss://draw-it-server.onrender.com
5. Distribue main.py à tes amis (avec Python et websockets installés) ou recrée ton EXE.

Installation locale : py -m pip install -r requirements.txt
Lancement du client : py main.py

Le serveur en ligne doit rester déployé. L'offre gratuite de l'hébergeur peut
mettre le service en veille après une période d'inactivité.
Le chat écrit est inclus ; le chat vocal n'est pas implémenté.
