"""UI views — list / detail / edit / delete / bulk for every model."""

from django.db.models import Count

from netbox.views import generic
from utilities.views import register_model_view

from . import filtersets, forms, models, tables


# ---------------------------------------------------------------------------
# K3sCluster
# ---------------------------------------------------------------------------
@register_model_view(models.K3sCluster, "list", path="", detail=False)
class K3sClusterListView(generic.ObjectListView):
    queryset = models.K3sCluster.objects.annotate(
        namespace_count=Count("namespaces")
    )
    table = tables.K3sClusterTable
    filterset = filtersets.K3sClusterFilterSet
    filterset_form = forms.K3sClusterFilterForm


@register_model_view(models.K3sCluster)
class K3sClusterView(generic.ObjectView):
    queryset = models.K3sCluster.objects.all()

    def get_extra_context(self, request, instance):
        namespaces = instance.namespaces.all()
        namespace_table = tables.K3sNamespaceTable(namespaces)
        namespace_table.configure(request)
        return {"namespace_table": namespace_table}


@register_model_view(models.K3sCluster, "add", detail=False)
@register_model_view(models.K3sCluster, "edit")
class K3sClusterEditView(generic.ObjectEditView):
    queryset = models.K3sCluster.objects.all()
    form = forms.K3sClusterForm


@register_model_view(models.K3sCluster, "delete")
class K3sClusterDeleteView(generic.ObjectDeleteView):
    queryset = models.K3sCluster.objects.all()


@register_model_view(models.K3sCluster, "bulk_edit", path="edit", detail=False)
class K3sClusterBulkEditView(generic.BulkEditView):
    queryset = models.K3sCluster.objects.all()
    filterset = filtersets.K3sClusterFilterSet
    table = tables.K3sClusterTable
    form = forms.K3sClusterBulkEditForm


@register_model_view(models.K3sCluster, "bulk_delete", path="delete", detail=False)
class K3sClusterBulkDeleteView(generic.BulkDeleteView):
    queryset = models.K3sCluster.objects.all()
    filterset = filtersets.K3sClusterFilterSet
    table = tables.K3sClusterTable


# ---------------------------------------------------------------------------
# K3sNamespace
# ---------------------------------------------------------------------------
@register_model_view(models.K3sNamespace, "list", path="", detail=False)
class K3sNamespaceListView(generic.ObjectListView):
    queryset = models.K3sNamespace.objects.annotate(
        pod_count=Count("pods", distinct=True),
        service_count=Count("services", distinct=True),
    )
    table = tables.K3sNamespaceTable
    filterset = filtersets.K3sNamespaceFilterSet
    filterset_form = forms.K3sNamespaceFilterForm


@register_model_view(models.K3sNamespace)
class K3sNamespaceView(generic.ObjectView):
    queryset = models.K3sNamespace.objects.all()

    def get_extra_context(self, request, instance):
        pod_table = tables.K3sPodTable(instance.pods.all())
        pod_table.configure(request)
        service_table = tables.K3sServiceTable(instance.services.all())
        service_table.configure(request)
        return {"pod_table": pod_table, "service_table": service_table}


@register_model_view(models.K3sNamespace, "add", detail=False)
@register_model_view(models.K3sNamespace, "edit")
class K3sNamespaceEditView(generic.ObjectEditView):
    queryset = models.K3sNamespace.objects.all()
    form = forms.K3sNamespaceForm


@register_model_view(models.K3sNamespace, "delete")
class K3sNamespaceDeleteView(generic.ObjectDeleteView):
    queryset = models.K3sNamespace.objects.all()


@register_model_view(models.K3sNamespace, "bulk_delete", path="delete", detail=False)
class K3sNamespaceBulkDeleteView(generic.BulkDeleteView):
    queryset = models.K3sNamespace.objects.all()
    filterset = filtersets.K3sNamespaceFilterSet
    table = tables.K3sNamespaceTable


# ---------------------------------------------------------------------------
# K3sPod
# ---------------------------------------------------------------------------
@register_model_view(models.K3sPod, "list", path="", detail=False)
class K3sPodListView(generic.ObjectListView):
    queryset = models.K3sPod.objects.all()
    table = tables.K3sPodTable
    filterset = filtersets.K3sPodFilterSet
    filterset_form = forms.K3sPodFilterForm


@register_model_view(models.K3sPod)
class K3sPodView(generic.ObjectView):
    queryset = models.K3sPod.objects.all()


@register_model_view(models.K3sPod, "add", detail=False)
@register_model_view(models.K3sPod, "edit")
class K3sPodEditView(generic.ObjectEditView):
    queryset = models.K3sPod.objects.all()
    form = forms.K3sPodForm


@register_model_view(models.K3sPod, "delete")
class K3sPodDeleteView(generic.ObjectDeleteView):
    queryset = models.K3sPod.objects.all()


@register_model_view(models.K3sPod, "bulk_edit", path="edit", detail=False)
class K3sPodBulkEditView(generic.BulkEditView):
    queryset = models.K3sPod.objects.all()
    filterset = filtersets.K3sPodFilterSet
    table = tables.K3sPodTable
    form = forms.K3sPodBulkEditForm


@register_model_view(models.K3sPod, "bulk_delete", path="delete", detail=False)
class K3sPodBulkDeleteView(generic.BulkDeleteView):
    queryset = models.K3sPod.objects.all()
    filterset = filtersets.K3sPodFilterSet
    table = tables.K3sPodTable


# ---------------------------------------------------------------------------
# K3sService
# ---------------------------------------------------------------------------
@register_model_view(models.K3sService, "list", path="", detail=False)
class K3sServiceListView(generic.ObjectListView):
    queryset = models.K3sService.objects.all()
    table = tables.K3sServiceTable
    filterset = filtersets.K3sServiceFilterSet
    filterset_form = forms.K3sServiceFilterForm


@register_model_view(models.K3sService)
class K3sServiceView(generic.ObjectView):
    queryset = models.K3sService.objects.all()


@register_model_view(models.K3sService, "add", detail=False)
@register_model_view(models.K3sService, "edit")
class K3sServiceEditView(generic.ObjectEditView):
    queryset = models.K3sService.objects.all()
    form = forms.K3sServiceForm


@register_model_view(models.K3sService, "delete")
class K3sServiceDeleteView(generic.ObjectDeleteView):
    queryset = models.K3sService.objects.all()


@register_model_view(models.K3sService, "bulk_edit", path="edit", detail=False)
class K3sServiceBulkEditView(generic.BulkEditView):
    queryset = models.K3sService.objects.all()
    filterset = filtersets.K3sServiceFilterSet
    table = tables.K3sServiceTable
    form = forms.K3sServiceBulkEditForm


@register_model_view(models.K3sService, "bulk_delete", path="delete", detail=False)
class K3sServiceBulkDeleteView(generic.BulkDeleteView):
    queryset = models.K3sService.objects.all()
    filterset = filtersets.K3sServiceFilterSet
    table = tables.K3sServiceTable
