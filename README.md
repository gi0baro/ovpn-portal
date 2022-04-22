# OpenVPN Portal

An OIDC authenticated client configuration generator for OpenVPN tunnels.

OpenVPN Portal requires an S3-compatible object storage endpoint.

## Installation

OpenVPN Portal can be installed to any Kubernetes >= 1.14 cluster using the Helm 3 chart:

```
helm repo add ovpn-portal https://gi0baro.github.io/ovpn-portal
helm install --generate-name --atomic ovpn-portal/ovpn-portal
```

OpenVPN Portal includes support to also deploy its dependencies, just enable them in the values:

```yaml
minio:
  enabled: true
  rootPassword: super-strong-password
```

## License

OpenVPN Portal is released under the BSD License.
