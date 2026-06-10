"""FilterSets powering the list-view filters and API query parameters."""

import django_filters
from django.db.models import Q

from netbox.filtersets import NetBoxModelFilterSet

from .choices import (
    K3sClusterStatusChoices,
    K3sPodStatusChoices,
    K3sServiceTypeChoices,
)
from .models import K3sCluster, K3sNamespace, K3sPod, K3sService


class K3sClusterFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(choices=K3sClusterStatusChoices)

    class Meta:
        model = K3sCluster
        fields = ("id", "name", "status", "version", "nb_cluster_id")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(version__icontains=value)
        )


class K3sNamespaceFilterSet(NetBoxModelFilterSet):
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster",
        queryset=K3sCluster.objects.all(),
        label="Cluster (ID)",
    )

    class Meta:
        model = K3sNamespace
        fields = ("id", "name", "cluster_id")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value))


class K3sPodFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(choices=K3sPodStatusChoices)
    namespace_id = django_filters.ModelMultipleChoiceFilter(
        field_name="namespace",
        queryset=K3sNamespace.objects.all(),
        label="Namespace (ID)",
    )
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        field_name="namespace__cluster",
        queryset=K3sCluster.objects.all(),
        label="Cluster (ID)",
    )

    class Meta:
        model = K3sPod
        fields = ("id", "name", "status", "node", "image", "namespace_id")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(image__icontains=value)
            | Q(node__icontains=value)
        )


class K3sServiceFilterSet(NetBoxModelFilterSet):
    type = django_filters.MultipleChoiceFilter(choices=K3sServiceTypeChoices)
    namespace_id = django_filters.ModelMultipleChoiceFilter(
        field_name="namespace",
        queryset=K3sNamespace.objects.all(),
        label="Namespace (ID)",
    )
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        field_name="namespace__cluster",
        queryset=K3sCluster.objects.all(),
        label="Cluster (ID)",
    )

    class Meta:
        model = K3sService
        fields = ("id", "name", "type", "cluster_ip", "namespace_id")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(ports__icontains=value)
        )
