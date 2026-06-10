# netbox-k3s

Plugin NetBox qui ajoute une section **Kubernetes** dédiée dans le menu de
navigation, totalement séparée des VMs et des autres objets NetBox. Il permet
d'inventorier un ou plusieurs clusters k3s/Kubernetes (clusters, namespaces,
pods, services) et de garder cet inventaire à jour automatiquement grâce à un
script de synchronisation fourni.

## Fonctionnalités

- Menu de navigation « Kubernetes » avec quatre sections : Clusters,
  Namespaces, Pods, Services.
- Modèles complets : statuts colorés, tags, champs personnalisés, journal de
  modifications (hérités de `NetBoxModel`).
- Pages de détail enrichies : version et nombre de nœuds du cluster, redémarrages
  et labels des pods, IP externe et sélecteur des services.
- API REST complète sous `/api/plugins/k3s/` (CRUD, filtres, recherche).
- Script de synchronisation : lit l'état réel du cluster et le reflète dans
  NetBox (création, mise à jour, suppression des objets disparus).
- Support multi-clusters : chaque cluster synchronise vers la même instance
  NetBox sous son propre nom.

## Modèles

| Objet          | Description                                                  |
|----------------|--------------------------------------------------------------|
| `K3sCluster`   | Un cluster, liable à un objet Cluster NetBox natif (optionnel) |
| `K3sNamespace` | Un namespace, rattaché à un `K3sCluster`                     |
| `K3sPod`       | Un pod (image, statut, nœud, IP, redémarrages, labels...)    |
| `K3sService`   | Un service (type, ClusterIP, IP externe, ports, sélecteur)   |

## Compatibilité

| netbox-k3s | NetBox      |
|------------|-------------|
| 0.1.x      | 4.2 – 4.6.x |

Testé contre NetBox 4.6 (image `netboxcommunity/netbox`, Python 3.14).

---

## Installation

### Option A — montage du code + PYTHONPATH (sans pip, recommandé avec l'image officielle)

L'image officielle NetBox récente ne contient pas `pip` dans son venv. Le plugin
étant du pur Python, il suffit de rendre le dossier importable :

1. Copier le dossier `netbox_k3s/` sur le serveur, par exemple dans
   `/opt/netbox-plugins/` (le dossier doit contenir `netbox_k3s/__init__.py`).
2. Monter ce dossier dans le conteneur NetBox et définir la variable
   d'environnement `PYTHONPATH` vers le point de montage.
3. Activer le plugin dans la configuration.

Un manifeste Kubernetes complet et commenté est fourni dans
[`deploy/k3s/netbox.yaml`](deploy/k3s/netbox.yaml) (NetBox + PostgreSQL + Redis
+ worker, plugin monté en hostPath). Voir le guide
[`deploy/k3s/README.md`](deploy/k3s/README.md).

### Option B — installation pip classique

Si votre environnement NetBox dispose de pip (installation source ou image
personnalisée) :

```bash
pip install /chemin/vers/le/depot
```

### Activer le plugin

Dans `configuration.py` (ou un fichier de configuration additionnel) :

```python
PLUGINS = ["netbox_k3s"]

PLUGINS_CONFIG = {
    "netbox_k3s": {
        # True (défaut) : menu « Kubernetes » de premier niveau.
        # False : entrées regroupées sous le menu générique « Plugins ».
        "top_level_menu": True,
    },
}
```

### Appliquer les migrations

```bash
python manage.py migrate netbox_k3s
```

Avec l'image officielle, les migrations sont appliquées automatiquement au
démarrage du conteneur.

### Vérifier

- Une section « Kubernetes » apparaît dans le menu de gauche.
- L'API répond sur `/api/plugins/k3s/clusters/` (authentification requise).

---

## Synchronisation automatique

Le script [`scripts/sync_k3s.py`](scripts/sync_k3s.py) lit l'état du cluster et
le pousse dans NetBox via l'API du plugin. Il fonctionne en miroir : les objets
sont créés ou mis à jour, et ceux qui n'existent plus dans le cluster sont
supprimés de NetBox. Il est idempotent : on peut le relancer autant de fois que
nécessaire.

Le script n'utilise que la bibliothèque standard Python. Il lit le cluster de
deux façons, détectées automatiquement :

- **in-cluster** : exécuté dans un pod, il interroge l'API Kubernetes via le
  ServiceAccount monté ;
- **kubectl** : exécuté sur une machine disposant d'un kubeconfig.

### Variables de configuration

| Variable       | Rôle                                              | Exemple                  |
|----------------|---------------------------------------------------|--------------------------|
| `NETBOX_URL`   | URL de l'instance NetBox                          | `http://IP-SERVER:8080`  |
| `NETBOX_TOKEN` | Token d'API NetBox avec droits d'écriture         | `nbt_xxxx.yyyy`          |
| `K3S_CLUSTER`  | Nom logique du cluster dans NetBox                | `mon-cluster`            |

### Méthode recommandée : CronJob Kubernetes

Un CronJob qui tourne dans le cluster toutes les 5 minutes, avec un
ServiceAccount en lecture seule (namespaces, pods, services, nodes). Aucune
dépendance à installer. Deux manifestes sont fournis :

- [`deploy/k3s/sync-cronjob.yaml`](deploy/k3s/sync-cronjob.yaml) — le cluster
  qui héberge NetBox se synchronise lui-même (cible `http://netbox:8080` en
  interne) ;
- [`deploy/k3s/sync-cronjob-remote.yaml`](deploy/k3s/sync-cronjob-remote.yaml) —
  un cluster distant pousse son inventaire vers le NetBox d'un autre serveur
  (cible `http://IP-SERVER:PORT`).

Guide pas à pas : [`deploy/k3s/SYNC.md`](deploy/k3s/SYNC.md).

### Alternative : timer systemd

Pour exécuter la synchronisation depuis un hôte avec kubectl, des unités
systemd d'exemple sont fournies dans [`scripts/`](scripts/README.md).

---

## API REST

Tous les objets sont exposés sous `/api/plugins/k3s/` :

```
GET/POST            /api/plugins/k3s/clusters/
GET/PATCH/DELETE    /api/plugins/k3s/clusters/<id>/
GET/POST            /api/plugins/k3s/namespaces/
GET/POST            /api/plugins/k3s/pods/
GET/POST            /api/plugins/k3s/services/
```

Filtres usuels : `?name=`, `?cluster_id=`, `?namespace_id=`, `?status=`,
recherche plein texte avec `?q=`.

Authentification par token :

```bash
curl -H "Authorization: Token <votre-token>" http://IP-SERVER:8080/api/plugins/k3s/clusters/
```

---

## Tests

Le dépôt contient deux suites de tests :

- **Tests du plugin** (`netbox_k3s/tests/`) : à exécuter dans un environnement
  NetBox (`python manage.py test netbox_k3s`). Un harnais Docker complet
  (NetBox + PostgreSQL + Redis) est fourni dans [`test/`](test/README.md).
- **Tests du script de sync** (`scripts/test_sync.py`) : sans dépendance,
  `python scripts/test_sync.py`.

---

## Structure du dépôt

```
netbox_k3s/        Le plugin NetBox (modèles, vues, API, templates, migrations)
scripts/           Script de synchronisation + unités systemd d'exemple
deploy/k3s/        Manifestes Kubernetes (NetBox complet + CronJobs de sync)
test/              Harnais de test Docker (docker compose)
docs/              Notes d'installation complémentaires
```

## Licence

Apache-2.0
