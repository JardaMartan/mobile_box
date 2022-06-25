# connection to the codec
# IP address can be determined from CDP by a restconf query to the router
CODEC_CONFIG = {
    "ip": "192.168.1.10",
    "username": "roomcontrol",
    "password": "roomcontrol123"
}
# router access information. The IP address is either a default gateway, or
# if TESTING["active"] is True, it's set to TESTING["router_ip"]
ROUTER_CONFIG = {
    "username": "admin",
    "password": "admin"
}
TESTING = {
    "active": False,
    "router_ip": "10.62.8.34"
}
