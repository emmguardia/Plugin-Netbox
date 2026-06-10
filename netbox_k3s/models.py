"""Database models for the k3s plugin.

All models inherit from ``NetBoxModel`` so they get custom fields, tags,
change-logging, journaling and the standard API/UI plumbing for free.
"""

from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel

from .choices import (
    K3sClusterStatusChoices,
    K3sPodStatusChoices,
    K3sServiceTypeChoices,
)

__all__ = ("K3sCluster", "K3sNamespace", "K3sPod", "K3sService")


class K3sCluster(NetBoxModel):
    """A k3s cluster, optionally tied to an existing NetBox Cluster."""

    name = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=50,
        choices=K3sClusterStatusChoices,
        default=K3sClusterStatusChoices.STATUS_ACTIVE,
    )
    version = models.CharField(max_length=50, blank=True)
    node_count = models.PositiveIntegerField(blank=True, null=True)
    # Link to the native NetBox Cluster object, if one exists.
    nb_cluster = models.ForeignKey(
        to="virtualization.Cluster",
        on_delete=models.SET_NULL,
        related_name="k3s_clusters",
        blank=True,
        null=True,
        verbose_name="NetBox cluster",
    )
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "k3s cluster"
        verbose_name_plural = "k3s clusters"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_k3s:k3scluster", args=[self.pk])

    def get_status_color(self):
        return K3sClusterStatusChoices.colors.get(self.status)


class K3sNamespace(NetBoxModel):
    """A namespace inside a k3s cluster."""

    name = models.CharField(max_length=253)
    cluster = models.ForeignKey(
        to="netbox_k3s.K3sCluster",
        on_delete=models.CASCADE,
        related_name="namespaces",
    )
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("cluster", "name")
        verbose_name = "k3s namespace"
        verbose_name_plural = "k3s namespaces"
        constraints = [
            models.UniqueConstraint(
                fields=["cluster", "name"],
                name="netbox_k3s_namespace_unique_cluster_name",
            )
        ]

    def __str__(self):
        return f"{self.cluster.name}/{self.name}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_k3s:k3snamespace", args=[self.pk])


class K3sPod(NetBoxModel):
    """A pod running in a namespace."""

    name = models.CharField(max_length=253)
    namespace = models.ForeignKey(
        to="netbox_k3s.K3sNamespace",
        on_delete=models.CASCADE,
        related_name="pods",
    )
    image = models.CharField(max_length=512, blank=True)
    status = models.CharField(
        max_length=50,
        choices=K3sPodStatusChoices,
        default=K3sPodStatusChoices.STATUS_UNKNOWN,
    )
    node = models.CharField(max_length=253, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    restarts = models.PositiveIntegerField(default=0)
    container_count = models.PositiveIntegerField(default=0)
    started = models.DateTimeField(blank=True, null=True)
    labels = models.JSONField(blank=True, default=dict)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("namespace", "name")
        verbose_name = "k3s pod"
        verbose_name_plural = "k3s pods"
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "name"],
                name="netbox_k3s_pod_unique_namespace_name",
            )
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_k3s:k3spod", args=[self.pk])

    def get_status_color(self):
        return K3sPodStatusChoices.colors.get(self.status)


class K3sService(NetBoxModel):
    """A service exposing pods within a namespace."""

    name = models.CharField(max_length=253)
    namespace = models.ForeignKey(
        to="netbox_k3s.K3sNamespace",
        on_delete=models.CASCADE,
        related_name="services",
    )
    type = models.CharField(
        max_length=50,
        choices=K3sServiceTypeChoices,
        default=K3sServiceTypeChoices.TYPE_CLUSTERIP,
    )
    cluster_ip = models.GenericIPAddressField(blank=True, null=True)
    # Free-form "port:targetPort/protocol" list, e.g. "80:8080/TCP, 443:8443/TCP".
    ports = models.CharField(max_length=255, blank=True)
    # LoadBalancer/external address (IP or hostname).
    external_ip = models.CharField(max_length=253, blank=True)
    # Kubernetes label selector of the service.
    selector = models.JSONField(blank=True, default=dict)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("namespace", "name")
        verbose_name = "k3s service"
        verbose_name_plural = "k3s services"
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "name"],
                name="netbox_k3s_service_unique_namespace_name",
            )
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_k3s:k3sservice", args=[self.pk])

    def get_type_color(self):
        return K3sServiceTypeChoices.colors.get(self.type)
