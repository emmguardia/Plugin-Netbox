"""Enumerations used across the k3s models."""

from utilities.choices import ChoiceSet


class K3sClusterStatusChoices(ChoiceSet):
    key = "K3sCluster.status"

    STATUS_ACTIVE = "active"
    STATUS_OFFLINE = "offline"
    STATUS_STAGING = "staging"
    STATUS_DECOMMISSIONING = "decommissioning"

    CHOICES = [
        (STATUS_ACTIVE, "Active", "green"),
        (STATUS_OFFLINE, "Offline", "red"),
        (STATUS_STAGING, "Staging", "blue"),
        (STATUS_DECOMMISSIONING, "Decommissioning", "yellow"),
    ]


class K3sPodStatusChoices(ChoiceSet):
    key = "K3sPod.status"

    STATUS_RUNNING = "Running"
    STATUS_PENDING = "Pending"
    STATUS_SUCCEEDED = "Succeeded"
    STATUS_FAILED = "Failed"
    STATUS_UNKNOWN = "Unknown"

    CHOICES = [
        (STATUS_RUNNING, "Running", "green"),
        (STATUS_PENDING, "Pending", "yellow"),
        (STATUS_SUCCEEDED, "Succeeded", "blue"),
        (STATUS_FAILED, "Failed", "red"),
        (STATUS_UNKNOWN, "Unknown", "gray"),
    ]


class K3sServiceTypeChoices(ChoiceSet):
    key = "K3sService.type"

    TYPE_CLUSTERIP = "ClusterIP"
    TYPE_NODEPORT = "NodePort"
    TYPE_LOADBALANCER = "LoadBalancer"
    TYPE_EXTERNALNAME = "ExternalName"

    CHOICES = [
        (TYPE_CLUSTERIP, "ClusterIP", "blue"),
        (TYPE_NODEPORT, "NodePort", "purple"),
        (TYPE_LOADBALANCER, "LoadBalancer", "green"),
        (TYPE_EXTERNALNAME, "ExternalName", "gray"),
    ]
