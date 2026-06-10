"""End-to-end tests for the netbox-k3s plugin.

Run inside a NetBox checkout/container:

    python manage.py test netbox_k3s --keepdb
"""

from django.contrib.auth import get_user_model
from django.test import TestCase as DjangoTestCase
from django.test import Client
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.constants import TOKEN_PREFIX
from users.models import Token

from netbox_k3s.models import K3sCluster, K3sNamespace, K3sPod, K3sService

User = get_user_model()


def _build_tree():
    cluster = K3sCluster.objects.create(
        name="demo-cluster", status="active", version="v1.30", node_count=1
    )
    ns = K3sNamespace.objects.create(name="default", cluster=cluster)
    pod = K3sPod.objects.create(
        name="web-0", namespace=ns, image="nginx:1.27",
        status="Running", node="node-1", ip_address="10.42.0.5",
        restarts=3, container_count=1, labels={"app": "web"},
    )
    svc = K3sService.objects.create(
        name="web", namespace=ns, type="ClusterIP",
        cluster_ip="10.43.0.10", ports="80:8080/TCP",
        external_ip="192.0.2.10", selector={"app": "web"},
    )
    return cluster, ns, pod, svc


class ModelTest(DjangoTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster, cls.ns, cls.pod, cls.svc = _build_tree()

    def test_str(self):
        self.assertEqual(str(self.cluster), "demo-cluster")
        self.assertEqual(str(self.ns), "demo-cluster/default")
        self.assertEqual(str(self.pod), "web-0")
        self.assertEqual(str(self.svc), "web")

    def test_get_absolute_url(self):
        for obj in (self.cluster, self.ns, self.pod, self.svc):
            self.assertTrue(obj.get_absolute_url().startswith("/plugins/k3s/"))

    def test_relationships(self):
        self.assertEqual(self.cluster.namespaces.count(), 1)
        self.assertEqual(self.ns.pods.count(), 1)
        self.assertEqual(self.ns.services.count(), 1)

    def test_color_helpers(self):
        self.assertEqual(self.cluster.get_status_color(), "green")
        self.assertEqual(self.pod.get_status_color(), "green")
        self.assertEqual(self.svc.get_type_color(), "blue")

    def test_unique_constraints(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                K3sNamespace.objects.create(name="default", cluster=self.cluster)


class UrlReverseTest(DjangoTestCase):
    """Every URL name referenced by navigation/templates must reverse."""

    def test_list_and_add_urls(self):
        for model in ("k3scluster", "k3snamespace", "k3spod", "k3sservice"):
            reverse(f"plugins:netbox_k3s:{model}_list")
            reverse(f"plugins:netbox_k3s:{model}_add")

    def test_detail_urls(self):
        cluster, ns, pod, svc = _build_tree()
        for obj, name in (
            (cluster, "k3scluster"), (ns, "k3snamespace"),
            (pod, "k3spod"), (svc, "k3sservice"),
        ):
            reverse(f"plugins:netbox_k3s:{name}", args=[obj.pk])
            reverse(f"plugins:netbox_k3s:{name}_edit", args=[obj.pk])
            reverse(f"plugins:netbox_k3s:{name}_delete", args=[obj.pk])


class UIViewTest(DjangoTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster, cls.ns, cls.pod, cls.svc = _build_tree()

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", password="admin", email="a@b.c"
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_list_views(self):
        for model in ("k3scluster", "k3snamespace", "k3spod", "k3sservice"):
            url = reverse(f"plugins:netbox_k3s:{model}_list")
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"{model}_list -> {resp.status_code}")

    def test_detail_views_render_templates(self):
        """Exercises the custom detail templates incl. nested tables."""
        cases = (
            ("k3scluster", self.cluster.pk),
            ("k3snamespace", self.ns.pk),
            ("k3spod", self.pod.pk),
            ("k3sservice", self.svc.pk),
        )
        for name, pk in cases:
            url = reverse(f"plugins:netbox_k3s:{name}", args=[pk])
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"{name} detail -> {resp.status_code}")

    def test_add_views(self):
        for model in ("k3scluster", "k3snamespace", "k3spod", "k3sservice"):
            url = reverse(f"plugins:netbox_k3s:{model}_add")
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"{model}_add -> {resp.status_code}")


class APITest(DjangoTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster, cls.ns, cls.pod, cls.svc = _build_tree()

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="apiadmin", password="x", email="api@b.c"
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        # NetBox 4.6+ uses v2 tokens (Bearer scheme) when API_TOKEN_PEPPERS is set.
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {TOKEN_PREFIX}{self.token.key}.{self.token.token}"
        )

    def test_list_endpoints(self):
        for ep in ("clusters", "namespaces", "pods", "services"):
            url = reverse(f"plugins-api:netbox_k3s-api:k3s{ep[:-1] if ep != 'clusters' else 'cluster'}-list")
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, status.HTTP_200_OK, f"{ep}: {resp.content}")
            self.assertGreaterEqual(resp.json()["count"], 1)

    def test_create_cluster_via_api(self):
        url = reverse("plugins-api:netbox_k3s-api:k3scluster-list")
        resp = self.client.post(url, {"name": "edge", "status": "staging"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertTrue(K3sCluster.objects.filter(name="edge").exists())

    def test_create_full_chain_via_api(self):
        c = self.client.post(
            reverse("plugins-api:netbox_k3s-api:k3scluster-list"),
            {"name": "c2"}, format="json",
        ).json()
        n = self.client.post(
            reverse("plugins-api:netbox_k3s-api:k3snamespace-list"),
            {"name": "kube-system", "cluster": c["id"]}, format="json",
        )
        self.assertEqual(n.status_code, status.HTTP_201_CREATED, n.content)
        nid = n.json()["id"]
        p = self.client.post(
            reverse("plugins-api:netbox_k3s-api:k3spod-list"),
            {"name": "coredns", "namespace": nid, "status": "Running"}, format="json",
        )
        self.assertEqual(p.status_code, status.HTTP_201_CREATED, p.content)
        s = self.client.post(
            reverse("plugins-api:netbox_k3s-api:k3sservice-list"),
            {"name": "kube-dns", "namespace": nid, "type": "ClusterIP"}, format="json",
        )
        self.assertEqual(s.status_code, status.HTTP_201_CREATED, s.content)

    def test_filtering(self):
        url = reverse("plugins-api:netbox_k3s-api:k3spod-list")
        resp = self.client.get(url, {"status": "Running"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["count"], 1)
        resp = self.client.get(url, {"status": "Failed"})
        self.assertEqual(resp.json()["count"], 0)

    def test_search(self):
        url = reverse("plugins-api:netbox_k3s-api:k3spod-list")
        resp = self.client.get(url, {"q": "nginx"})
        self.assertEqual(resp.json()["count"], 1)

    def test_detail_fields_in_api(self):
        """The enriched fields must round-trip through the API."""
        url = reverse("plugins-api:netbox_k3s-api:k3spod-list")
        pod = self.client.get(url, {"name": "web-0"}).json()["results"][0]
        self.assertEqual(pod["restarts"], 3)
        self.assertEqual(pod["container_count"], 1)
        self.assertEqual(pod["labels"], {"app": "web"})
        url = reverse("plugins-api:netbox_k3s-api:k3sservice-list")
        svc = self.client.get(url, {"name": "web"}).json()["results"][0]
        self.assertEqual(svc["external_ip"], "192.0.2.10")
        self.assertEqual(svc["selector"], {"app": "web"})
        url = reverse("plugins-api:netbox_k3s-api:k3scluster-list")
        cl = self.client.get(url, {"name": "demo-cluster"}).json()["results"][0]
        self.assertEqual(cl["node_count"], 1)

    def test_unauthenticated_denied(self):
        anon = APIClient()
        url = reverse("plugins-api:netbox_k3s-api:k3scluster-list")
        resp = anon.get(url)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
