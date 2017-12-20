#!/usr/bin/env bash

# small IntelliJ hack to prevent warning on non-existing variables
if [[ "THIS_WILL_NEVER_BE_TRUE" == "true" ]]; then
    DOMAIN=${DOMAIN}
    AUTH_EMAIL=${AUTH_EMAIL}
    AUTH_KEY=${AUTH_KEY}
fi

while true; do
    # read domain name
    if [[ -z "${DOMAIN}" ]]; then
        echo "DOMAIN environment variable not defined" >&2
        exit 1
    fi

    # read Cloudflare authentication Email
    if [[ -z "${AUTH_EMAIL}" ]]; then
        echo "AUTH_EMAIL environment variable not defined" >&2
        exit 1
    fi

    # read Cloudflare authentication key
    if [[ -z "${AUTH_KEY}" ]]; then
        echo "AUTH_KEY environment variable not defined" >&2
        exit 1
    fi

    # fetch list of services from Kubernetes as JSON, filtering to only those with dns annotations, and redirecting them
    # to our Python script which will ensure their DNS records are correctly defined in Cloudflare
    kubectl get services --all-namespaces --output=json | jq -r '
                    [.items[] |
                    select(.spec.type == "LoadBalancer") |
                    select(.spec.loadBalancerIP) |
                    select(.metadata.annotations.dns) |
                    {
                        "kind": .kind,
                        "name": .metadata.name,
                        ips: [.status.loadBalancer.ingress[].ip],
                        "dns": .metadata.annotations.dns|fromjson
                    }]' | $(dirname $0)/update_dns_records.py "${DOMAIN}" "${AUTH_EMAIL}" "${AUTH_KEY}"
    if [[ $? != 0 ]]; then
        echo "Updating service DNS records failed!" >&2
        exit 1
    fi

    # fetch list of ingresses from Kubernetes as JSON, filtering to only those that got their public IP, and redirecting
    # them to our Python script which will ensure their DNS records are correctly defined in Cloudflare
    kubectl get ingress --all-namespaces --output=json | jq -r '
                    [.items[] |
                    select(.metadata.name | startswith( "kube-lego-" ) | not ) |
                    select(.status.loadBalancer) |
                    select(.status.loadBalancer.ingress) |
                    select(.status.loadBalancer.ingress[].ip) |
                    {
                        "kind": .kind,
                        "name": .metadata.name,
                        ips: [.status.loadBalancer.ingress[].ip],
                        "dns": [ .spec.rules[].host ]
                    }]' | $(dirname $0)/update_dns_records.py "${DOMAIN}" "${AUTH_EMAIL}" "${AUTH_KEY}"
    if [[ $? != 0 ]]; then
        echo "Updating ingress DNS records failed!" >&2
        exit 1
    fi

    # rinse & repeat
    sleep 10
    if [[ $? != 0 ]]; then
        echo "Interrupted" >&2
        exit 0
    fi
done
