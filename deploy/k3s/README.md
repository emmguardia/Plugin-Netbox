# Déployer NetBox + le plugin sur k3s

Le manifeste [`netbox.yaml`](netbox.yaml) déploie une instance NetBox complète
(NetBox + PostgreSQL + Redis + worker RQ) avec le plugin `netbox_k3s` intégré
dès le départ, via un montage hostPath + `PYTHONPATH` (pas besoin de pip ni de
registre d'images).

## Prérequis

- Un cluster k3s (ou k8s) avec une classe de stockage par défaut.
- Le dossier `netbox_k3s/` du dépôt copié sur le nœud, par exemple dans
  `/opt/netbox-plugins/` (adapter le `hostPath` du manifeste si différent).

```bash
# depuis votre machine, copier le plugin sur le serveur
scp -r netbox_k3s USER@IP-SERVER:/opt/netbox-plugins/

# sur le serveur : supprimer les caches et rendre lisible par le conteneur
find /opt/netbox-plugins -name __pycache__ -type d -exec rm -rf {} +
chmod -R a+rX /opt/netbox-plugins
```

## 1. Renseigner les valeurs du manifeste

Éditer `netbox.yaml` et remplacer toutes les valeurs `CHANGE_ME` :

```bash
openssl rand -base64 50    # SECRET_KEY
openssl rand -base64 50    # API_TOKEN_PEPPERS (ne plus changer ensuite)
```

À adapter également :

- `CSRF_TRUSTED_ORIGINS` : votre domaine public (`https://netbox.example.com`) ;
- le mot de passe PostgreSQL (deux occurrences, qui doivent rester identiques) ;
- le `hostPath` du plugin si vous avez choisi un autre dossier ;
- l'image NetBox (épingler une version précise plutôt que `latest` est
  recommandé en production) ;
- le bloc `REMOTE_AUTH_*` si vous utilisez un SSO (reverse proxy d'auth) ;
  supprimez-le sinon.

Important : conservez la version renseignée de ce fichier hors du dépôt git
(les valeurs sont des secrets).

## 2. Déployer

```bash
kubectl apply -f netbox.yaml

# suivre le démarrage (la première fois, les migrations prennent quelques minutes)
kubectl -n netbox get pods -w
kubectl -n netbox logs deploy/netbox -f
```

Le pod `netbox` applique automatiquement les migrations (NetBox + plugin) à
chaque démarrage. Le worker attend la fin des migrations avant de démarrer.

## 3. Vérifier le plugin

```bash
kubectl -n netbox exec deploy/netbox -- /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py showmigrations netbox_k3s
```

Toutes les migrations doivent être cochées. Ouvrir ensuite l'interface : une
section « Kubernetes » apparaît dans le menu de navigation.

## 4. Créer un compte administrateur

Sans SSO :

```bash
kubectl -n netbox exec -it deploy/netbox -- /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py createsuperuser
```

Avec SSO (`REMOTE_AUTH_ENABLED = True`) : le compte est créé automatiquement à
la première connexion, mais sans droits. Pour le promouvoir :

```bash
kubectl -n netbox exec -i deploy/netbox -- /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py shell <<'EOF'
from django.contrib.auth import get_user_model
U = get_user_model()
u, created = U.objects.get_or_create(username="VOTRE_UTILISATEUR")
u.is_superuser = True
u.save()
print("OK", u)
EOF
```

Note : le nom d'utilisateur doit correspondre exactement à celui transmis par
l'en-tête configuré dans `REMOTE_AUTH_HEADER`.

## 5. Mettre en place la synchronisation

Voir [SYNC.md](SYNC.md) pour brancher le CronJob qui remplit l'inventaire
automatiquement toutes les 5 minutes.

## Mettre à jour le plugin

```bash
# recopier les fichiers puis redémarrer (les migrations s'appliquent au boot)
scp -r netbox_k3s USER@IP-SERVER:/opt/netbox-plugins/
kubectl -n netbox rollout restart deploy/netbox deploy/netbox-worker
kubectl -n netbox rollout status deploy/netbox --timeout=300s
```

Le redémarrage prend deux à trois minutes (migrations + sonde de disponibilité) :
c'est normal que `rollout status` patiente.

## Notes

- Le Service `netbox` est exposé en NodePort (`30500` par défaut) ; adaptez ou
  remplacez par votre Ingress habituel.
- Le worker RQ monte le plugin et le `PYTHONPATH` exactement comme le pod web :
  un worker qui charge `PLUGINS` sans pouvoir importer le module ne démarre pas.
- `SECRET_KEY`, mot de passe PostgreSQL et `API_TOKEN_PEPPERS` sont dans une
  ConfigMap pour rester simples à gérer ; pour durcir, déplacez-les dans un
  Secret Kubernetes.
