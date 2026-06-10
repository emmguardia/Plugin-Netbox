# Synchronisation automatique cluster → NetBox

Un CronJob Kubernetes lit l'état du cluster (ServiceAccount en lecture seule)
et le pousse dans NetBox toutes les 5 minutes. Le script n'utilise que la
bibliothèque standard Python : aucune dépendance, pas de kubeconfig à gérer.

Deux manifestes selon la topologie :

| Manifeste                  | Cas d'usage                                            | Cible NetBox            |
|----------------------------|--------------------------------------------------------|-------------------------|
| `sync-cronjob.yaml`        | le cluster qui héberge NetBox s'inventorie lui-même    | `http://netbox:8080`    |
| `sync-cronjob-remote.yaml` | un cluster distant pousse vers le NetBox d'un autre serveur | `http://IP-SERVER:30500` |

La synchronisation fonctionne en miroir : objets créés, mis à jour, et
supprimés de NetBox quand ils disparaissent du cluster. Chaque cluster est
rangé sous son propre objet `K3sCluster` (variable `K3S_CLUSTER`).

## 1. Générer un token d'API

Créer un utilisateur de service et son token :

```bash
kubectl -n netbox exec -i deploy/netbox -- /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py shell <<'EOF'
from django.contrib.auth import get_user_model
from users.constants import TOKEN_PREFIX
from users.models import Token
U = get_user_model()
u, _ = U.objects.get_or_create(username="svc-k3s-sync")
u.is_superuser = True
u.save()
Token.objects.filter(user=u).delete()
t = Token.objects.create(user=u)
print("TOKEN=" + TOKEN_PREFIX + t.key + "." + t.token)
EOF
```

Copier la valeur affichée (`nbt_...`).

Remarque : si l'instance est derrière un proxy d'authentification (SSO), ciblez
le NodePort ou le Service interne plutôt que le domaine public, sinon le proxy
interceptera les appels d'API.

## 2. Créer la ConfigMap (script) et le Secret (token)

```bash
# copier le script sur le serveur
scp scripts/sync_k3s.py USER@IP-SERVER:/tmp/sync_k3s.py
```

```bash
# sur le serveur (adapter le namespace : netbox pour le cluster local,
# netbox-sync pour un cluster distant)
kubectl -n netbox create configmap netbox-k3s-sync-script \
    --from-file=sync_k3s.py=/tmp/sync_k3s.py

kubectl -n netbox create secret generic netbox-k3s-sync-token \
    --from-literal=token='nbt_VOTRE_TOKEN'
```

## 3. Appliquer le CronJob

Adapter dans le manifeste : `NETBOX_URL`, `K3S_CLUSTER` (nom logique du
cluster) et éventuellement la planification (`schedule`).

```bash
kubectl apply -f sync-cronjob.yaml      # ou sync-cronjob-remote.yaml
```

## 4. Tester immédiatement

```bash
kubectl -n netbox create job --from=cronjob/netbox-k3s-sync sync-test-1
kubectl -n netbox wait --for=condition=complete job/sync-test-1 --timeout=180s
kubectl -n netbox logs job/sync-test-1
kubectl -n netbox delete job sync-test-1
```

Sortie attendue :

```
Cluster 'mon-cluster' -> id 1 (v1.30.x+k3s1, 1 nodes)
Synced 12 namespaces
Synced 35 pods
Synced 22 services
Pruned 0 pods, 0 services, 0 namespaces
Sync complete.
```

Recharger NetBox : la section Kubernetes est remplie, puis mise à jour toutes
les 5 minutes.

## Piloter le CronJob

```bash
kubectl -n netbox get cronjob netbox-k3s-sync
kubectl -n netbox logs -l job-name --tail=50

# suspendre / réactiver
kubectl -n netbox patch cronjob netbox-k3s-sync -p '{"spec":{"suspend":true}}'
kubectl -n netbox patch cronjob netbox-k3s-sync -p '{"spec":{"suspend":false}}'
```

## Mettre à jour le script

```bash
scp scripts/sync_k3s.py USER@IP-SERVER:/tmp/sync_k3s.py
kubectl -n netbox create configmap netbox-k3s-sync-script \
    --from-file=sync_k3s.py=/tmp/sync_k3s.py \
    --dry-run=client -o yaml | kubectl apply -f -
# la prochaine exécution utilise la nouvelle version
```

## Notes

- Les pods de jobs terminés (`Succeeded`) encore présents dans le cluster
  apparaissent dans NetBox : c'est un miroir fidèle de l'état réel. Ils
  disparaissent quand Kubernetes purge son historique.
- Le RBAC fourni est en lecture seule sur namespaces, pods, services et nodes.
- Le même script fonctionne aussi hors cluster avec kubectl (voir
  `scripts/README.md` pour la variante systemd).
