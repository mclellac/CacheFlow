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
        "header_color": "rgba(128, 0, 128, 0.8)",
        "body_color": "rgba(128, 0, 128, 0.6)",
        "unchanged_text_color": "rgba(255, 255, 255, 1.0)",
        "added_text_color": "rgba(173, 255, 47, 1.0)",
        "removed_text_color": "rgba(255, 99, 71, 1.0)",
        "modified_text_color": "rgba(255, 215, 0, 1.0)",
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
        "header_color": "rgba(0, 128, 128, 0.8)",
        "body_color": "rgba(0, 128, 128, 0.6)",
        "unchanged_text_color": "rgba(255, 255, 255, 1.0)",
        "added_text_color": "rgba(173, 255, 47, 1.0)",
        "removed_text_color": "rgba(255, 99, 71, 1.0)",
        "modified_text_color": "rgba(255, 215, 0, 1.0)",
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
            default_config_dict = {
                'id': GLib.Variant('s', default_id),
                'name': GLib.Variant('s', 'Example Domain'),
                'layers': self._pack_layers(DEFAULT_LAYERS)
            }

            self.settings.set_value('configurations', GLib.Variant('aa{sv}', [default_config_dict]))
            self.settings.set_string('active-config-id', default_id)
            return [{
                'id': default_id,
                'name': 'Example Domain',
                'entry_point': 'www.example.com',
                'layers': DEFAULT_LAYERS
            }]

        # Recursively unpack variants into python types
        unpacked_configs = []
        for c in configs:
            unpacked_c = {}
            for k, v in c.items():
                if isinstance(v, GLib.Variant):
                    unpacked_c[k] = v.unpack()
                else:
                    unpacked_c[k] = v

            # entry_point is deprecated, use name (Domain Name)
            unpacked_c['entry_point'] = unpacked_c.get('name', '')
            unpacked_configs.append(unpacked_c)

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
        builder = GLib.VariantBuilder.new(GLib.VariantType.new('aa{sv}'))
        for c_data in configs:
            dict_builder = GLib.VariantBuilder.new(GLib.VariantType.new('a{sv}'))
            dict_builder.add_value(GLib.Variant('{sv}', ('id', GLib.Variant('s', c_data.get('id', str(uuid.uuid4()))))))
            dict_builder.add_value(GLib.Variant('{sv}', ('name', GLib.Variant('s', c_data.get('name', '')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('layers', self._pack_layers(c_data.get('layers', [])))))
            builder.add_value(dict_builder.end())

        try:
            self.settings.set_value('configurations', builder.end())
            log.info("Configurations saved successfully.")
        except TypeError as e:
            log.error("TypeError saving configurations. "
                      "This indicates a data mismatch: %s", e)
        except Exception as e:
            log.error("An unexpected error occurred while saving configurations: %s",
                      e)

    def _pack_layers(self, layers_data):
        """Packs a list of Python layer dicts into a GLib.Variant ('aa{sv}')."""
        builder = GLib.VariantBuilder.new(GLib.VariantType.new('aa{sv}'))
        for l_data in layers_data:
            dict_builder = GLib.VariantBuilder.new(GLib.VariantType.new('a{sv}'))
            # Pack all known keys, providing defaults for missing ones
            dict_builder.add_value(GLib.Variant('{sv}', ('name', GLib.Variant('s', l_data.get('name', '')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('description', GLib.Variant('s', l_data.get('description', '')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('layer_type', GLib.Variant('s', l_data.get('layer_type', 'CDN')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('provider', GLib.Variant('s', l_data.get('provider', 'Akamai')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('host_url', GLib.Variant('s', l_data.get('host_url', '')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('default_backend_host', GLib.Variant('s', l_data.get('default_backend_host', '')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('default_backend_host_header', GLib.Variant('s', l_data.get('default_backend_host_header', '')))))

            # Color settings
            dict_builder.add_value(GLib.Variant('{sv}', ('header_color', GLib.Variant('s', l_data.get('header_color', 'rgba(0,0,0,0)')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('body_color', GLib.Variant('s', l_data.get('body_color', 'rgba(0,0,0,0)')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('text_color', GLib.Variant('s', l_data.get('text_color', 'rgba(0,0,0,0)')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('added_text_color', GLib.Variant('s', l_data.get('added_text_color', 'rgba(0,0,0,0)')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('removed_text_color', GLib.Variant('s', l_data.get('removed_text_color', 'rgba(0,0,0,0)')))))
            dict_builder.add_value(GLib.Variant('{sv}', ('modified_text_color', GLib.Variant('s', l_data.get('modified_text_color', 'rgba(0,0,0,0)')))))

            # Complex types
            dict_builder.add_value(GLib.Variant('{sv}', ('custom_headers', GLib.Variant('a{ss}', l_data.get('custom_headers', {})))))

            # Build 'host_overrides' (aa{ss})
            overrides_builder = GLib.VariantBuilder.new(GLib.VariantType.new('aa{ss}'))
            for override in l_data.get('host_overrides', []):
                overrides_builder.add_value(GLib.Variant('a{ss}', override))
            dict_builder.add_value(GLib.Variant('{sv}', ('host_overrides', overrides_builder.end())))

            dict_builder.add_value(GLib.Variant('{sv}', ('path_match_only', GLib.Variant('as', l_data.get('path_match_only', [])))))

            # Build 'routing_rules' (aa{ss})
            rules_builder = GLib.VariantBuilder.new(GLib.VariantType.new('aa{ss}'))
            for rule in l_data.get('routing_rules', []):
                rules_builder.add_value(GLib.Variant('a{ss}', rule))
            dict_builder.add_value(GLib.Variant('{sv}', ('routing_rules', rules_builder.end())))

            # Deprecated, pack empty for compatibility if needed
            dict_builder.add_value(GLib.Variant('{sv}', ('varnish_backends', GLib.Variant('aa{sv}', []))))

            builder.add_value(dict_builder.end())

        return builder.end()
