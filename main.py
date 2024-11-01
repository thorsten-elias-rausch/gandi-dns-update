import json
import traceback
import requests
import sys

from datetime import datetime, timezone
from ipaddress import ip_address, IPv4Address
from dataclasses import dataclass


def main() -> bool:
    argv = sys.argv
    if len(argv) != 2:
        log(f"Incorrect number of arguments. Expected 1, received {len(argv) - 1}.")
        return False
    path = argv[1]

    config = load_config(path)
    if config is None:
        return False

    address = get_ip_address()
    if address is None:
        return False

    if not update_domain(address, config):
        return False

    return True


@dataclass
class Config:
    pat: str
    domain: str
    ttl: int

    def is_valid(self) -> bool:
        if not isinstance(self.pat, str):
            log("Field 'pat' is not a string.")
            return False
        if not isinstance(self.domain, str):
            log("Field 'domain' is not a string.")
            return False
        if not isinstance(self.ttl, int):
            log("Field 'ttl' is not an integer.")
            return False
        if self.ttl < 300:
            log("Field 'ttl' must be greater or equal than 300.")
            return False
        return True


def load_config(path: str) -> Config | None:
    log(f"Loading config at path '{path}'...")
    try:
        with open(path) as file:
            data = json.load(file)
        config = Config(**data)
    except Exception as exception:
        log(f"Failed to load config: {exception}")
        traceback.print_exc()
        return None

    if not config.is_valid():
        log("Config is invalid.")
        return None

    return config


def get_ip_address() -> IPv4Address | None:
    url = "https://api.ipify.org"
    log(f"Requesting public IP address from '{url}'...")

    try:
        response = requests.get(url)
    except Exception as exception:
        log(f"Failed to reach public IP address service: {exception}")
        traceback.print_exc()
        return None

    if response.status_code != 200:
        log(f"Failed to retrieve public IP address. HTTP status: '{response.status_code}', text: '{response.text}'.")
        return None

    try:
        address = ip_address(response.text)
    except Exception as exception:
        log(f"Retrieved value '{response.text}' is not a valid IP address: {exception}")
        traceback.print_exc()
        return None

    if not isinstance(address, IPv4Address):
        log(f"Expected address '{address}' to be an IPv4Address, but got '{type(address)}'.")

    log(f"Retrieved public IP address '{address}'.")
    return address


def update_domain(address: IPv4Address, config: Config) -> bool:
    url = f"https://api.gandi.net/v5/livedns/domains/{config.domain}/records/@/A"
    log(f"Updating DNS record at '{url}' with address '{address}'...")

    address_string = str(address)

    try:
        response = requests.put(url, headers={
            "Authorization": f"Bearer {config.pat}"
        }, json={
            "rrset_ttl": config.ttl,
            "rrset_values": [address_string]
        })
    except Exception as exception:
        log(f"Failed to reach DNS registrar service: {exception}")
        traceback.print_exc()
        return False

    if response.status_code != 201:
        log(f"Failed to update DNS entry. HTTP status: '{response.status_code}', text: '{response.text}'.")
        return False

    log(f"DNS entry updated.")
    return True


def log(line):
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"[{timestamp}] {line}"
    print(line)


if __name__ == "__main__":
    log("Running script...")
    if main():
        log("Script succeeded.")
        exit(0)
    else:
        log("Script failed.")
        exit(1)
