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
        "header_color": "rgba(0, 122, 204, 1.0)",  # Blue for CDN
        "body_color": "rgba(0, 122, 204, 0.8)",
        "text_color": "rgba(255, 255, 255, 1.0)",
        "added_text_color": "rgba(46, 204, 113, 1.0)",  # Green
        "removed_text_color": "rgba(231, 76, 60, 1.0)",  # Red
        "modified_text_color": "rgba(243, 156, 18, 1.0)",  # Orange
        "custom_headers": {
            "Pragma": "akamai-x-get-request-id, akamai-x-cache-on, "
            "akamai-x-cache-key"
        },
        "host_overrides": [],
        "path_match_only": [],
        "routing_rules": [],
    },
    {
        "name": "Infra_Cache",
        "description": "Varnish (Internal Cache Layer)",
        "layer_type": "Cache Proxy",
        "provider": "Varnish",
        "host_url": "http://cache.examplefarm.com",
        "default_backend_host": "",
        "default_backend_host_header": "",
        "header_color": "rgba(22, 160, 133, 1.0)",  # Teal/Green for Proxy
        "body_color": "rgba(22, 160, 133, 0.8)",
        "text_color": "rgba(255, 255, 255, 1.0)",
        "added_text_color": "rgba(46, 204, 113, 1.0)",
        "removed_text_color": "rgba(231, 76, 60, 1.0)",
        "modified_text_color": "rgba(243, 156, 18, 1.0)",
        "custom_headers": {
            "X-Varnish-Debug": "true",
            "X-Origin-Auth": "secret-token-123",
        },
        "host_overrides": [
            {
                "path_pattern": "/api/*",
                "host_header": "api-internal.example.com",
            }
        ],
        "path_match_only": [],
        "routing_rules": [],
    },
]


class ConfigManager:
    """Handles all GSettings interactions for layer configurations."""

    def __init__(self, settings):
        """Initializes the ConfigManager.

        Args:
            settings: The GSettings object for the application.
        """
        self.settings = settings
        log.debug("ConfigManager initialized.")

    def get_configurations(self):
        """Returns the list of configurations.

        If no configurations are found, a default configuration is created and
        returned.

        Returns:
            A list of dictionaries, where each dictionary represents a
            configuration.
        """
        val = self.settings.get_value("configurations")
        configs = val.unpack()
        if not configs:
            # If empty, create a default one
            default_id = str(uuid.uuid4())
            default_config_dict = {
                "id": GLib.Variant("s", default_id),
                "name": GLib.Variant("s", "Example Domain"),
                "layers": self._pack_layers(DEFAULT_LAYERS),
            }

            self.settings.set_value(
                "configurations", GLib.Variant("aa{sv}", [default_config_dict])
            )
            self.settings.set_string("active-config-id", default_id)
            return [
                {
                    "id": default_id,
                    "name": "Example Domain",
                    "entry_point": "www.example.com",
                    "layers": DEFAULT_LAYERS,
                }
            ]

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
            unpacked_c["entry_point"] = unpacked_c.get("name", "")
            unpacked_configs.append(unpacked_c)

        return unpacked_configs

    def get_configuration(self, conf_id):
        """Returns a single configuration by ID.

        Args:
            conf_id: The ID of the configuration to retrieve.

        Returns:
            A dictionary representing the configuration, or None if not found.
        """
        configs = self.get_configurations()
        for c in configs:
            if c["id"] == conf_id:
                return c
        return None

    def add_configuration(self, name, entry_point, layers=None):
        """Adds a new configuration.

        Args:
            name: The name of the new configuration.
            entry_point: The entry point for the new configuration.
            layers: An optional list of layers for the new configuration.

        Returns:
            The ID of the newly created configuration.
        """
        configs = self.get_configurations()
        new_id = str(uuid.uuid4())
        new_conf = {
            "id": new_id,
            "name": name,
            "entry_point": entry_point,
            "layers": layers if layers else [],
        }
        configs.append(new_conf)
        self._save_configs(configs)
        return new_id

    def delete_configuration(self, conf_id):
        """Deletes a configuration.

        Args:
            conf_id: The ID of the configuration to delete.
        """
        configs = self.get_configurations()
        configs = [c for c in configs if c["id"] != conf_id]
        self._save_configs(configs)

    def save_configuration(self, conf_id, data):
        """Updates a configuration.

        Args:
            conf_id: The ID of the configuration to update.
            data: A dictionary containing the new configuration data.
        """
        configs = self.get_configurations()
        for i, c in enumerate(configs):
            if c["id"] == conf_id:
                configs[i] = data
                break
        self._save_configs(configs)

    def _save_configs(self, configs):
        """Packs and saves a list of configurations to GSettings.

        Args:
            configs: A list of dictionaries, where each dictionary represents a
                configuration.
        """
        builder = GLib.VariantBuilder.new(GLib.VariantType.new("aa{sv}"))
        for c_data in configs:
            dict_builder = GLib.VariantBuilder.new(
                GLib.VariantType.new("a{sv}")
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "id",
                        GLib.Variant("s", c_data.get("id", str(uuid.uuid4()))),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}", ("name", GLib.Variant("s", c_data.get("name", "")))
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    ("layers", self._pack_layers(c_data.get("layers", []))),
                )
            )
            builder.add_value(dict_builder.end())

        try:
            self.settings.set_value("configurations", builder.end())
            log.info("Configurations saved successfully.")
        except TypeError as e:
            log.error(
                "TypeError saving configurations. "
                "This indicates a data mismatch: %s",
                e,
            )
        except Exception as e:
            log.error(
                "An unexpected error occurred while saving configurations: %s",
                e,
            )

    def _pack_layers(self, layers_data):
        """Packs a list of Python layer dicts into a GLib.Variant.

        Args:
            layers_data: A list of dictionaries, where each dictionary
                represents a layer.

        Returns:
            A GLib.Variant of type 'aa{sv}' containing the packed layer data.
        """
        builder = GLib.VariantBuilder.new(GLib.VariantType.new("aa{sv}"))
        for l_data in layers_data:
            dict_builder = GLib.VariantBuilder.new(
                GLib.VariantType.new("a{sv}")
            )
            # Pack all known keys, providing defaults for missing ones
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}", ("name", GLib.Variant("s", l_data.get("name", "")))
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "description",
                        GLib.Variant("s", l_data.get("description", "")),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "layer_type",
                        GLib.Variant("s", l_data.get("layer_type", "CDN")),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "provider",
                        GLib.Variant("s", l_data.get("provider", "Akamai")),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "host_url",
                        GLib.Variant("s", l_data.get("host_url", "")),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "default_backend_host",
                        GLib.Variant(
                            "s", l_data.get("default_backend_host", "")
                        ),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "default_backend_host_header",
                        GLib.Variant(
                            "s", l_data.get("default_backend_host_header", "")
                        ),
                    ),
                )
            )

            # Color settings
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "header_color",
                        GLib.Variant(
                            "s", l_data.get("header_color", "rgba(0,0,0,0)")
                        ),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "body_color",
                        GLib.Variant(
                            "s", l_data.get("body_color", "rgba(0,0,0,0)")
                        ),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "text_color",
                        GLib.Variant(
                            "s", l_data.get("text_color", "rgba(0,0,0,0)")
                        ),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "added_text_color",
                        GLib.Variant(
                            "s",
                            l_data.get("added_text_color", "rgba(0,0,0,0)"),
                        ),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "removed_text_color",
                        GLib.Variant(
                            "s",
                            l_data.get("removed_text_color", "rgba(0,0,0,0)"),
                        ),
                    ),
                )
            )
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "modified_text_color",
                        GLib.Variant(
                            "s",
                            l_data.get("modified_text_color", "rgba(0,0,0,0)"),
                        ),
                    ),
                )
            )

            # Complex types
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "custom_headers",
                        GLib.Variant(
                            "a{ss}", l_data.get("custom_headers", {})
                        ),
                    ),
                )
            )

            # Build 'host_overrides' (aa{ss})
            overrides_builder = GLib.VariantBuilder.new(
                GLib.VariantType.new("aa{ss}")
            )
            for override in l_data.get("host_overrides", []):
                overrides_builder.add_value(GLib.Variant("a{ss}", override))
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}", ("host_overrides", overrides_builder.end())
                )
            )

            dict_builder.add_value(
                GLib.Variant(
                    "{sv}",
                    (
                        "path_match_only",
                        GLib.Variant("as", l_data.get("path_match_only", [])),
                    ),
                )
            )

            # Build 'routing_rules' (aa{ss})
            rules_builder = GLib.VariantBuilder.new(
                GLib.VariantType.new("aa{ss}")
            )
            for rule in l_data.get("routing_rules", []):
                rules_builder.add_value(GLib.Variant("a{ss}", rule))
            dict_builder.add_value(
                GLib.Variant("{sv}", ("routing_rules", rules_builder.end()))
            )

            # Deprecated, pack empty for compatibility if needed
            dict_builder.add_value(
                GLib.Variant(
                    "{sv}", ("varnish_backends", GLib.Variant("aa{sv}", []))
                )
            )

            # Build 'nodes' (aa{sv}) for multiple proxies/backends
            nodes_builder = GLib.VariantBuilder.new(
                GLib.VariantType.new("aa{sv}")
            )
            for node in l_data.get("nodes", []):
                node_dict_builder = GLib.VariantBuilder.new(
                    GLib.VariantType.new("a{sv}")
                )
                node_dict_builder.add_value(
                    GLib.Variant(
                        "{sv}", ("name", GLib.Variant("s", node.get("name", "")))
                    )
                )
                node_dict_builder.add_value(
                    GLib.Variant(
                        "{sv}", ("host_url", GLib.Variant("s", node.get("host_url", "")))
                    )
                )
                node_dict_builder.add_value(
                    GLib.Variant(
                        "{sv}", ("match_header", GLib.Variant("s", node.get("match_header", "")))
                    )
                )
                node_dict_builder.add_value(
                    GLib.Variant(
                        "{sv}", ("match_value", GLib.Variant("s", node.get("match_value", "")))
                    )
                )
                node_dict_builder.add_value(
                    GLib.Variant(
                        "{sv}", ("provider", GLib.Variant("s", node.get("provider", "")))
                    )
                )
                node_dict_builder.add_value(
                    GLib.Variant(
                        "{sv}", ("header_color", GLib.Variant("s", node.get("header_color", "rgba(0,0,0,0)")))
                    )
                )
                node_dict_builder.add_value(
                    GLib.Variant(
                        "{sv}", ("body_color", GLib.Variant("s", node.get("body_color", "rgba(0,0,0,0)")))
                    )
                )
                nodes_builder.add_value(node_dict_builder.end())

            dict_builder.add_value(
                GLib.Variant(
                    "{sv}", ("nodes", nodes_builder.end())
                )
            )

            builder.add_value(dict_builder.end())

        return builder.end()
