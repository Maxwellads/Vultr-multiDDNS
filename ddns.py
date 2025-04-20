#!/usr/bin/env python3
'''
Dynamic DNS service for Vultr
Extended to support per-record interface mappings and configurable IP mode
'''

import json
import sys
import requests
import re
import subprocess
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

CONFIG_PATH = "/etc/vultrddns/config.json"

# Load config
with open(CONFIG_PATH) as config_file:
    config = json.load(config_file)

api_key = config["api_key"]
domain = config["domain"]
dynamic_records = config["dynamic_records"]

# Get IP address from interface
def get_ipv4_from_interface(interface):
    logging.debug(f"Fetching IPv4 address for interface: {interface}")
    result = subprocess.run(
        f"ifconfig {interface}", shell=True, capture_output=True, text=True
    )
    ips = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", result.stdout)
    if ips:
        ipv4 = ips.group(1)
        logging.debug(f"Found IPv4: {ipv4}")
        return ipv4
    logging.warning(f"No IPv4 found for interface {interface}")
    return None

def get_public_ipv4():
    logging.debug("Fetching public IPv4 address from https://ipv4.seeip.org")
    try:
        return requests.get("https://ipv4.seeip.org", timeout=10).text.strip()
    except Exception as e:
        logging.error(f"Failed to fetch public IPv4: {e}")
        return None

def get_ipv6():
    logging.debug("Fetching public IPv6 address from https://ipv6.seeip.org")
    try:
        return requests.get("https://ipv6.seeip.org", timeout=10).text.strip()
    except Exception as e:
        logging.error(f"Failed to fetch IPv6: {e}")
        return None

# Get current DNS records from Vultr
logging.debug(f"Fetching DNS records for domain: {domain}")
response = requests.get(
    f"https://api.vultr.com/v2/domains/{domain}/records?per_page=500",
    headers={"Authorization": f"Bearer {api_key}"}
)

if "is not authorized" in response.text:
    logging.error("Authorization error. Check your API key and permissions.")
    sys.exit(1)

try:
    response.raise_for_status()
    raw_records = response.json()
except Exception as e:
    logging.error(f"Failed to load records from Vultr: {str(e)}")
    sys.exit(1)

vultr_records = raw_records.get("records", [])
changes = []

# Iterate over the dynamic records from the config
for record_config in dynamic_records:
    name = record_config["name"]
    interfaces = record_config["interfaces"]
    mode = record_config.get("mode", "local")  # Default to 'local' if not specified

    logging.info(f"Processing record for subdomain: {name}, mode: {mode}")
    
    current_ipv4 = None
    if mode == "local":
        for iface in interfaces:
            current_ipv4 = get_ipv4_from_interface(iface)
            if current_ipv4:
                break
    elif mode == "internet":
        current_ipv4 = get_public_ipv4()

    current_ipv6 = get_ipv6()  # Always try to fetch IPv6, even for local mode

    logging.debug(f"Fetched IPv4: {current_ipv4}, IPv6: {current_ipv6}")

    # Check and compare records for A and AAAA types
    for record in vultr_records:
        if record["name"] != name:
            continue

        if record["type"] == "A" and current_ipv4 and record["data"] != current_ipv4:
            logging.info(f"IPv4 mismatch for {name}: {record['data']} != {current_ipv4}")
            changes.append({
                "id": record["id"],
                "type": "A",
                "name": name,
                "new_ip": current_ipv4
            })

        elif record["type"] == "AAAA" and current_ipv6 and record["data"] != current_ipv6:
            logging.info(f"IPv6 mismatch for {name}: {record['data']} != {current_ipv6}")
            changes.append({
                "id": record["id"],
                "type": "AAAA",
                "name": name,
                "new_ip": current_ipv6
            })

if not changes:
    logging.info("No IP changes detected. Records are up to date.")
    sys.exit(0)

logging.info("Updating the following records:")
for change in changes:
    logging.info(f"Updating {change['name']}/{change['type']} → {change['new_ip']}")
    payload = {"data": change["new_ip"]}
    update_response = requests.patch(
        f"https://api.vultr.com/v2/domains/{domain}/records/{change['id']}",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"}
    )
    if "error" in update_response.text:
        logging.error(f"Error updating record {change['id']}: {update_response.text}")
    else:
        logging.info(f"✅ Updated {change['name']} ({change['type']}) to {change['new_ip']}")
