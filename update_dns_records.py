#!/usr/bin/env python3
import argparse
import json
import sys
from typing import Mapping, Sequence, Any

import requests

# base Cloudflare URL
CF_BASE_URL = "https://api.cloudflare.com/client/v4"


def build_cloudflare_request_headers(auth_email: str, auth_key: str) -> Mapping[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Auth-Key": auth_key,
        "X-Auth-Email": auth_email
    }


def update_dns_record(zone_id: int, auth_email: str, auth_key: str, subdomain: str, domain: str, ip_address: str):
    records_url: str = f"{CF_BASE_URL}/zones/{zone_id}/dns_records"
    full_name: str = subdomain + '.' + domain
    desired_record: dict = {
        'type': 'A',
        'name': subdomain,
        'content': ip_address,
        'ttl': 1,
        'proxied': False
    }

    dns_lookup: dict = requests.get(url=records_url,
                                    headers=build_cloudflare_request_headers(auth_email=auth_email, auth_key=auth_key),
                                    params={'name': full_name}).json()

    if 'result' not in dns_lookup or len(dns_lookup['result']) == 0:
        print(f"Creating missing DNS record: '{full_name}' -> '{ip_address}'")
        requests.post(url=records_url,
                      headers=build_cloudflare_request_headers(auth_email=auth_email, auth_key=auth_key),
                      json=desired_record).raise_for_status()

    elif len(dns_lookup['result']) > 1:
        print(f"Too many DNS records found for domain name '{full_name}'! (replacing all)", file=sys.stderr)
        for rec in dns_lookup['result']:
            rec_id: str = rec['id']
            if not rec_id or len(rec_id) == 0:
                raise Exception("empty record ID encountered!")

            ##########################################################################################
            # CAREFUL WHEN FIDDLING HERE!!!!!!
            #   using a wrong URL here CAN *** DELETE THE WHOLE ZONE *** !!!!!!!!!!!
            ##########################################################################################
            delete_url = f"{records_url}/{rec_id}"
            print(f"Deleting DNS record with ID '{rec_id}' ({rec['content']}) using: {delete_url}")
            # TODO: re-enable DNS record deletion
            # requests.delete(url=delete_url,
            #                 headers=build_cloudflare_request_headers(auth_email=auth_email, auth_key=auth_key))\
            #     .raise_for_status()

        # print(f"Creating replacement record: '{full_name}' -> '{ip_address}'")
        # requests.post(url=records_url,
        #               headers=build_cloudflare_request_headers(auth_email=auth_email, auth_key=auth_key),
        #               json=desired_record).raise_for_status()

    else:
        rec: dict = dns_lookup['result'][0]
        rec_id: str = rec['id']
        rec_ip_address: str = rec['content']
        if rec_ip_address != ip_address:
            print(f"Updating DNS record '{rec_id}': '{full_name}' -> '{ip_address}'")
            requests.put(url=f"{records_url}/{rec_id}",
                         headers=build_cloudflare_request_headers(auth_email=auth_email, auth_key=auth_key),
                         json=desired_record).raise_for_status()


def main():
    argparser = argparse.ArgumentParser(description='Updates Cloudflare DNS records')
    argparser.add_argument('domain', help='public suffix domain name, eg. \'mydomain.com\'')
    argparser.add_argument('auth_email', metavar='EMAIL', help='Email of the account used to connect to Cloudflare')
    argparser.add_argument('auth_key', metavar='KEY', help='authentication key of the Cloudflare account')
    args = argparser.parse_args()

    zone: dict = requests.get(
        url=f"{CF_BASE_URL}/zones",
        headers=build_cloudflare_request_headers(auth_email=args.auth_email, auth_key=args.auth_key),
        params={'name': args.domain}).json()['result'][0]

    # read JSON from stdin
    try:
        dns_expected_state: Sequence[Mapping[str, Any]] = json.loads('\n'.join(sys.stdin.readlines()))
    except:
        sys.stderr.write("Failed reading JSON from stdin!\n")
        sys.stderr.flush()
        raise

    # process DNS JSON, updating each individual records for each individual service
    for svc in dns_expected_state:
        service_domain_names: Sequence[str] = svc['dns']
        service_ip_addresses: Sequence[str] = svc['ips']
        for dns in service_domain_names:
            for ip_address in service_ip_addresses:
                subdomain: str = dns[0:dns.rfind('.' + args.domain)] if dns.endswith('.' + args.domain) else dns
                update_dns_record(zone_id=int(zone['id']),
                                  auth_email=args.auth_email,
                                  auth_key=args.auth_key,
                                  subdomain=subdomain,
                                  domain=args.domain,
                                  ip_address=ip_address)


if __name__ == "__main__":
    main()
