"""Seed some example k3s data so the UI shows content."""
from netbox_k3s.models import K3sCluster, K3sNamespace, K3sPod, K3sService

cluster, _ = K3sCluster.objects.get_or_create(
    name="demo-cluster", defaults={"status": "active", "version": "v1.30.2+k3s1"}
)

ns_default, _ = K3sNamespace.objects.get_or_create(name="default", cluster=cluster)
ns_kube, _ = K3sNamespace.objects.get_or_create(name="kube-system", cluster=cluster)
ns_apps, _ = K3sNamespace.objects.get_or_create(name="apps", cluster=cluster)

pods = [
    ("traefik-abc", ns_kube, "rancher/traefik:2.11", "Running", "demo-node-1", "10.42.0.3"),
    ("coredns-xyz", ns_kube, "rancher/coredns:1.11", "Running", "demo-node-1", "10.42.0.4"),
    ("web-0", ns_apps, "nginx:1.27", "Running", "demo-node-2", "10.42.1.10"),
    ("web-1", ns_apps, "nginx:1.27", "Running", "demo-node-2", "10.42.1.11"),
    ("redis-0", ns_apps, "redis:7-alpine", "Pending", "demo-node-2", None),
]
for name, ns, image, st, node, ip in pods:
    K3sPod.objects.get_or_create(
        name=name, namespace=ns,
        defaults={"image": image, "status": st, "node": node, "ip_address": ip},
    )

services = [
    ("traefik", ns_kube, "LoadBalancer", "10.43.0.10", "80:8000/TCP, 443:8443/TCP"),
    ("kube-dns", ns_kube, "ClusterIP", "10.43.0.10", "53:53/UDP"),
    ("web", ns_apps, "ClusterIP", "10.43.1.50", "80:8080/TCP"),
    ("redis", ns_apps, "ClusterIP", None, "6379:6379/TCP"),
]
for name, ns, typ, cip, ports in services:
    K3sService.objects.get_or_create(
        name=name, namespace=ns,
        defaults={"type": typ, "cluster_ip": cip, "ports": ports},
    )

print(
    f"Seeded: {K3sCluster.objects.count()} cluster, "
    f"{K3sNamespace.objects.count()} namespaces, "
    f"{K3sPod.objects.count()} pods, {K3sService.objects.count()} services"
)
