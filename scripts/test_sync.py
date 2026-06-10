"""Unit tests for sync_k3s.py — no network or kubectl required.

Run:  python -m unittest scripts.test_sync   (from repo root)
   or: python test_sync.py                   (from scripts/)
"""

import importlib.util
import os
import unittest
from unittest import mock

# Import sync_k3s.py as a module regardless of CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sync_k3s", os.path.join(_HERE, "sync_k3s.py"))
sync_k3s = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync_k3s)


# Canned kubectl payloads keyed by the resource being queried.
KUBECTL_DATA = {
    "nodes": {
        "items": [
            {
                "metadata": {"name": "node-1"},
                "status": {"nodeInfo": {"kubeletVersion": "v1.30.2+k3s1"}},
            },
        ]
    },
    "namespaces": {
        "items": [
            {"metadata": {"name": "default"}},
            {"metadata": {"name": "kube-system"}},
        ]
    },
    "pods": {
        "items": [
            {
                "metadata": {
                    "name": "web-0", "namespace": "default",
                    "labels": {"app": "web"},
                },
                "spec": {"nodeName": "node-1", "containers": [{"image": "nginx:1.27"}]},
                "status": {
                    "phase": "Running", "podIP": "10.42.0.5",
                    "startTime": "2026-06-10T08:00:00Z",
                    "containerStatuses": [{"restartCount": 3}],
                },
            },
            {
                # Pod in a namespace we did not sync -> must be skipped.
                "metadata": {"name": "ghost", "namespace": "does-not-exist"},
                "spec": {"containers": [{"image": "x"}]},
                "status": {"phase": "Running"},
            },
        ]
    },
    "services": {
        "items": [
            {
                "metadata": {"name": "web", "namespace": "default"},
                "spec": {
                    "type": "ClusterIP",
                    "clusterIP": "10.43.0.10",
                    "ports": [{"port": 80, "targetPort": 8080, "protocol": "TCP"}],
                    "selector": {"app": "web"},
                },
                "status": {"loadBalancer": {"ingress": [{"ip": "192.0.2.10"}]}},
            },
            {
                "metadata": {"name": "headless", "namespace": "default"},
                "spec": {"type": "ClusterIP", "clusterIP": "None", "ports": []},
            },
        ]
    },
}


def fake_kube_get(resource):
    # resource is "namespaces" | "pods" | "services"
    return KUBECTL_DATA[resource]


class FakeNetBox:
    """Records every upsert call and hands back incrementing ids.

    ``stale`` simulates objects already present in NetBox but absent from the
    live cluster — they must be pruned. Keyed by endpoint.
    """

    def __init__(self, stale=None):
        self.calls = []
        self.deleted = []  # list of (endpoint, id)
        self._id = 0
        self._stale = stale or {}
        self._created = {}  # endpoint -> list of ids handed out

    def upsert(self, endpoint, match, data):
        self._id += 1
        self.calls.append({"endpoint": endpoint, "match": match, "data": data})
        self._created.setdefault(endpoint, []).append(self._id)
        return {"id": self._id, **match, **data}

    def list_all(self, endpoint, params=None):
        ids = list(self._created.get(endpoint, []))
        ids += [o["id"] for o in self._stale.get(endpoint, [])]
        return [{"id": i} for i in ids]

    def delete(self, endpoint, obj_id):
        self.deleted.append((endpoint, obj_id))


class SyncLogicTest(unittest.TestCase):
    def setUp(self):
        self.nb = FakeNetBox()
        patcher = mock.patch.object(sync_k3s, "kube_get", fake_kube_get)
        patcher.start()
        self.addCleanup(patcher.stop)
        sync_k3s.sync(self.nb, "demo-cluster")

    def _calls(self, endpoint):
        return [c for c in self.nb.calls if c["endpoint"] == endpoint]

    def test_cluster_created_first(self):
        first = self.nb.calls[0]
        self.assertEqual(first["endpoint"], "clusters/")
        self.assertEqual(first["match"], {"name": "demo-cluster"})
        self.assertEqual(first["data"]["status"], "active")
        self.assertEqual(first["data"]["name"], "demo-cluster")
        self.assertEqual(first["data"]["version"], "v1.30.2+k3s1")
        self.assertEqual(first["data"]["node_count"], 1)

    def test_all_namespaces_synced(self):
        ns = self._calls("namespaces/")
        names = {c["match"]["name"] for c in ns}
        self.assertEqual(names, {"default", "kube-system"})
        for c in ns:
            # Match must use the *_id filter name, body uses the FK field name.
            self.assertEqual(c["match"]["cluster_id"], 1)
            self.assertEqual(c["data"]["cluster"], 1)

    def test_pod_in_unknown_namespace_skipped(self):
        pods = self._calls("pods/")
        names = {c["match"]["name"] for c in pods}
        self.assertIn("web-0", names)
        self.assertNotIn("ghost", names)  # namespace does-not-exist -> skipped

    def test_pod_payload_fields(self):
        pod = next(c for c in self._calls("pods/") if c["match"]["name"] == "web-0")
        # ids: cluster=1, default ns=2, kube-system ns=3.
        self.assertEqual(pod["match"]["namespace_id"], 2)
        self.assertEqual(pod["data"]["namespace"], 2)
        self.assertEqual(pod["data"]["image"], "nginx:1.27")
        self.assertEqual(pod["data"]["status"], "Running")
        self.assertEqual(pod["data"]["node"], "node-1")
        self.assertEqual(pod["data"]["ip_address"], "10.42.0.5")
        self.assertEqual(pod["data"]["restarts"], 3)
        self.assertEqual(pod["data"]["container_count"], 1)
        self.assertEqual(pod["data"]["started"], "2026-06-10T08:00:00Z")
        self.assertEqual(pod["data"]["labels"], {"app": "web"})

    def test_service_port_formatting(self):
        svc = next(c for c in self._calls("services/") if c["match"]["name"] == "web")
        self.assertEqual(svc["data"]["ports"], "80:8080/TCP")
        self.assertEqual(svc["data"]["cluster_ip"], "10.43.0.10")
        self.assertEqual(svc["data"]["external_ip"], "192.0.2.10")
        self.assertEqual(svc["data"]["selector"], {"app": "web"})

    def test_headless_service_clusterip_none(self):
        svc = next(c for c in self._calls("services/") if c["match"]["name"] == "headless")
        # "None" string from kubectl must become Python None for the API.
        self.assertIsNone(svc["data"]["cluster_ip"])
        self.assertEqual(svc["data"]["ports"], "")

    def test_no_prune_when_everything_alive(self):
        # All listed objects were just upserted -> nothing must be deleted.
        self.assertEqual(self.nb.deleted, [])


class PruneTest(unittest.TestCase):
    """Objects present in NetBox but gone from the cluster must be deleted."""

    def setUp(self):
        # Simulate leftovers in NetBox: 2 stale pods (e.g. completed Job pods
        # with unique names), 1 stale service, 1 stale namespace.
        self.nb = FakeNetBox(stale={
            "pods/": [{"id": 901}, {"id": 902}],
            "services/": [{"id": 903}],
            "namespaces/": [{"id": 904}],
        })
        patcher = mock.patch.object(sync_k3s, "kube_get", fake_kube_get)
        patcher.start()
        self.addCleanup(patcher.stop)
        sync_k3s.sync(self.nb, "demo-cluster")

    def test_stale_objects_deleted(self):
        self.assertIn(("pods/", 901), self.nb.deleted)
        self.assertIn(("pods/", 902), self.nb.deleted)
        self.assertIn(("services/", 903), self.nb.deleted)
        self.assertIn(("namespaces/", 904), self.nb.deleted)

    def test_live_objects_kept(self):
        # No object we just upserted may be deleted.
        live_ids = {i for ids in self.nb._created.values() for i in ids}
        deleted_ids = {i for _, i in self.nb.deleted}
        self.assertFalse(live_ids & deleted_ids)


class UpsertHttpTest(unittest.TestCase):
    """Verify NetBox.upsert chooses PATCH vs POST correctly."""

    def _nb(self, existing_results):
        nb = sync_k3s.NetBox.__new__(sync_k3s.NetBox)
        nb.base = "http://nb/"
        nb.token = "t"
        nb.ctx = None
        nb._calls = []

        def fake_request(method, path, data=None):
            nb._calls.append((method, path, data))
            return {"id": 99}

        def fake_get(path, params=None):
            return {"results": existing_results}

        nb._request = fake_request
        nb.get = fake_get
        return nb

    def test_post_when_absent(self):
        nb = self._nb(existing_results=[])
        nb.upsert("clusters/", {"name": "x"}, {"status": "active"})
        methods = [c[0] for c in nb._calls]
        self.assertIn("POST", methods)
        self.assertNotIn("PATCH", methods)

    def test_patch_when_present(self):
        nb = self._nb(existing_results=[{"id": 7}])
        nb.upsert("clusters/", {"name": "x"}, {"status": "active"})
        methods = [c[0] for c in nb._calls]
        self.assertIn("PATCH", methods)
        self.assertNotIn("POST", methods)
        # PATCH must target the existing object id.
        patch_path = next(c[1] for c in nb._calls if c[0] == "PATCH")
        self.assertIn("/clusters/7/", patch_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
