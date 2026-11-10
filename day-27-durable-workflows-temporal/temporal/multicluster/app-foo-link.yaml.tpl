# Applied to the "app-foo" cluster after replacing __COMMON_NODE_IP__ (see probe.sh). A Service WITHOUT a selector plus an EndpointSlice
# that points at the other cluster's node: inside app-foo, "shared-postgres.platform-link" now resolves like any Service.
# (The older Endpoints object also works but is deprecated in recent Kubernetes: use EndpointSlice; check the docs for your version.)
apiVersion: v1
kind: Namespace
metadata: {name: platform-link}
---
apiVersion: v1
kind: Service
metadata: {name: shared-postgres, namespace: platform-link}
spec:
  ports: [{name: pg, port: 5432, targetPort: 30432}]
---
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: shared-postgres-1
  namespace: platform-link
  labels: {kubernetes.io/service-name: shared-postgres}
addressType: IPv4
ports: [{name: pg, port: 30432, protocol: TCP}]
endpoints:
  - addresses: ["__COMMON_NODE_IP__"]
