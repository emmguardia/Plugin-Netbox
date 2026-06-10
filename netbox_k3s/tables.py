"""django-tables2 tables for the list views."""

import django_tables2 as tables

from netbox.tables import NetBoxTable, columns

from .models import K3sCluster, K3sNamespace, K3sPod, K3sService


class K3sClusterTable(NetBoxTable):
    name = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    nb_cluster = tables.Column(linkify=True, verbose_name="NetBox cluster")
    namespace_count = columns.LinkedCountColumn(
        viewname="plugins:netbox_k3s:k3snamespace_list",
        url_params={"cluster_id": "pk"},
        verbose_name="Namespaces",
    )
    tags = columns.TagColumn(url_name="plugins:netbox_k3s:k3scluster_list")

    class Meta(NetBoxTable.Meta):
        model = K3sCluster
        fields = (
            "pk", "id", "name", "status", "version", "node_count", "nb_cluster",
            "namespace_count", "tags", "created", "last_updated",
        )
        default_columns = (
            "name", "status", "version", "node_count", "nb_cluster", "namespace_count",
        )


class K3sNamespaceTable(NetBoxTable):
    name = tables.Column(linkify=True)
    cluster = tables.Column(linkify=True)
    pod_count = columns.LinkedCountColumn(
        viewname="plugins:netbox_k3s:k3spod_list",
        url_params={"namespace_id": "pk"},
        verbose_name="Pods",
    )
    service_count = columns.LinkedCountColumn(
        viewname="plugins:netbox_k3s:k3sservice_list",
        url_params={"namespace_id": "pk"},
        verbose_name="Services",
    )
    tags = columns.TagColumn(url_name="plugins:netbox_k3s:k3snamespace_list")

    class Meta(NetBoxTable.Meta):
        model = K3sNamespace
        fields = (
            "pk", "id", "name", "cluster", "pod_count", "service_count",
            "tags", "created", "last_updated",
        )
        default_columns = ("name", "cluster", "pod_count", "service_count")


class K3sPodTable(NetBoxTable):
    name = tables.Column(linkify=True)
    namespace = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_k3s:k3spod_list")

    class Meta(NetBoxTable.Meta):
        model = K3sPod
        fields = (
            "pk", "id", "name", "namespace", "image", "status", "node",
            "ip_address", "restarts", "container_count", "started",
            "tags", "created", "last_updated",
        )
        default_columns = (
            "name", "namespace", "status", "node", "ip_address", "restarts",
        )


class K3sServiceTable(NetBoxTable):
    name = tables.Column(linkify=True)
    namespace = tables.Column(linkify=True)
    type = columns.ChoiceFieldColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_k3s:k3sservice_list")

    class Meta(NetBoxTable.Meta):
        model = K3sService
        fields = (
            "pk", "id", "name", "namespace", "type", "cluster_ip", "external_ip",
            "ports", "tags", "created", "last_updated",
        )
        default_columns = (
            "name", "namespace", "type", "cluster_ip", "external_ip", "ports",
        )
