"""Client-process network guard. Does not control the separate Ollama daemon."""
import ipaddress
import socket
from contextlib import ExitStack, contextmanager
from unittest.mock import patch


def is_loopback(host):
    if host=='localhost':return True
    try:return ipaddress.ip_address(str(host).split('%')[0]).is_loopback
    except ValueError:return False


@contextmanager
def loopback_only():
    connect=socket.socket.connect;connect_ex=socket.socket.connect_ex;getaddrinfo=socket.getaddrinfo
    def check(address):
        if isinstance(address,tuple) and not is_loopback(address[0]):
            raise PermissionError('Offline client guard blocked a non-loopback connection.')
    def guarded_connect(sock,address):check(address);return connect(sock,address)
    def guarded_connect_ex(sock,address):check(address);return connect_ex(sock,address)
    def guarded_dns(host,*args,**kwargs):
        if host is not None and not is_loopback(host):raise PermissionError('Offline client guard blocked external DNS.')
        return getaddrinfo(host,*args,**kwargs)
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket,'connect',guarded_connect))
        stack.enter_context(patch.object(socket.socket,'connect_ex',guarded_connect_ex))
        stack.enter_context(patch.object(socket,'getaddrinfo',guarded_dns))
        yield


def active_network_interfaces():
    try:
        import psutil
        addresses=psutil.net_if_addrs();stats=psutil.net_if_stats();active=[]
        for name,values in addresses.items():
            if not stats.get(name) or not stats[name].isup:continue
            if any(v.family in (socket.AF_INET,socket.AF_INET6) and not is_loopback(v.address) for v in values):active.append(name)
        return active
    except (ImportError, OSError):return None
