"""Navigation menu — a dedicated top-level 'Kubernetes' section.

When the ``top_level_menu`` plugin setting is True (default) the items appear as
their own top-level menu. When False they are grouped under NetBox's generic
"Plugins" menu via ``menu_items``.
"""

from django.conf import settings

from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem


def _add_button(model):
    return [
        PluginMenuButton(
            link=f"plugins:netbox_k3s:{model}_add",
            title="Add",
            icon_class="mdi mdi-plus-thick",
        )
    ]


cluster_item = PluginMenuItem(
    link="plugins:netbox_k3s:k3scluster_list",
    link_text="Clusters",
    buttons=_add_button("k3scluster"),
)

namespace_item = PluginMenuItem(
    link="plugins:netbox_k3s:k3snamespace_list",
    link_text="Namespaces",
    buttons=_add_button("k3snamespace"),
)

pod_item = PluginMenuItem(
    link="plugins:netbox_k3s:k3spod_list",
    link_text="Pods",
    buttons=_add_button("k3spod"),
)

service_item = PluginMenuItem(
    link="plugins:netbox_k3s:k3sservice_list",
    link_text="Services",
    buttons=_add_button("k3sservice"),
)

_items = (cluster_item, namespace_item, pod_item, service_item)

if settings.PLUGINS_CONFIG.get("netbox_k3s", {}).get("top_level_menu", True):
    menu = PluginMenu(
        label="Kubernetes",
        icon_class="mdi mdi-kubernetes",
        groups=(("k3s", _items),),
    )
else:
    menu_items = _items
