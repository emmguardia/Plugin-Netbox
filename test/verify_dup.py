import json
import os
import urllib.request

BASE = "http://localhost:8080/api/plugins/k3s"
TOKEN = os.environ["NB"]


def api(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Token {TOKEN}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


pods = api("/pods/?name=web-0")["results"]
print(f"pods named web-0: {len(pods)}")
for p in pods:
    print(f"  ns={p['namespace']['name']} node={p['node']} image={p['image']} status={p['status']}")
assert len(pods) == 2, "Expected 2 distinct web-0 pods (one per namespace)!"
ns_set = {p["namespace"]["name"] for p in pods}
assert ns_set == {"default", "kube-system"}, ns_set
print("OK: same-named pods in different namespaces are kept distinct.")
