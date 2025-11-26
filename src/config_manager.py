"""
This module handles the application preferences, including the PreferencesWindow
and configuration management via GSettings.
"""

import logging
import uuid
from gi.repository import GLib

log = logging.getLogger(__name__)

DEFAULT_LAYERS = [
    {
        "name": "CDN_Edge",
        "description": "Akamai (External View)",
        "layer_type": "CDN",
        "provider": "Akamai",
        "host_url": "https://www.example.com",
        "default_backend_host": "cache.examplefarm.com",
        "default_backend_host_header": "origin.example.com",
        "custom_headers": {
            "Pragma": "akamai-x-get-request-id, akamai-x-cache-on, akamai-x-cache-key"
        },
        "host_overrides": [],
        "path_match_only": [],
        "routing_rules": []
    },
    {
        "name": "Infra_Cache",
        "description": "Varnish (Internal Cache Layer)",
        "layer_type": "Cache Proxy",
        "provider": "Varnish",
        "host_url": "http://cache.examplefarm.com",
        "default_backend_host": "",
        "default_backend_host_header": "",
        "custom_headers": {
            "X-Varnish-Debug": "true",
            "X-Origin-Auth": "secret-token-123"
        },
        "host_overrides": [
            {
                "path_pattern": "/api/*",
                "host_header": "api-internal.example.com"
            }
        ],
        "path_match_only": [],
        "routing_rules": []
    }
]


class ConfigManager:
    """Handles all GSettings interactions for layer configurations."""

    def __init__(self, settings):
        self.settings = settings
        log.debug("ConfigManager initialized.")

    def get_configurations(self):
        """Returns the list of configurations (list of dicts)."""
        val = self.settings.get_value('configurations')
        configs = val.unpack()
        if not configs:
            # If empty, create a default one
            default_id = str(uuid.uuid4())
            default_config = {
                'id': GLib.Variant('s', default_id),
                'name': GLib.Variant('s', 'Example Domain'),
                'entry_point': GLib.Variant('s', 'www.example.com'),
                'layers': self._pack_layers(DEFAULT_LAYERS)
            }
            self.settings.set_value('configurations', GLib.Variant('aa{sv}', [default_config]))
            self.settings.set_string('active-config-id', default_id)
            return [{
                'id': default_id,
                'name': 'Example Domain',
                'entry_point': 'www.example.com',
                'layers': DEFAULT_LAYERS
            }]

        # Unpack layers recursively
        unpacked_configs = []
        for c in configs:
            c_dict = dict(c) # c is a dict from aa{sv}
            layers_variant = c_dict.get('layers')
            if isinstance(layers_variant, GLib.Variant):
                layers = layers_variant.unpack()
            else:
                layers = layers_variant if layers_variant else []

            # entry_point is deprecated/removed, use name (Domain Name)
            unpacked_configs.append({
                'id': c_dict.get('id', ''),
                'name': c_dict.get('name', ''),
                'entry_point': c_dict.get('name', ''),
                'layers': layers
            })
        return unpacked_configs

    def get_configuration(self, conf_id):
        """Returns a single configuration by ID."""
        configs = self.get_configurations()
        for c in configs:
            if c['id'] == conf_id:
                return c
        return None

    def add_configuration(self, name, entry_point, layers=None):
        """Adds a new configuration."""
        configs = self.get_configurations()
        new_id = str(uuid.uuid4())
        new_conf = {
            'id': new_id,
            'name': name,
            'entry_point': entry_point,
            'layers': layers if layers else []
        }
        configs.append(new_conf)
        self._save_configs(configs)
        return new_id

    def delete_configuration(self, conf_id):
        """Deletes a configuration."""
        configs = self.get_configurations()
        configs = [c for c in configs if c['id'] != conf_id]
        self._save_configs(configs)

    def save_configuration(self, conf_id, data):
        """Updates a configuration."""
        configs = self.get_configurations()
        for i, c in enumerate(configs):
            if c['id'] == conf_id:
                configs[i] = data
                break
        self._save_configs(configs)

    def _save_configs(self, configs):
        """ packs and saves list of configs to GSettings."""
        variant_data = []
        for c in configs:
            c_dict = {
                'id': GLib.Variant('s', c['id']),
                'name': GLib.Variant('s', c['name']),
                # entry_point is duplicate of name (Domain Name), so we don't save it anymore
                'layers': self._pack_layers(c['layers'])
            }
            variant_data.append(c_dict)

        try:
            self.settings.set_value('configurations', GLib.Variant('aa{sv}', variant_data))
        except Exception as e:
            log.error("Error saving configurations: %s", e)

    def _pack_layers(self, layers_data):
        """Packs list of layer dicts into Variant."""
        variant_data = []
        for l_data in layers_data:
            layer_dict = {
                'name': GLib.Variant('s', l_data.get('name', '')),
                'description': GLib.Variant('s', l_data.get('description', '')),
                'layer_type': GLib.Variant('s', l_data.get('layer_type', 'CDN')),
                'provider': GLib.Variant('s', l_data.get('provider', 'Akamai')),
                'host_url': GLib.Variant('s', l_data.get('host_url', '')),
                'default_backend_host': GLib.Variant('s', l_data.get('default_backend_host', '')),
                'default_backend_host_header': GLib.Variant('s', l_data.get('default_backend_host_header', '')),
                'header_color': GLib.Variant('s', l_data.get('header_color', '')),
                'body_color': GLib.Variant('s', l_data.get('body_color', '')),
                'text_color': GLib.Variant('s', l_data.get('text_color', '')),
                'unchanged_text_color': GLib.Variant('s', l_data.get('unchanged_text_color', '')),
                'added_text_color': GLib.Variant('s', l_data.get('added_text_color', '')),
                'removed_text_color': GLib.Variant('s', l_data.get('removed_text_color', '')),
                'modified_text_color': GLib.Variant('s', l_data.get('modified_text_color', '')),
                'custom_headers': GLib.Variant('a{ss}', l_data.get('custom_headers', {})),
                'host_overrides': GLib.Variant('aa{ss}', l_data.get('host_overrides', [])),
                'path_match_only': GLib.Variant('as', l_data.get('path_match_only', [])),
                'routing_rules': GLib.Variant('aa{ss}', l_data.get('routing_rules', []))
            }
            variant_data.append(layer_dict)

        return GLib.Variant('aa{sv}', variant_data)
