# Synchronisation cluster → NetBox

`sync_k3s.py` lit l'état du cluster et le reflète dans NetBox via l'API REST du
plugin. Le script est idempotent et fonctionne en miroir : les objets sont
créés ou mis à jour, et ceux qui ont disparu du cluster sont supprimés de
NetBox.

> Méthode recommandée sur Kubernetes : le **CronJob** fourni dans
> [`../deploy/k3s/SYNC.md`](../deploy/k3s/SYNC.md), sans dépendance ni
> kubeconfig. La méthode systemd ci-dessous est l'alternative pour exécuter la
> synchronisation depuis un hôte.

## Prérequis

- Python 3 (bibliothèque standard uniquement) ;
- `kubectl` configuré pour joindre le cluster (variable `KUBECONFIG` si
  besoin), **ou** exécution dans un pod (le ServiceAccount est détecté
  automatiquement) ;
- un token d'API NetBox avec droits d'écriture sur le plugin.

## Exécution manuelle

```bash
NETBOX_URL=http://IP-SERVER:8080 \
NETBOX_TOKEN=votre_token_api \
K3S_CLUSTER=mon-cluster \
KUBECONFIG=/etc/rancher/k3s/k3s.yaml \
    python3 sync_k3s.py
```

Ajouter `--insecure` si NetBox est servi avec un certificat auto-signé.

## Planification avec systemd

1. Installer le script et un fichier d'environnement protégé contenant le
   token :

   ```bash
   sudo mkdir -p /opt/netbox-k3s
   sudo cp sync_k3s.py /opt/netbox-k3s/
   echo 'NETBOX_TOKEN=votre_token_api' | sudo tee /etc/netbox-k3s-sync.env
   sudo chmod 600 /etc/netbox-k3s-sync.env
   ```

2. Adapter `netbox-k3s-sync.service` (URL, nom du cluster, chemins) puis
   installer les unités :

   ```bash
   sudo cp netbox-k3s-sync.service netbox-k3s-sync.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now netbox-k3s-sync.timer
   ```

3. Vérifier :

   ```bash
   systemctl list-timers netbox-k3s-sync.timer
   sudo systemctl start netbox-k3s-sync.service   # exécution immédiate
   journalctl -u netbox-k3s-sync.service -f       # logs
   ```

## Tests

```bash
python3 test_sync.py
```

Aucune dépendance ni accès réseau requis.
