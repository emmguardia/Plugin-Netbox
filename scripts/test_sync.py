"""Unit tests for sync_k3s.py — no network or kubectl required.

Run:  python scripts/test_sync.py   (from repo root)
   or: python test_sync.py          (from scripts/)
"""

import copy
import importlib.util
import os
import unittest
from unittest import mock

# Import sync_k3s.py as a module regardless of CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sync_k3s", os.path.join(_HERE, "sync_k3s.py"))
sync_k3s = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync_k3s)


# Canned kubectl/k8s-API payloads keyed by resource.
BASE_DATA = {
    "nodes": {
        "items": [
            {"metadata": {"name": "node-1"},
             "status": {"nodeInfo": {"kubeletVersion": "v1.30.2+k3s1"}}},
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
                "metadata": {"name": "web-0", "namespace": "default", "labels": {"app": "web"}},
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
                    "type": "LoadBalancer", "clusterIP": "10.43.0.10",
                    "selector": {"app": "web"},
                    "ports": [{"port": 80, "targetPort": 8080, "protocol": "TCP"}],
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


def make_kube_get(data):
    def _f(resource):
        return data[resource]
    return _f


class FakeNetBox:
    """In-memory stand-in for the real NetBox client, with call recording."""

    def __init__(self):
        self.store = {"clusters/": {}, "namespaces/": {}, "pods/": {}, "services/": {}}
        self._id = 0
        self.calls = []  # list of (op, endpoint, count)

    def _next(self):
        self._id += 1
        return self._id

    def _ns_name(self, ns_id):
        ns = self.store["namespaces/"].get(ns_id)
        return ns["name"] if ns else None

    def upsert(self, endpoint, match, data):
        for obj in self.store[endpoint].values():
            if obj["name"] == match["name"]:
                obj.update(data)
                self.calls.append(("upsert-update", endpoint, 1))
                return dict(obj)
        oid = self._next()
        obj = {"id": oid, **data}
        self.store[endpoint][oid] = obj
        self.calls.append(("upsert-create", endpoint, 1))
        return dict(obj)

    def list_all(self, endpoint, params=None):
        out = []
        for obj in self.store[endpoint].values():
            o = dict(obj)
            if isinstance(o.get("namespace"), int):
                o["namespace"] = {"id": o["namespace"], "name": self._ns_name(o["namespace"])}
            out.append(o)
        return out

    def bulk_create(self, endpoint, items):
        created = []
        for data in items:
            oid = self._next()
            obj = {"id": oid, **data}
            self.store[endpoint][oid] = obj
            created.append(dict(obj))
        if items:
            self.calls.append(("bulk_create", endpoint, len(items)))
        return created

    def bulk_update(self, endpoint, items):
        for it in items:
            self.store[endpoint][it["id"]].update({k: v for k, v in it.items() if k != "id"})
        if items:
            self.calls.append(("bulk_update", endpoint, len(items)))
        return items

    def bulk_delete(self, endpoint, ids):
        for i in ids:
            self.store[endpoint].pop(i, None)
        if ids:
            self.calls.append(("bulk_delete", endpoint, len(ids)))


class FirstRunTest(unittest.TestCase):
    def setUp(self):
        self.nb = FakeNetBox()
        self.data = copy.deepcopy(BASE_DATA)
        p = mock.patch.object(sync_k3s, "kube_get", make_kube_get(self.data))
        p.start()
        self.addCleanup(p.stop)
        sync_k3s.sync(self.nb, "demo-cluster")

    def _one(self, endpoint, name):
        return next(o for o in self.nb.store[endpoint].values() if o["name"] == name)

    def test_cluster(self):
        cl = next(iter(self.nb.store["clusters/"].values()))
        self.assertEqual(cl["name"], "demo-cluster")
        self.assertEqual(cl["version"], "v1.30.2+k3s1")
        self.assertEqual(cl["node_count"], 1)

    def test_namespaces(self):
        names = {n["name"] for n in self.nb.store["namespaces/"].values()}
        self.assertEqual(names, {"default", "kube-system"})

    def test_pod_skipped_unknown_namespace(self):
        names = {p["name"] for p in self.nb.store["pods/"].values()}
        self.assertEqual(names, {"web-0"})  # 'ghost' skipped

    def test_pod_fields(self):
        web = self._one("pods/", "web-0")
        self.assertEqual(web["image"], "nginx:1.27")
        self.assertEqual(web["status"], "Running")
        self.assertEqual(web["node"], "node-1")
        self.assertEqual(web["ip_address"], "10.42.0.5")
        self.assertEqual(web["restarts"], 3)
        self.assertEqual(web["container_count"], 1)
        self.assertEqual(web["started"], "2026-06-10T08:00:00Z")
        self.assertEqual(web["labels"], {"app": "web"})

    def test_service_fields(self):
        web = self._one("services/", "web")
        self.assertEqual(web["type"], "LoadBalancer")
        self.assertEqual(web["cluster_ip"], "10.43.0.10")
        self.assertEqual(web["external_ip"], "192.0.2.10")
        self.assertEqual(web["ports"], "80:8080/TCP")
        self.assertEqual(web["selector"], {"app": "web"})
        headless = self._one("services/", "headless")
        self.assertIsNone(headless["cluster_ip"])
        self.assertEqual(headless["ports"], "")


class IdempotencyTest(unittest.TestCase):
    def test_second_run_does_no_bulk_writes(self):
        nb = FakeNetBox()
        data = copy.deepcopy(BASE_DATA)
        with mock.patch.object(sync_k3s, "kube_get", make_kube_get(data)):
            sync_k3s.sync(nb, "demo-cluster")
            nb.calls.clear()
            sync_k3s.sync(nb, "demo-cluster")
        bulk = [c for c in nb.calls if c[0].startswith("bulk")]
        self.assertEqual(bulk, [], f"2nd run should write nothing in bulk, got: {nb.calls}")


class ChangeDetectionTest(unittest.TestCase):
    def test_only_changed_object_updated(self):
        nb = FakeNetBox()
        data = copy.deepcopy(BASE_DATA)
        with mock.patch.object(sync_k3s, "kube_get", make_kube_get(data)):
            sync_k3s.sync(nb, "demo-cluster")
            nb.calls.clear()
            data["pods"]["items"][0]["status"]["phase"] = "Failed"  # web-0 changes
            sync_k3s.sync(nb, "demo-cluster")
        updates = [c for c in nb.calls if c[0] == "bulk_update"]
        self.assertEqual(updates, [("bulk_update", "pods/", 1)])
        web = next(p for p in nb.store["pods/"].values() if p["name"] == "web-0")
        self.assertEqual(web["status"], "Failed")


class PruneTest(unittest.TestCase):
    def test_stale_pod_removed(self):
        nb = FakeNetBox()
        data = copy.deepcopy(BASE_DATA)
        with mock.patch.object(sync_k3s, "kube_get", make_kube_get(data)):
            sync_k3s.sync(nb, "demo-cluster")
            ns_id = next(n["id"] for n in nb.store["namespaces/"].values() if n["name"] == "default")
            sid = nb._next()
            nb.store["pods/"][sid] = {
                "id": sid, "name": "old-job-xyz", "namespace": ns_id,
                "image": "", "status": "Succeeded", "node": "", "ip_address": None,
                "restarts": 0, "container_count": 1, "started": None, "labels": {},
            }
            nb.calls.clear()
            sync_k3s.sync(nb, "demo-cluster")
        self.assertNotIn(sid, nb.store["pods/"])
        self.assertTrue(any(c[0] == "bulk_delete" and c[1] == "pods/" for c in nb.calls))


class BulkHttpTest(unittest.TestCase):
    """The NetBox client's bulk methods must chunk and format requests right."""

    def _nb(self):
        nb = sync_k3s.NetBox.__new__(sync_k3s.NetBox)
        nb.base = "http://nb/"
        nb.token = "t"
        nb.ctx = None
        nb.sent = []

        def fake_request(method, path, data=None):
            nb.sent.append((method, path, data))
            return data if isinstance(data, list) else None

        nb._request = fake_request
        return nb

    def test_bulk_create_chunks(self):
        nb = self._nb()
        items = [{"name": f"p{i}"} for i in range(250)]
        nb.bulk_create("pods/", items)
        posts = [s for s in nb.sent if s[0] == "POST"]
        self.assertEqual(len(posts), 3)  # 100 + 100 + 50
        self.assertEqual(sum(len(p[2]) for p in posts), 250)

    def test_bulk_delete_format(self):
        nb = self._nb()
        nb.bulk_delete("pods/", [5, 7])
        d = next(s for s in nb.sent if s[0] == "DELETE")
        self.assertEqual(d[2], [{"id": 5}, {"id": 7}])

    def test_empty_makes_no_request(self):
        nb = self._nb()
        nb.bulk_create("pods/", [])
        nb.bulk_update("pods/", [])
        nb.bulk_delete("pods/", [])
        self.assertEqual(nb.sent, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
