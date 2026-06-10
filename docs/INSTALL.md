# Installing netbox-k3s in the k3s NetBox pod

The `netboxcommunity/netbox` image supports two ways to add a plugin. Pick one.

---

## Option A — `local_requirements.txt` (simplest, no rebuild)

The container installs anything listed in `/opt/netbox/local_requirements.txt`
on startup. Mount the plugin and reference it:

1. Build a wheel and copy it somewhere the pod can reach (a PVC), or publish to
   a private index. From this repo:

   ```bash
   python -m build           # produces dist/netbox_k3s-0.1.0-py3-none-any.whl
   ```

2. In your `netbox.yaml`, mount the wheel and a `local_requirements.txt` that
   points at it, e.g. via a ConfigMap + PVC. The file just needs:

   ```text
   netbox-k3s
   ```

   (or `/opt/wheels/netbox_k3s-0.1.0-py3-none-any.whl` if installing from a path)

> Note: with the official image, code changes require a pod restart so the
> entrypoint re-runs `pip install` and `migrate`.

---

## Option B — derived image (most robust for production)

```dockerfile
FROM netboxcommunity/netbox:latest

COPY . /opt/netbox-k3s
RUN /opt/netbox/venv/bin/pip install /opt/netbox-k3s
```

Build, push to your registry, and point the k3s Deployment at the new image:

```bash
docker build -t your-registry/netbox-k3s:latest .
docker push your-registry/netbox-k3s:latest
```

In `netbox.yaml`, set the Deployment `image:` to `your-registry/netbox-k3s:latest`.

---

## Enable the plugin (both options)

NetBox reads `PLUGINS` from `configuration.py`. With the community image this is
driven by env / the mounted `configuration.py`. Ensure:

```python
PLUGINS = [
    "netbox_k3s",
]

# Optional per-plugin settings:
PLUGINS_CONFIG = {
    "netbox_k3s": {
        "top_level_menu": True,
    },
}
```

If you manage config via env vars on the community image, the equivalent is to
mount an `extra.py`/`configuration.py` fragment that appends `"netbox_k3s"` to
`PLUGINS`.

## Apply migrations

The community image entrypoint runs `manage.py migrate` automatically on start.
To run it by hand inside the pod:

```bash
kubectl -n netbox exec deploy/netbox -- /opt/netbox/venv/bin/python \
    /opt/netbox/netbox/manage.py migrate netbox_k3s
```

## Verify

- A **Kubernetes** entry appears in the left navigation with Clusters,
  Namespaces, Pods and Services.
- The REST API is live at `/api/plugins/k3s/` (clusters, namespaces, pods,
  services).

## Rollout commands (k3s)

```bash
# after changing the image or config
kubectl -n netbox rollout restart deploy/netbox
kubectl -n netbox rollout status deploy/netbox
```
