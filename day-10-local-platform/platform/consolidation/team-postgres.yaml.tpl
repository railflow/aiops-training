# One team's private Postgres: the "before" picture. Three of these is the problem; thirty is the incident.
apiVersion: v1
kind: Namespace
metadata: {name: team-__TEAM__}
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: db, namespace: team-__TEAM__, labels: {app: db}}
spec:
  replicas: 1
  strategy: {type: Recreate}
  selector: {matchLabels: {app: db}}
  template:
    metadata: {labels: {app: db}}
    spec:
      containers:
        - name: postgres
          image: postgres:17-alpine
          env:
            - {name: POSTGRES_PASSWORD, value: password}      # on purpose: a typical "it works" shortcut to find and fix
            - {name: POSTGRES_DB, value: __TEAM__}
          ports: [{containerPort: 5432}]
          resources: {requests: {cpu: 50m, memory: 128Mi}}
---
apiVersion: v1
kind: Service
metadata: {name: db, namespace: team-__TEAM__}
spec:
  selector: {app: db}
  ports: [{port: 5432}]
