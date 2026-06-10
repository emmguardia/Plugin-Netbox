"""Edit, filter and bulk-edit forms for the UI."""

from django import forms

from netbox.forms import (
    NetBoxModelForm,
    NetBoxModelFilterSetForm,
    NetBoxModelBulkEditForm,
)
from virtualization.models import Cluster
from utilities.forms.fields import (
    CommentField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from utilities.forms.rendering import FieldSet

from .choices import (
    K3sClusterStatusChoices,
    K3sPodStatusChoices,
    K3sServiceTypeChoices,
)
from .models import K3sCluster, K3sNamespace, K3sPod, K3sService


# ---------------------------------------------------------------------------
# K3sCluster
# ---------------------------------------------------------------------------
class K3sClusterForm(NetBoxModelForm):
    nb_cluster = DynamicModelChoiceField(
        queryset=Cluster.objects.all(),
        required=False,
        label="NetBox cluster",
    )
    comments = CommentField()

    class Meta:
        model = K3sCluster
        fields = ("name", "status", "version", "nb_cluster", "comments", "tags")


class K3sClusterFilterForm(NetBoxModelFilterSetForm):
    model = K3sCluster
    status = forms.MultipleChoiceField(choices=K3sClusterStatusChoices, required=False)
    version = forms.CharField(required=False)
    tag = TagFilterField(model)


class K3sClusterBulkEditForm(NetBoxModelBulkEditForm):
    model = K3sCluster
    status = forms.ChoiceField(
        choices=[("", "---------")] + K3sClusterStatusChoices.CHOICES, required=False
    )
    version = forms.CharField(max_length=50, required=False)
    fieldsets = (FieldSet("status", "version"),)
    nullable_fields = ("version",)


# ---------------------------------------------------------------------------
# K3sNamespace
# ---------------------------------------------------------------------------
class K3sNamespaceForm(NetBoxModelForm):
    cluster = DynamicModelChoiceField(queryset=K3sCluster.objects.all())
    comments = CommentField()

    class Meta:
        model = K3sNamespace
        fields = ("name", "cluster", "comments", "tags")


class K3sNamespaceFilterForm(NetBoxModelFilterSetForm):
    model = K3sNamespace
    cluster_id = DynamicModelMultipleChoiceField(
        queryset=K3sCluster.objects.all(), required=False, label="Cluster"
    )
    tag = TagFilterField(model)


# ---------------------------------------------------------------------------
# K3sPod
# ---------------------------------------------------------------------------
class K3sPodForm(NetBoxModelForm):
    namespace = DynamicModelChoiceField(queryset=K3sNamespace.objects.all())
    comments = CommentField()

    class Meta:
        model = K3sPod
        fields = (
            "name", "namespace", "image", "status", "node", "ip_address",
            "comments", "tags",
        )


class K3sPodFilterForm(NetBoxModelFilterSetForm):
    model = K3sPod
    cluster_id = DynamicModelMultipleChoiceField(
        queryset=K3sCluster.objects.all(), required=False, label="Cluster"
    )
    namespace_id = DynamicModelMultipleChoiceField(
        queryset=K3sNamespace.objects.all(),
        required=False,
        label="Namespace",
        query_params={"cluster_id": "$cluster_id"},
    )
    status = forms.MultipleChoiceField(choices=K3sPodStatusChoices, required=False)
    node = forms.CharField(required=False)
    tag = TagFilterField(model)


class K3sPodBulkEditForm(NetBoxModelBulkEditForm):
    model = K3sPod
    status = forms.ChoiceField(
        choices=[("", "---------")] + K3sPodStatusChoices.CHOICES, required=False
    )
    node = forms.CharField(max_length=253, required=False)
    fieldsets = (FieldSet("status", "node"),)
    nullable_fields = ("node",)


# ---------------------------------------------------------------------------
# K3sService
# ---------------------------------------------------------------------------
class K3sServiceForm(NetBoxModelForm):
    namespace = DynamicModelChoiceField(queryset=K3sNamespace.objects.all())
    comments = CommentField()

    class Meta:
        model = K3sService
        fields = (
            "name", "namespace", "type", "cluster_ip", "ports", "comments", "tags",
        )


class K3sServiceFilterForm(NetBoxModelFilterSetForm):
    model = K3sService
    cluster_id = DynamicModelMultipleChoiceField(
        queryset=K3sCluster.objects.all(), required=False, label="Cluster"
    )
    namespace_id = DynamicModelMultipleChoiceField(
        queryset=K3sNamespace.objects.all(),
        required=False,
        label="Namespace",
        query_params={"cluster_id": "$cluster_id"},
    )
    type = forms.MultipleChoiceField(choices=K3sServiceTypeChoices, required=False)
    tag = TagFilterField(model)


class K3sServiceBulkEditForm(NetBoxModelBulkEditForm):
    model = K3sService
    type = forms.ChoiceField(
        choices=[("", "---------")] + K3sServiceTypeChoices.CHOICES, required=False
    )
    fieldsets = (FieldSet("type"),)
