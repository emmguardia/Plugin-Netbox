"""REST API serializers."""

from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer
from virtualization.api.serializers import ClusterSerializer

from ..models import K3sCluster, K3sNamespace, K3sPod, K3sService


class K3sClusterSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_k3s-api:k3scluster-detail"
    )
    nb_cluster = ClusterSerializer(nested=True, required=False, allow_null=True)
    namespace_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = K3sCluster
        fields = (
            "id", "url", "display", "name", "status", "version", "node_count",
            "nb_cluster", "namespace_count", "comments", "tags", "custom_fields",
            "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "name", "status")


class K3sNamespaceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_k3s-api:k3snamespace-detail"
    )
    cluster = K3sClusterSerializer(nested=True)

    class Meta:
        model = K3sNamespace
        fields = (
            "id", "url", "display", "name", "cluster", "comments", "tags",
            "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "name")


class K3sPodSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_k3s-api:k3spod-detail"
    )
    namespace = K3sNamespaceSerializer(nested=True)

    class Meta:
        model = K3sPod
        fields = (
            "id", "url", "display", "name", "namespace", "image", "status",
            "node", "ip_address", "restarts", "container_count", "started",
            "labels", "comments", "tags", "custom_fields",
            "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "name", "status")


class K3sServiceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_k3s-api:k3sservice-detail"
    )
    namespace = K3sNamespaceSerializer(nested=True)

    class Meta:
        model = K3sService
        fields = (
            "id", "url", "display", "name", "namespace", "type", "cluster_ip",
            "external_ip", "ports", "selector", "comments", "tags",
            "custom_fields", "created", "last_updated",
        )
        brief_fields = ("id", "url", "display", "name", "type")
