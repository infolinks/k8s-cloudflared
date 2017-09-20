#!/usr/bin/env bash

AUTH_EMAIL_FILE=./conf/cf_auth_email.txt
AUTH_KEY_FILE=./conf/cf_auth_key.txt
DOMAIN_FILE=./conf/cf_domain.txt

while true; do
    # read domain name
    [[ -e "${DOMAIN_FILE}" ]] && DOMAIN=$(cat ${DOMAIN_FILE})
    if [[ -z "${DOMAIN}" ]]; then
        echo "DOMAIN not defined, and empty Cloudflare domain at '${DOMAIN_FILE}'!" >&2
        exit 1
    fi

    # read Cloudflare authentication Email
    [[ -e "${AUTH_EMAIL_FILE}" ]] && AUTH_EMAIL=$(cat ${AUTH_EMAIL_FILE})
    if [[ -z "${AUTH_EMAIL}" ]]; then
        echo "AUTH_EMAIL not defined, and empty Cloudflare authentication Email at '${AUTH_EMAIL_FILE}'!" >&2
        exit 1
    fi

    # read Cloudflare authentication key
    [[ -e "${AUTH_KEY_FILE}" ]] && AUTH_KEY=$(cat ${AUTH_KEY_FILE})
    if [[ -z "${AUTH_KEY}" ]]; then
        echo "AUTH_KEY not defined, and empty Cloudflare authentication key at '${AUTH_KEY_FILE}'!" >&2
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
                    }]' | $(dirname $0)/update_dns_records.py --domain "${DOMAIN}" \
                                                              --auth-email "${AUTH_EMAIL}" \
                                                              --auth-key "${AUTH_KEY}"
    if [[ $? != 0 ]]; then
        echo "Updating service DNS records failed!" >&2
        exit 1
    fi

    # fetch list of ingresses from Kubernetes as JSON, filtering to only those that got their public IP, and redirecting
    # them to our Python script which will ensure their DNS records are correctly defined in Cloudflare
    kubectl get ingress --all-namespaces --output=json | jq -r '
                    [.items[] |
                    select(.status.loadBalancer) |
                    select(.status.loadBalancer.ingress) |
                    select(.status.loadBalancer.ingress[].ip) |
                    {
                        "kind": .kind,
                        "name": .metadata.name,
                        ips: [.status.loadBalancer.ingress[].ip],
                        "dns": [ .spec.rules[].host ]
                    }]' | $(dirname $0)/update_dns_records.py --domain "${DOMAIN}" \
                                                              --auth-email "${AUTH_EMAIL}" \
                                                              --auth-key "${AUTH_KEY}"
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
