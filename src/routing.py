"""
Routing logic for CacheFlow.
"""

import fnmatch
import re
import logging
from typing import Dict, Any, Optional, Tuple

log = logging.getLogger(__name__)

class RouteCalculator:
    """Calculates the next hop in the request chain."""

    @staticmethod
    def calculate_next_hop(layer_config: Dict[str, Any],
                           target_path: str) -> Tuple[Optional[str], str, Optional[str]]:
        """
        Determines the next base URL, path, and host header.

        Returns:
            (next_base, next_path, next_host_header)
        """
        next_base = None
        next_path = target_path
        next_host_header = None

        # Check Routing Rules
        routing_rules = layer_config.get('routing_rules', [])
        rule_matched = False

        for rule in routing_rules:
            path_match = rule.get('path_match')
            is_match = False
            if path_match:
                is_match = fnmatch.fnmatch(target_path, path_match)

            if is_match:
                log.info("Routing rule matched: %s", path_match)
                backend_host = rule.get('backend_host')
                path_rewrite = rule.get('path_rewrite')
                backend_host_header = rule.get('backend_host_header')

                if backend_host:
                    if not backend_host.startswith('http'):
                        next_base = f"https://{backend_host}"
                    else:
                        next_base = backend_host

                if backend_host_header:
                    next_host_header = backend_host_header

                if path_rewrite and path_rewrite.startswith('s'):
                    try:
                        parts = path_rewrite.split(path_rewrite[1])
                        if len(parts) >= 3:
                            pattern = parts[1]
                            repl = parts[2]
                            next_path = re.sub(pattern, repl, target_path)
                            log.debug("Rewrote path '%s' to '%s'", target_path, next_path)
                    except Exception as e: # pylint: disable=broad-exception-caught
                        log.error("Failed to parse rewrite rule: %s", e)

                rule_matched = True
                break

        if not rule_matched:
            default_host = layer_config.get('default_backend_host')
            if default_host:
                log.info("Using default backend: %s", default_host)
                if not default_host.startswith('http'):
                    next_base = f"https://{default_host}"
                else:
                    next_base = default_host

                next_host_header = layer_config.get('default_backend_host_header')

        return next_base, next_path, next_host_header
