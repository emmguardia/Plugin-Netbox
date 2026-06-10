import json
import os
import urllib.request

BASE = "http://localhost:8080/api/plugins/k3s"
TOKEN = os.environ["NB"]


def api(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Token {TOKEN}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


pod = api("/pods/?name=web-0")["results"][0]
print("pod web-0  : restarts=", pod["restarts"], "containers=", pod["container_count"],
      "started=", pod["started"], "labels=", pod["labels"])
svc = api("/services/?name=web")["results"][0]
print("svc web    : external_ip=", svc["external_ip"], "selector=", svc["selector"])
cl = api("/clusters/?name=demo-cluster")["results"][0]
print("cluster    : version=", cl["version"], "node_count=", cl["node_count"])
