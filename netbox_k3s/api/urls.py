"""REST API routing — registered under /api/plugins/k3s/."""

from netbox.api.routers import NetBoxRouter

from . import views

app_name = "netbox_k3s"

router = NetBoxRouter()
router.register("clusters", views.K3sClusterViewSet)
router.register("namespaces", views.K3sNamespaceViewSet)
router.register("pods", views.K3sPodViewSet)
router.register("services", views.K3sServiceViewSet)

urlpatterns = router.urls
