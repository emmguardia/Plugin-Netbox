"""URL routing for the plugin.

Concrete view routes are produced by the ``@register_model_view`` decorators in
``views.py`` and collected here with ``get_model_urls``.
"""

from django.urls import include, path

from utilities.urls import get_model_urls

# Importing views runs the @register_model_view decorators, which populate the
# registry that get_model_urls() reads from. Without this import the registry is
# empty and no URLs/names are produced.
from . import views  # noqa: F401

app_name = "netbox_k3s"

urlpatterns = [
    path("clusters/", include(get_model_urls("netbox_k3s", "k3scluster", detail=False))),
    path("clusters/<int:pk>/", include(get_model_urls("netbox_k3s", "k3scluster"))),

    path("namespaces/", include(get_model_urls("netbox_k3s", "k3snamespace", detail=False))),
    path("namespaces/<int:pk>/", include(get_model_urls("netbox_k3s", "k3snamespace"))),

    path("pods/", include(get_model_urls("netbox_k3s", "k3spod", detail=False))),
    path("pods/<int:pk>/", include(get_model_urls("netbox_k3s", "k3spod"))),

    path("services/", include(get_model_urls("netbox_k3s", "k3sservice", detail=False))),
    path("services/<int:pk>/", include(get_model_urls("netbox_k3s", "k3sservice"))),
]
