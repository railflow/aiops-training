# Least privilege: read-only access to the hello-app secrets and nothing else.
# KV version 2 stores data under "data/" and metadata under "metadata/".
path "secret/data/hello-app/*" {
  capabilities = ["read"]
}

path "secret/metadata/hello-app/*" {
  capabilities = ["read", "list"]
}
