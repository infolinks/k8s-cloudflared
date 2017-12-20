#!/usr/bin/env python3

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Mapping, Sequence, Any

import requests

REQ_CONFIG: dict = {}


def get_json(path: str, params: dict = None) -> dict:
    return requests.get(url=f"https://api.cloudflare.com/client/v4{path}",
                        headers=REQ_CONFIG['headers'],
                        params=params).json()


def post_json(path: str, json: dict = None) -> None:
    requests.post(url=f"https://api.cloudflare.com/client/v4{path}",
                  headers=REQ_CONFIG['headers'],
                  json=json).raise_for_status()


def delete(path: str, params: dict = None) -> None:
    requests.delete(url=f"https://api.cloudflare.com/client/v4{path}",
                    headers=REQ_CONFIG['headers'],
                    params=params).raise_for_status()


def fetch_dns_records(zone_id: str, full_dns_name: str) -> Sequence[dict]:
    # fetch DNS "A" records for the given name
    query_result: dict = get_json(path=f"/zones/{zone_id}/dns_records", params={'name': full_dns_name, 'type': 'A'})
    return query_result['result'] if 'result' in query_result else []


def create_dns_record(zone_id: str, subdomain: str, ip_address: str) -> None:
    post_json(path=f"/zones/{zone_id}/dns_records", json={
        "type": "A",
        "name": subdomain,
        "content": ip_address,
        "proxied": False,
        "ttl": 120
    })


def delete_dns_record(zone_id: str, rec_id: str) -> None:
    delete(path=f"/zones/{zone_id}/dns_records/{rec_id}")


def update_dns_record(zone_id: str, subdomain: str, domain: str, ip_addresses: Sequence[str]) -> None:
    # fetch DNS "A" records for the given name
    actual_recs: Sequence[dict] = fetch_dns_records(zone_id=zone_id, full_dns_name=subdomain + '.' + domain)

    # create records for IP addresses without corresponding DNS record, and also mark actual records we want to keep,
    # if they are pointing to one of the given IP addresses; records that do not point to any of our given IP addresses
    # will NOT be marked for preservation, and will be deleted in a subsequent iteration
    for ip_address in ip_addresses:
        found: bool = False
        for actual_rec in actual_recs:
            if ip_address == actual_rec['content']:
                found: bool = True
                actual_rec['preserve'] = True
                break
        if not found:
            print(f"Adding DNS record: '{subdomain + '.' + domain}' -> '{ip_address}'")
            create_dns_record(zone_id=zone_id, subdomain=subdomain, ip_address=ip_address)

    # iterate actual records that have not been marked for preservation (ie. they point to IP addresses that are not
    # in the given list of IP addresses) and DELETE them via the API
    #
    ##########################################################################################
    # CAREFUL WHEN FIDDLING HERE!!!!!!
    #   using a wrong URL here CAN *** DELETE THE WHOLE ZONE *** !!!!!!!!!!!
    ##########################################################################################
    for actual_rec in [rec for rec in actual_recs if 'preserve' not in rec or not rec['preserve']]:
        rec_id: str = actual_rec['id']
        if not rec_id or len(rec_id) == 0:
            raise Exception("empty record ID encountered!")
        print(f"Deleting DNS record '{rec_id}': '{subdomain + '.' + domain}' -> '{actual_rec['content']}'")
        delete_dns_record(zone_id=zone_id, rec_id=rec_id)


def main():
    argparser = argparse.ArgumentParser(description='Updates Cloudflare DNS records')
    argparser.add_argument('auth_email', metavar='EMAIL', help='Email of the account used to connect to Cloudflare')
    argparser.add_argument('auth_key', metavar='KEY', help='authentication key of the Cloudflare account')
    argparser.add_argument('-f', '--file', dest='file', metavar='FILE',
                           help='file to read JSON from (defaults to stdin)')
    args = argparser.parse_args()

    # update configuration
    REQ_CONFIG['headers'] = {
        "Content-Type": "application/json",
        "X-Auth-Email": args.auth_email,
        "X-Auth-Key": args.auth_key
    }

    # read JSON from stdin
    try:
        if args.file:
            with Path(args.file).open() as f:
                dns_expected_state: Sequence[Mapping[str, Any]] = json.loads(f.read())
        else:
            dns_expected_state: Sequence[Mapping[str, Any]] = json.loads('\n'.join(sys.stdin.readlines()))
    except:
        sys.stderr.write("Failed reading JSON from stdin!\n")
        sys.stderr.flush()
        raise

    # discover our zone ID
    zones: Sequence[dict] = get_json(path=f"/zones")['result']

    # process DNS JSON, updating each individual records for each individual service
    try:
        for svc in dns_expected_state:
            for dns in svc['dns']:
                for zone in zones:
                    domain: str = zone['name']
                    if dns.endswith(domain):
                        subdomain: str = dns[0:dns.rfind('.' + domain)] if dns.endswith('.' + domain) else dns
                        update_dns_record(zone_id=zone['id'],
                                          subdomain=subdomain,
                                          domain=domain,
                                          ip_addresses=svc['ips'])
    except:
        # on error we sleep for a random time, to prevent abusing Cloudflare APIs
        rand = random.randrange(1, 5, 1)
        print(f"Encountered an error! sleeping for {rand} seconds to prevent abusing Cloudflare APIs "
              f"(will print the error afterwards)")
        time.sleep(rand)
        raise


if __name__ == "__main__":
    main()
