import json
import urllib.request
import ssl

SERVER = "https://api.rm2.thpm.p1.openshiftapps.com:6443"
TOKEN = "sha256~TU3kndilhkXq2T1Etlr8FhhgjdmUiQVZIY2lgR1kkN4"
NAMESPACE = "jaisjoseph2028-dev"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

deployment_body = {
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "metadata": {
        "name": "bloodbank",
        "labels": {
            "app": "bloodbank",
            "app.kubernetes.io/component": "bloodbank",
            "app.kubernetes.io/instance": "bloodbank",
            "app.kubernetes.io/name": "bloodbank",
            "app.kubernetes.io/part-of": "bloodbank-app"
        }
    },
    "spec": {
        "replicas": 1,
        "selector": {
            "matchLabels": {
                "app": "bloodbank"
            }
        },
        "template": {
            "metadata": {
                "labels": {
                    "app": "bloodbank"
                }
            },
            "spec": {
                "containers": [
                    {
                        "name": "bloodbank",
                        "image": "image-registry.openshift-image-registry.svc:5000/jaisjoseph2028-dev/bloodbank:latest",
                        "ports": [
                            {
                                "containerPort": 8080,
                                "protocol": "TCP"
                            }
                        ],
                        "resources": {
                            "limits": {
                                "cpu": "500m",
                                "memory": "512Mi"
                            },
                            "requests": {
                                "cpu": "50m",
                                "memory": "128Mi"
                            }
                        },
                        "env": [
                            {
                                "name": "PORT",
                                "value": "8080"
                            }
                        ]
                    }
                ]
            }
        }
    }
}

req = urllib.request.Request(
    f"{SERVER}/apis/apps/v1/namespaces/{NAMESPACE}/deployments",
    data=json.dumps(deployment_body).encode('utf-8'),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, context=ctx) as resp:
        print(f"Deployment created: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"Error {e.code}: {e.read().decode('utf-8')}")
