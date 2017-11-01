# k8s-cloudflared

[![Build status](https://badge.buildkite.com/8e3145c6e8516acd680b71ea97e5bfa18073f9ee4eb286126c.svg)](https://buildkite.com/infolinks/k8s-cloudflared)

Container for continually updating Cloudflare DNS records for Kubernetes
`Service` and `Ingress` objects found in a cluster.

This container, when deployed to a Kubernetes cluster (though it can
essentially run externally to the cluster when `kubectl` has been
properly configured to access the cluster externally) will continually
monitor deployed `Service` and `Ingress` resources, and will ensure that
DNS records for them exist in a configured Cloudflare account.

## Service Resources

Every `Service` resource of type `LoadBalancer`, which also has the
`dns` annotation, will be picked up by this container, expecting that
the annotation's value will be a JSON array (serialized to a string as
the configuration value) of sub-domains for which DNS records need to
point to in Cloudflare.

Example `Service` manifest containing the annotation:

    apiVersion: v1
    kind: Service
    metadata:
        name: my-service
        annotations:
        dns: |
            [ "my-svc" ]
        labels:
            name: my-service
    spec:
        type: LoadBalancer
        loadBalancerIP: 1.2.3.4
        #
        # ... other service properties here ...
        #

The Cloudflared daemon will update the DNS record `my-service.infolinks.com`
to point to `1.2.3.4` in Cloudflare.

## Ingress Resources

The same applies to `Ingress` resources in the cluster, but you don't
have to define the `dns` annotation - the host names will be taken
automatically from the host rules.

## Deployment

When running externally to a Kubernetes cluster, make sure that you
configure `kubectl` to properly access your cluster.

If this container is running inside a Kubernetes cluster, you just need
to make sure the `Pod` running this container has the RBAC permissions
to use `kubectl`.

## Contributions

Any contribution to the project will be appreciated! Whether it's bug
reports, feature requests, pull requests - all are welcome, as long as
you follow our [contribution guidelines for this project](CONTRIBUTING.md)
and our [code of conduct](CODE_OF_CONDUCT.md).
