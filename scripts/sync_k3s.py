#!/usr/bin/env python3
"""Synchronise live k3s state into NetBox through the netbox-k3s REST API.

Reads namespaces, pods and services and upserts them into NetBox. Everything is
scoped under a single K3sCluster (``--cluster``), created on first run.

The Kubernetes data is fetched either:
  * **in-cluster** (automatic when running as a Pod) — via the Kubernetes API
    using the mounted ServiceAccount token; or
  * **via kubectl** (fallback) — when running on a host that has kubectl
    configured (e.g. with a systemd timer).

Only the Python standard library is required (no `requests`, no `kubectl` when
running in-cluster).

Configuration (CLI flag or environment variable):
    NETBOX_URL    e.g. http://netbox:8080   (in-cluster) or http://IP-SERVER:8080
    NETBOX_TOKEN  a NetBox API token with write access to the plugin
    K3S_CLUSTER   logical cluster name to attach everything to
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

API_PREFIX = "/api/plugins/k3s/"
SA_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"


# ---------------------------------------------------------------------------
# Kubernetes side
# ---------------------------------------------------------------------------
def _in_cluster() -> bool:
    return os.path.exists(os.path.join(SA_DIR, "token"))


def _k8s_api_get(resource: str) -> dict:
    """Fetch a core/v1 collection from the in-cluster Kubernetes API."""
    host = os.environ.get("KUBERNETES_SERVICE_HOST", "kubernetes.default.svc")
    port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
    with open(os.path.join(SA_DIR, "token"), encoding="utf-8") as fh:
        token = fh.read().strip()
    ctx = ssl.create_default_context(cafile=os.path.join(SA_DIR, "ca.crt"))
    url = f"https://{host}:{port}/api/v1/{resource}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.load(resp)


def _kubectl_get(resource: str) -> dict:
    """Fetch a collection by shelling out to kubectl (host fallback)."""
    args = ["kubectl", "get", resource, "-o", "json"]
    if resource in ("pods", "services"):
        args.insert(3, "-A")
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed:\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)


def kube_get(resource: str) -> dict:
    """Return the {'items': [...]} collection for namespaces/pods/services."""
    if _in_cluster():
        return _k8s_api_get(resource)
    return _kubectl_get(resource)


# ---------------------------------------------------------------------------
# NetBox side (stdlib HTTP client)
# ---------------------------------------------------------------------------
class NetBox:
    def __init__(self, url: str, token: str, verify_tls: bool = True):
        self.base = url.rstrip("/") + "/"
        self.token = token
        self.ctx = ssl.create_default_context()
        if not verify_tls:
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE

    def _request(self, method: str, path: str, data: dict | None = None) -> dict:
        url = urllib.parse.urljoin(self.base, path.lstrip("/"))
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Token {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, context=self.ctx, timeout=30) as resp:
            return json.load(resp)

    def get(self, path: str, params: dict | None = None) -> dict:
        if params:
            path = f"{path}?{urllib.parse.urlencode(params)}"
        return self._request("GET", path)

    def delete(self, endpoint: str, obj_id: int) -> None:
        url = urllib.parse.urljoin(
            self.base, (API_PREFIX + endpoint).lstrip("/") + f"{obj_id}/"
        )
        req = urllib.request.Request(
            url, method="DELETE",
            headers={"Authorization": f"Token {self.token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, context=self.ctx, timeout=30):
            pass  # 204 No Content

    def list_all(self, endpoint: str, params: dict | None = None) -> list[dict]:
        """Return every object of an endpoint, following pagination."""
        results: list[dict] = []
        page_params = {**(params or {}), "limit": 250, "offset": 0}
        while True:
            page = self.get(API_PREFIX + endpoint, params=page_params)
            results.extend(page.get("results", []))
            if not page.get("next"):
                return results
            page_params["offset"] += page_params["limit"]

    def upsert(self, endpoint: str, match: dict, data: dict) -> dict:
        """Idempotent create-or-update.

        Args:
            endpoint: API endpoint, e.g. ``"pods/"``.
            match:    Filter params to find an existing object. FKs use the
                      ``<field>_id`` form (e.g. ``namespace_id``).
            data:     Full request body for create/update. FKs use the plain
                      field name + PK (e.g. ``namespace``).
        """
        existing = self.get(API_PREFIX + endpoint, params={**match, "limit": 1})
        results = existing.get("results", [])
        if results:
            obj_id = results[0]["id"]
            return self._request("PATCH", f"{API_PREFIX}{endpoint}{obj_id}/", data)
        return self._request("POST", API_PREFIX + endpoint, data)


# ---------------------------------------------------------------------------
# Sync logic
# ---------------------------------------------------------------------------
def sync(nb: NetBox, cluster_name: str) -> None:
    # 1. Ensure the cluster exists; grab version + node count from the nodes.
    nodes = kube_get("nodes").get("items", [])
    version = ""
    if nodes:
        version = nodes[0].get("status", {}).get("nodeInfo", {}).get("kubeletVersion", "")
    cluster = nb.upsert(
        "clusters/",
        match={"name": cluster_name},
        data={
            "name": cluster_name,
            "status": "active",
            "version": version[:50],
            "node_count": len(nodes),
        },
    )
    cluster_id = cluster["id"]
    print(f"Cluster '{cluster_name}' -> id {cluster_id} ({version}, {len(nodes)} nodes)")

    # 2. Namespaces. Map ns name -> NetBox namespace id.
    ns_ids: dict[str, int] = {}
    for item in kube_get("namespaces").get("items", []):
        name = item["metadata"]["name"]
        obj = nb.upsert(
            "namespaces/",
            match={"name": name, "cluster_id": cluster_id},
            data={"name": name, "cluster": cluster_id},
        )
        ns_ids[name] = obj["id"]
    print(f"Synced {len(ns_ids)} namespaces")

    # 3. Pods.
    seen_pod_ids: set[int] = set()
    for item in kube_get("pods").get("items", []):
        meta, spec, status = item["metadata"], item.get("spec", {}), item.get("status", {})
        ns = meta["namespace"]
        if ns not in ns_ids:
            continue
        containers = spec.get("containers", [])
        image = containers[0]["image"] if containers else ""
        restarts = sum(
            cs.get("restartCount", 0) for cs in status.get("containerStatuses", [])
        )
        obj = nb.upsert(
            "pods/",
            match={"name": meta["name"], "namespace_id": ns_ids[ns]},
            data={
                "name": meta["name"],
                "namespace": ns_ids[ns],
                "image": image[:512],
                "status": status.get("phase", "Unknown"),
                "node": spec.get("nodeName", "") or "",
                "ip_address": status.get("podIP") or None,
                "restarts": restarts,
                "container_count": len(containers),
                "started": status.get("startTime") or None,
                "labels": meta.get("labels") or {},
            },
        )
        seen_pod_ids.add(obj["id"])
    print(f"Synced {len(seen_pod_ids)} pods")

    # 4. Services.
    seen_svc_ids: set[int] = set()
    for item in kube_get("services").get("items", []):
        meta, spec = item["metadata"], item.get("spec", {})
        ns = meta["namespace"]
        if ns not in ns_ids:
            continue
        ports = ", ".join(
            f"{p.get('port')}:{p.get('targetPort', '')}/{p.get('protocol', 'TCP')}"
            for p in spec.get("ports", [])
        )
        cluster_ip = spec.get("clusterIP")
        if cluster_ip in ("None", ""):
            cluster_ip = None
        # External address: LoadBalancer ingress first, then spec.externalIPs.
        lb = item.get("status", {}).get("loadBalancer", {}).get("ingress", [])
        external_ip = ""
        if lb:
            external_ip = lb[0].get("ip") or lb[0].get("hostname") or ""
        elif spec.get("externalIPs"):
            external_ip = spec["externalIPs"][0]
        obj = nb.upsert(
            "services/",
            match={"name": meta["name"], "namespace_id": ns_ids[ns]},
            data={
                "name": meta["name"],
                "namespace": ns_ids[ns],
                "type": spec.get("type", "ClusterIP"),
                "cluster_ip": cluster_ip,
                "external_ip": external_ip[:253],
                "ports": ports[:255],
                "selector": spec.get("selector") or {},
            },
        )
        seen_svc_ids.add(obj["id"])
    print(f"Synced {len(seen_svc_ids)} services")

    # 5. Prune: remove NetBox objects (scoped to this cluster) that no longer
    # exist in the live cluster — e.g. completed Job pods with unique names.
    pruned = {"pods": 0, "services": 0, "namespaces": 0}
    for obj in nb.list_all("pods/", params={"cluster_id": cluster_id, "brief": "true"}):
        if obj["id"] not in seen_pod_ids:
            nb.delete("pods/", obj["id"])
            pruned["pods"] += 1
    for obj in nb.list_all("services/", params={"cluster_id": cluster_id, "brief": "true"}):
        if obj["id"] not in seen_svc_ids:
            nb.delete("services/", obj["id"])
            pruned["services"] += 1
    live_ns_ids = set(ns_ids.values())
    for obj in nb.list_all("namespaces/", params={"cluster_id": cluster_id, "brief": "true"}):
        if obj["id"] not in live_ns_ids:
            nb.delete("namespaces/", obj["id"])  # cascade deletes its pods/services
            pruned["namespaces"] += 1
    print(
        f"Pruned {pruned['pods']} pods, {pruned['services']} services, "
        f"{pruned['namespaces']} namespaces"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync k3s state into NetBox")
    parser.add_argument("--url", default=os.environ.get("NETBOX_URL"))
    parser.add_argument("--token", default=os.environ.get("NETBOX_TOKEN"))
    parser.add_argument("--cluster", default=os.environ.get("K3S_CLUSTER"))
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification")
    args = parser.parse_args()

    missing = [
        n for n, v in (("URL", args.url), ("TOKEN", args.token), ("CLUSTER", args.cluster))
        if not v
    ]
    if missing:
        print(f"Missing required value(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    nb = NetBox(args.url, args.token, verify_tls=not args.insecure)
    try:
        sync(nb, args.cluster)
    except (RuntimeError, OSError, urllib.error.URLError) as exc:
        print(f"Sync failed: {exc}", file=sys.stderr)
        return 1
    print("Sync complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
