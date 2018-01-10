import argparse
import json
import sys
import base64
from typing import Mapping, Sequence, Any

import requests


# build headers
def build_cloudflare_request_headers(auth_email: str, auth_key: str) -> Mapping[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Auth-Key": auth_key,
        "X-Auth-Email": auth_email
    }


# upload certificate to cloudflare
def upload_certificate(zone_id: str, auth_email: str, auth_key: str, key: str, crt: str):
    url: str = f"{CF_BASE_URL}/zones/{zone_id}"
    certificates_url: str = url + '/custom_certificates'

    certificate: dict = {
        'certificate': crt,
        'private_key': key
    }

    requests.post(url=certificates_url,
                  headers=build_cloudflare_request_headers(auth_email=auth_email, auth_key=auth_key),
                  json=certificate).raise_for_status()


def main():
    argparser = argparse.ArgumentParser(description="Uploads custom certificate to cloudflare")
    argparser.add_argument('domain', help='public suffix domain name, eg. \'mydomain.com\'')
    argparser.add_argument('auth_email', metavar='EMAIL', help='Email of the account used to connect to Cloudflare')
    argparser.add_argument('auth_key', metavar='KEY', help='authentication key of the Cloudflare account')
    args = argparser.parse_args()

    zone: dict = requests.get(
        url=f"{CF_BASE_URL}/zones",
        headers=build_cloudflare_request_headers(auth_email=args.auth_email, auth_key=args.auth_key),
        params={'name': args.domain}).json()['result'][0]

    certificate_list: Sequence[Mapping[str, Any]] = json.loads('\n'.join(sys.stdin.readlines()))
    for obj in certificate_list:
        private_key = base64.b64decode(obj['tls.key']).decode('utf-8').replace('\n', '\\n')
        cert = base64.b64decode(obj['tls.crt']).decode('utf-8').replace('\n', '\\n')
        upload_certificate(zone_id=zone['id'],
                           auth_email=args.auth_email,
                           auth_key=args.auth_key,
                           key=private_key,
                           crt=cert)


if __name__ == '__main__':
    main()