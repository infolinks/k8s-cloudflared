#!/usr/bin/env python2
import argparse
import json
import sys

import requests

# URL constants
CF_BASE_URL = "https://api.cloudflare.com/client/v4"
CF_ZONES_URL = CF_BASE_URL + "/zones"
CF_ZONE_RECORDS = CF_BASE_URL + "/zones/%s/dns_records"
CF_ZONE_RECORD_ID = CF_BASE_URL + "/zones/%s/dns_records/%s"


def build_cloudflare_request_headers(auth_email, auth_key):
    return {
        "Content-Type": "application/json",
        "X-Auth-Key": auth_key,
        "X-Auth-Email": auth_email
    }


def update_dns_record(zone_id, auth_email, auth_key, subdomain, domain, ip_address):
    full_name = subdomain + '.' + domain

    print "Validataing domain name '%s' points to '%s'..." % (full_name, ip_address)
    dns_lookup = requests.get(CF_ZONE_RECORDS % zone_id,
                              headers=build_cloudflare_request_headers(auth_email, auth_key),
                              params={'name': full_name}).json()

    if 'result' not in dns_lookup or len(dns_lookup['result']) == 0:
        print "Creating missing DNS record for domain name '%s' and IP address '%s'..." % (full_name, ip_address)
        requests.post(CF_ZONE_RECORDS % zone_id,
                      headers=build_cloudflare_request_headers(auth_email, auth_key),
                      json={'type': 'A', 'name': subdomain, 'content': ip_address, 'ttl': 1, 'proxied': False}) \
            .raise_for_status()

    elif len(dns_lookup['result']) > 1:
        print "Too many DNS records found for domain name '%s'! (replacing all with a new one)" % full_name
        for rec in dns_lookup['result']:
            rec_id = rec['id']
            if not rec_id or len(rec_id) == 0:
                raise Exception("empty record ID encountered!")

            ##########################################################################################
            # CAREFUL WHEN FIDDLING HERE!!!!!!
            #   using a wrong URL here CAN *** DELETE THE WHOLE ZONE *** !!!!!!!!!!!
            ##########################################################################################
            delete_url = CF_ZONE_RECORD_ID % (zone_id, rec_id)
            print "Deleting DNS record with ID '%s' using URL: %s" % (rec_id, delete_url)
            # TODO: print IP address of record before deleting it
            # requests.delete(delete_url,
            #                 headers=build_cloudflare_request_headers(auth_email, auth_key)) \
            #     .raise_for_status()

        print "Creating new record for domain name '%s' and IP address '%s'..." % (full_name, ip_address)
        requests.post(CF_ZONE_RECORDS % zone_id,
                      headers=build_cloudflare_request_headers(auth_email, auth_key),
                      json={'type': 'A', 'name': subdomain, 'content': ip_address, 'ttl': 1, 'proxied': False}) \
            .raise_for_status()

    else:
        rec = dns_lookup['result'][0]
        rec_id = rec['id']
        rec_ip_address = rec['content']
        if rec_ip_address != ip_address:
            print "Updating DNS record with domain name '%s' to IP address '%s'..." % (full_name, ip_address)
            requests.put(CF_ZONE_RECORD_ID % (zone_id, rec_id),
                         headers=build_cloudflare_request_headers(auth_email, auth_key),
                         json={'type': 'A', 'name': subdomain, 'content': ip_address, 'ttl': 1, 'proxied': False}) \
                .raise_for_status()


def main():
    # TODO: support proxied records with a separate annotation? (or maybe all records should be proxied...)

    argparser = argparse.ArgumentParser(description='Updates Cloudflare DNS records')
    argparser.add_argument('--domain',
                           metavar='DOMAIN',
                           help='the public suffix domain name, eg. \'mydomain.com\' (which is the default)')
    argparser.add_argument('--auth-email',
                           required=True,
                           metavar='EMAIL',
                           help='Email of the account used to connect to Cloudflare')
    argparser.add_argument('--auth-key',
                           required=True,
                           metavar='KEY',
                           help='authentication key of the Cloudflare account')
    args = argparser.parse_args()

    # TODO: consider caching Cloudflare zone ID value in a file
    print "Obtaining Cloudflare zone ID for '%s'..." % args.domain
    zone_id_ = requests.get(CF_ZONES_URL,
                            headers=build_cloudflare_request_headers(args.auth_email, args.auth_key),
                            params={'name': args.domain}).json()['result'][0]['id']
    print "Zone ID for '%s' is %s" % (args.domain, zone_id_)

    # read JSON from stdin
    try:
        dns_expected_state = json.loads('\n'.join(sys.stdin.readlines()))
    except:
        sys.stderr.write("Failed reading JSON from stdin!\n")
        sys.stderr.flush()
        raise

    # process DNS JSON, updating each individual records for each individual service
    for svc in dns_expected_state:
        service_domain_names = svc['dns']
        service_ip_addresses = svc['ips']
        for dns in service_domain_names:
            for ip_address in service_ip_addresses:
                subdomain = dns[0:dns.rfind('.' + args.domain)] if dns.endswith('.' + args.domain) else dns
                update_dns_record(zone_id_, args.auth_email, args.auth_key, subdomain, args.domain, ip_address)
    print "DONE."

if __name__ == "__main__":
    main()
