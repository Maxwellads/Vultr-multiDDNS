# Vultr-multiDDNS
Dynamically update IPv4/v6 addresses of subdomains by specified matches

# Modes
## local
`local` mode supports acquring IP address from `ifconfig`, so that the user can always access an instance in the Intranet environments where they cannot have a static IP address. For example, if there is a dedicated SQL server in the office, but specifying a static IP is impossible due to various reasons, they can grab the Intranet IP address and update the DNS record, making it always possible to access the SQL server by domain.
## inet
`inet` mode supports acquring IP address from public Internet servers, assuming that the user has a public IP(but the IP is not static).

# Configuration sample
```config.json
{
  "api_key": "MY_API_KEY",
  "domain": "MY_DOMAIN",
  "dynamic_records": [
    {
      "name": "www",
      "interfaces": ["eth0"],
      "mode": "local"
    },
    {
      "name": "www2",
      "mode": "inet"
    }
  ]
}
```

# How to use
Clone this repo:
```
git clone https://github.com/Maxwellads/Vultr-multiDDNS
```
And use it with systemd, cron or whatever you like :)

Please note that Windows is currently not supported, which would be implemented later.
