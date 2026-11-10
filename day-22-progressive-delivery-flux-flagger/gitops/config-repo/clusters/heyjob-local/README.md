This repository ("hello-config") is what Flux watches. Layout:

    infrastructure/        Flagger and its load tester (HelmReleases)
    apps/podinfo/          the application: Deployment, IngressRoute, Canary

A release is a commit that changes `image:` in apps/podinfo/deployment.yaml. Do not `kubectl edit` anything Flux manages:
Flux puts it back.
