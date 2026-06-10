"""REST API viewsets."""

from django.db.models import Count

from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets, models
from .serializers import (
    K3sClusterSerializer,
    K3sNamespaceSerializer,
    K3sPodSerializer,
    K3sServiceSerializer,
)


class K3sClusterViewSet(NetBoxModelViewSet):
    queryset = models.K3sCluster.objects.prefetch_related("tags").annotate(
        namespace_count=Count("namespaces")
    )
    serializer_class = K3sClusterSerializer
    filterset_class = filtersets.K3sClusterFilterSet


class K3sNamespaceViewSet(NetBoxModelViewSet):
    queryset = models.K3sNamespace.objects.prefetch_related("cluster", "tags")
    serializer_class = K3sNamespaceSerializer
    filterset_class = filtersets.K3sNamespaceFilterSet


class K3sPodViewSet(NetBoxModelViewSet):
    queryset = models.K3sPod.objects.prefetch_related("namespace", "tags")
    serializer_class = K3sPodSerializer
    filterset_class = filtersets.K3sPodFilterSet


class K3sServiceViewSet(NetBoxModelViewSet):
    queryset = models.K3sService.objects.prefetch_related("namespace", "tags")
    serializer_class = K3sServiceSerializer
    filterset_class = filtersets.K3sServiceFilterSet
