FROM infolinks/cloud-sdk:178.0.0-alpine
MAINTAINER Arik Kfir <arik@infolinks.com>
RUN apk --no-cache --update add jq tree bash python3 py3-pip && \
    pip3 install requests && \
    gcloud components install kubectl
COPY cloudflared.sh update_dns_records.py /usr/local/bin/
RUN chmod a+x /usr/local/bin/cloudflared.sh /usr/local/bin/update_dns_records.py
ENTRYPOINT ["/usr/local/bin/cloudflared.sh"]
