import json
import urllib.request
import ssl

SERVER = "https://api.rm2.thpm.p1.openshiftapps.com:6443"
TOKEN = "sha256~TU3kndilhkXq2T1Etlr8FhhgjdmUiQVZIY2lgR1kkN4"
NAMESPACE = "jaisjoseph2028-dev"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def api_request(path, method="GET", data=None):
    url = f"{SERVER}{path}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_content = e.read().decode('utf-8')
        try:
            return e.code, json.loads(error_content)
        except:
            return e.code, {"error": error_content}

# 1. Create ImageStream
is_body = {
    "apiVersion": "image.openshift.io/v1",
    "kind": "ImageStream",
    "metadata": {
        "name": "bloodbank",
        "labels": {"app": "bloodbank"}
    }
}
status, res = api_request(f"/apis/image.openshift.io/v1/namespaces/{NAMESPACE}/imagestreams", "POST", is_body)
print(f"ImageStream: {status}")

# 2. Create BuildConfig (Docker build from GitHub)
bc_body = {
    "apiVersion": "build.openshift.io/v1",
    "kind": "BuildConfig",
    "metadata": {
        "name": "bloodbank",
        "labels": {"app": "bloodbank"}
    },
    "spec": {
        "source": {
            "type": "Git",
            "git": {
                "uri": "https://github.com/jais-002/bloodbank.git",
                "ref": "main"
            }
        },
        "strategy": {
            "type": "Docker",
            "dockerStrategy": {}
        },
        "output": {
            "to": {
                "kind": "ImageStreamTag",
                "name": "bloodbank:latest"
            }
        },
        "triggers": [
            {"type": "ConfigChange"},
            {"type": "ImageChange"}
        ]
    }
}
status, res = api_request(f"/apis/build.openshift.io/v1/namespaces/{NAMESPACE}/buildconfigs", "POST", bc_body)
print(f"BuildConfig: {status}")

# 3. Create Service
svc_body = {
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {
        "name": "bloodbank",
        "labels": {"app": "bloodbank"}
    },
    "spec": {
        "selector": {"app": "bloodbank"},
        "ports": [
            {
                "name": "8080-tcp",
                "port": 8080,
                "targetPort": 8080,
                "protocol": "TCP"
            }
        ]
    }
}
status, res = api_request(f"/api/v1/namespaces/{NAMESPACE}/services", "POST", svc_body)
print(f"Service: {status}")

# 4. Create Route
route_body = {
    "apiVersion": "route.openshift.io/v1",
    "kind": "Route",
    "metadata": {
        "name": "bloodbank",
        "labels": {"app": "bloodbank"}
    },
    "spec": {
        "to": {
            "kind": "Service",
            "name": "bloodbank"
        },
        "port": {
            "targetPort": "8080-tcp"
        },
        "tls": {
            "termination": "edge",
            "insecureEdgeTerminationPolicy": "Redirect"
        }
    }
}
status, res = api_request(f"/apis/route.openshift.io/v1/namespaces/{NAMESPACE}/routes", "POST", route_body)
print(f"Route: {status}")
if status in (200, 201):
    print("Route host:", res.get("spec", {}).get("host"))
elif "spec" in res:
    print("Route host:", res["spec"].get("host"))
else:
    print(res)
