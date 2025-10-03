import netifaces
import socket
import time


def get_broadcast_addresses():
    """
    Returns a list of tuples (interface_name, ip, netmask, broadcast) for all active IPv4 interfaces
    with valid broadcast addresses (excluding loopback and link-local).
    """
    results = {}
    for iface in netifaces.interfaces():
        try:
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET not in addrs:
                continue
            ipv4_info = addrs[netifaces.AF_INET][0]
            ip = ipv4_info.get("addr")
            netmask = ipv4_info.get("netmask")
            broadcast = ipv4_info.get("broadcast")

            # Filter out loopback and link-local IPs
            if ip is None or ip.startswith("127.") or ip.startswith("169.254."):
                continue

            if broadcast is None:
                continue

            results[iface] = {}
            results[iface]["ip"] = ip
            results[iface]["netmask"] = netmask
            results[iface]["broadcast"] = broadcast
        except Exception:
            continue
    return results


for iface, data in get_broadcast_addresses().items():
    print(iface, data["broadcast"])
# DEFAULT_UDP_PORT = 15733
# timeout = 10

# udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# udp.bind(("", DEFAULT_UDP_PORT))
# udp.settimeout(timeout)
# rooms = []
# start = time.time()
# while time.time() - start < timeout:
#     try:
#         data, addr = udp.recvfrom(1024)
#         msg = data.decode()
#         if msg.startswith("ROOM_HOST:"):
#             print(msg)
#     except socket.timeout:
#         break
#     except Exception:
#         continue
