import json
import os
import urllib.request

BASE = "http://localhost:8080/api/plugins/k3s"
TOKEN = os.environ["NB"]


def api(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Token {TOKEN}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


for res in ("clusters", "namespaces", "pods", "services"):
    print(f"{res}: {api('/' + res + '/')['count']}")

pod = api("/pods/?name=web-0")["results"][0]
print("pod web-0:", pod["image"], pod["status"], pod["node"], pod["ip_address"])

svc = api("/services/?name=web")["results"][0]
print("svc web:", svc["type"], svc["cluster_ip"], repr(svc["ports"]))

# Namespace linkage
ns = api("/namespaces/?name=default")["results"][0]
print("ns default cluster:", ns["cluster"]["name"])
