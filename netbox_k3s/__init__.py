"""netbox-k3s — a NetBox plugin adding a dedicated Kubernetes section."""

from netbox.plugins import PluginConfig

__version__ = "0.1.0"


class NetBoxK3sConfig(PluginConfig):
    name = "netbox_k3s"
    verbose_name = "Kubernetes (k3s)"
    description = "Dedicated Kubernetes section: clusters, namespaces, pods and services."
    version = __version__
    base_url = "k3s"
    min_version = "4.2.0"
    max_version = "4.99.99"
    # Plugin-level settings, overridable via PLUGINS_CONFIG in configuration.py.
    default_settings = {
        # If True, the top-level menu gets its own icon and section.
        "top_level_menu": True,
    }


config = NetBoxK3sConfig
