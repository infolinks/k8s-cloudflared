FROM google/cloud-sdk:168.0.0
MAINTAINER Arik Kfir <arik@infolinks.com>
RUN apt-get update -qqy && apt-get install -qqy jq && rm -rf /var/lib/apt/lists/*
COPY cloudflared.sh update_dns_records.py /usr/local/bin/
RUN chmod a+x /usr/local/bin/cloudflared.sh /usr/local/bin/update_dns_records.py
ENTRYPOINT ["/usr/local/bin/cloudflared.sh"]
