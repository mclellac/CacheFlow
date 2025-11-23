import logging
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.connectionpool import HTTPSConnectionPool, HTTPConnectionPool
from urllib3.connection import HTTPSConnection, HTTPConnection

log = logging.getLogger(__name__)

class CustomHTTPSConnectionPool(HTTPSConnectionPool):
    def __init__(self, host, port=None, target_ip=None, **kwargs):
        self.target_ip = target_ip
        super().__init__(host, port, **kwargs)

    def _new_conn(self):
        self.num_connections += 1
        actual_host = self.target_ip if self.target_ip else self.host

        log.debug(f"Creating HTTPS connection to {actual_host} for {self.host}")
        return HTTPSConnection(
            host=actual_host,
            port=self.port,
            timeout=self.timeout.clone().connect_timeout,
            server_hostname=self.host,
            **self.conn_kw
        )

class CustomHTTPConnectionPool(HTTPConnectionPool):
    def __init__(self, host, port=None, target_ip=None, **kwargs):
        self.target_ip = target_ip
        super().__init__(host, port, **kwargs)

    def _new_conn(self):
        self.num_connections += 1
        actual_host = self.target_ip if self.target_ip else self.host

        log.debug(f"Creating HTTP connection to {actual_host} for {self.host}")
        return HTTPConnection(
            host=actual_host,
            port=self.port,
            timeout=self.timeout.clone().connect_timeout,
            **self.conn_kw
        )

class CustomPoolManager(PoolManager):
    def __init__(self, dns_map=None, **kwargs):
        self.dns_map = dns_map or {}
        super().__init__(**kwargs)

    def _new_pool(self, scheme, host, port, request_context=None):
        target_ip = self.dns_map.get(host)
        if target_ip:
            log.debug(f"Using custom IP {target_ip} for host {host} (scheme: {scheme})")

        if scheme == 'https':
            return CustomHTTPSConnectionPool(host, port, target_ip=target_ip, **self.connection_pool_kw)
        if scheme == 'http':
            return CustomHTTPConnectionPool(host, port, target_ip=target_ip, **self.connection_pool_kw)
        return super()._new_pool(scheme, host, port, request_context)

class DNSAdapter(HTTPAdapter):
    """
    A custom requests HTTPAdapter that allows forcing a specific IP for a hostname
    while preserving the hostname for SNI and SSL verification.
    """
    def __init__(self, dns_map=None, **kwargs):
        self.dns_map = dns_map or {}
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = CustomPoolManager(
            dns_map=self.dns_map,
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            strict=True
        )
