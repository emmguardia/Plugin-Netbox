"""Django admin registration (optional; NetBox primarily uses its own UI)."""

from django.contrib import admin

from .models import K3sCluster, K3sNamespace, K3sPod, K3sService


@admin.register(K3sCluster)
class K3sClusterAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "version", "nb_cluster")
    list_filter = ("status",)
    search_fields = ("name", "version")


@admin.register(K3sNamespace)
class K3sNamespaceAdmin(admin.ModelAdmin):
    list_display = ("name", "cluster")
    list_filter = ("cluster",)
    search_fields = ("name",)


@admin.register(K3sPod)
class K3sPodAdmin(admin.ModelAdmin):
    list_display = ("name", "namespace", "status", "node", "ip_address")
    list_filter = ("status", "namespace")
    search_fields = ("name", "image", "node")


@admin.register(K3sService)
class K3sServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "namespace", "type", "cluster_ip", "ports")
    list_filter = ("type", "namespace")
    search_fields = ("name",)
