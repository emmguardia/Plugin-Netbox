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
# Max objects per bulk request (NetBox handles large batches, but keep it sane).
CHUNK = 100

# Fields compared to decide whether an existing object needs an update. FK and
# format-fragile fields (namespace, started) are excluded on purpose.
_POD_FIELDS = ("image", "status", "node", "ip_address", "restarts", "container_count", "labels")
_SVC_FIELDS = ("type", "cluster_ip", "external_ip", "ports", "selector")


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

    def _request(self, method: str, path: str, data=None):
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
        with urllib.request.urlopen(req, context=self.ctx, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None

    def get(self, path: str, params: dict | None = None) -> dict:
        if params:
            path = f"{path}?{urllib.parse.urlencode(params)}"
        return self._request("GET", path)

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

    # --- Bulk operations: one HTTP request per chunk, not per object ---------
    def bulk_create(self, endpoint: str, items: list[dict]) -> list[dict]:
        out: list[dict] = []
        for i in range(0, len(items), CHUNK):
            res = self._request("POST", API_PREFIX + endpoint, items[i:i + CHUNK])
            if isinstance(res, list):
                out.extend(res)
        return out

    def bulk_update(self, endpoint: str, items: list[dict]) -> list[dict]:
        out: list[dict] = []
        for i in range(0, len(items), CHUNK):
            res = self._request("PATCH", API_PREFIX + endpoint, items[i:i + CHUNK])
            if isinstance(res, list):
                out.extend(res)
        return out

    def bulk_delete(self, endpoint: str, ids: list[int]) -> None:
        payload = [{"id": i} for i in ids]
        for i in range(0, len(payload), CHUNK):
            self._request("DELETE", API_PREFIX + endpoint, payload[i:i + CHUNK])

    def upsert(self, endpoint: str, match: dict, data: dict) -> dict:
        """Single-object create-or-update (used for the cluster object)."""
        existing = self.get(API_PREFIX + endpoint, params={**match, "limit": 1})
        results = existing.get("results", [])
        if results:
            obj_id = results[0]["id"]
            return self._request("PATCH", f"{API_PREFIX}{endpoint}{obj_id}/", data)
        return self._request("POST", API_PREFIX + endpoint, data)


def _changed(existing: dict, desired: dict, fields) -> bool:
    """True if any compared field differs between NetBox and the live state."""
    return any(existing.get(f) != desired.get(f) for f in fields)


# ---------------------------------------------------------------------------
# Sync logic
# ---------------------------------------------------------------------------
def _pod_data(item, ns_id):
    meta, spec, status = item["metadata"], item.get("spec", {}), item.get("status", {})
    containers = spec.get("containers", [])
    image = containers[0]["image"] if containers else ""
    restarts = sum(cs.get("restartCount", 0) for cs in status.get("containerStatuses", []))
    return {
        "name": meta["name"],
        "namespace": ns_id,
        "image": image[:512],
        "status": status.get("phase", "Unknown"),
        "node": spec.get("nodeName", "") or "",
        "ip_address": status.get("podIP") or None,
        "restarts": restarts,
        "container_count": len(containers),
        "started": status.get("startTime") or None,
        "labels": meta.get("labels") or {},
    }


def _svc_data(item, ns_id):
    meta, spec = item["metadata"], item.get("spec", {})
    ports = ", ".join(
        f"{p.get('port')}:{p.get('targetPort', '')}/{p.get('protocol', 'TCP')}"
        for p in spec.get("ports", [])
    )
    cluster_ip = spec.get("clusterIP")
    if cluster_ip in ("None", ""):
        cluster_ip = None
    lb = item.get("status", {}).get("loadBalancer", {}).get("ingress", [])
    external_ip = ""
    if lb:
        external_ip = lb[0].get("ip") or lb[0].get("hostname") or ""
    elif spec.get("externalIPs"):
        external_ip = spec["externalIPs"][0]
    return {
        "name": meta["name"],
        "namespace": ns_id,
        "type": spec.get("type", "ClusterIP"),
        "cluster_ip": cluster_ip,
        "external_ip": external_ip[:253],
        "ports": ports[:255],
        "selector": spec.get("selector") or {},
    }


def _reconcile(nb, endpoint, desired, existing_by_key, compare_fields):
    """Bulk create/update/delete to make NetBox match ``desired``.

    desired:          {key: data} for the live objects.
    existing_by_key:  {key: netbox_object} currently in NetBox.
    Returns (created_objects, n_created, n_updated, n_deleted).
    """
    to_create = [data for key, data in desired.items() if key not in existing_by_key]
    to_update = []
    for key, data in desired.items():
        ex = existing_by_key.get(key)
        if ex is not None and _changed(ex, data, compare_fields):
            to_update.append({"id": ex["id"], **data})
    to_delete = [ex["id"] for key, ex in existing_by_key.items() if key not in desired]

    created = nb.bulk_create(endpoint, to_create)
    nb.bulk_update(endpoint, to_update)
    nb.bulk_delete(endpoint, to_delete)
    return created, len(to_create), len(to_update), len(to_delete)


def sync(nb: NetBox, cluster_name: str) -> None:
    # 1. Cluster (single object).
    nodes = kube_get("nodes").get("items", [])
    version = ""
    if nodes:
        version = nodes[0].get("status", {}).get("nodeInfo", {}).get("kubeletVersion", "")
    cluster = nb.upsert(
        "clusters/",
        match={"name": cluster_name},
        data={"name": cluster_name, "status": "active",
              "version": version[:50], "node_count": len(nodes)},
    )
    cluster_id = cluster["id"]
    print(f"Cluster '{cluster_name}' -> id {cluster_id} ({version}, {len(nodes)} nodes)")

    # 2. Namespaces (no mutable fields -> create + prune only, no update).
    existing_ns = {n["name"]: n for n in nb.list_all("namespaces/", {"cluster_id": cluster_id})}
    live_ns_names = [it["metadata"]["name"] for it in kube_get("namespaces").get("items", [])]
    desired_ns = {n: {"name": n, "cluster": cluster_id} for n in live_ns_names}
    # Deleting a stale namespace here cascades to its leftover pods/services.
    created_ns, ns_c, _, ns_d = _reconcile(nb, "namespaces/", desired_ns, existing_ns, ())
    ns_ids = {n: o["id"] for n, o in existing_ns.items() if n in desired_ns}
    for o in created_ns:
        ns_ids[o["name"]] = o["id"]
    print(f"Namespaces: {len(ns_ids)} live (+{ns_c} new, -{ns_d} removed)")

    # 3. Pods. Key = (namespace_id, name).
    desired_pods = {}
    for item in kube_get("pods").get("items", []):
        ns = item["metadata"]["namespace"]
        if ns not in ns_ids:
            continue
        desired_pods[(ns_ids[ns], item["metadata"]["name"])] = _pod_data(item, ns_ids[ns])
    existing_pods = {
        (p["namespace"]["id"], p["name"]): p
        for p in nb.list_all("pods/", {"cluster_id": cluster_id})
    }
    _, pc, pu, pd = _reconcile(nb, "pods/", desired_pods, existing_pods, _POD_FIELDS)
    print(f"Pods: {len(desired_pods)} live (+{pc} new, ~{pu} updated, -{pd} removed)")

    # 4. Services. Key = (namespace_id, name).
    desired_svc = {}
    for item in kube_get("services").get("items", []):
        ns = item["metadata"]["namespace"]
        if ns not in ns_ids:
            continue
        desired_svc[(ns_ids[ns], item["metadata"]["name"])] = _svc_data(item, ns_ids[ns])
    existing_svc = {
        (s["namespace"]["id"], s["name"]): s
        for s in nb.list_all("services/", {"cluster_id": cluster_id})
    }
    _, sc, su, sd = _reconcile(nb, "services/", desired_svc, existing_svc, _SVC_FIELDS)
    print(f"Services: {len(desired_svc)} live (+{sc} new, ~{su} updated, -{sd} removed)")


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
