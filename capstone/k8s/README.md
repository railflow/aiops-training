# k8s/

Apply in order: `kubectl apply -f 00-namespace.yaml -f 10-quota-and-priority.yaml -f 20-network-policy.yaml -f 30-rbac.yaml`, then the worker. NetworkPolicy needs the Calico cluster from Day 6. These manifests were parsed, not applied.
