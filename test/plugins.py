# Test config: enable the k3s plugin
DEVELOPER = True

# Required so API token creation works in tests (NetBox 4.6+ v2 tokens).
API_TOKEN_PEPPERS = {1: "test-pepper-value-that-is-at-least-fifty-characters-long-000000"}

# Allow login/CSRF when browsing locally at http://localhost:8080
CSRF_TRUSTED_ORIGINS = ["http://localhost:8080", "http://127.0.0.1:8080"]
LOGIN_REQUIRED = False

PLUGINS = ["netbox_k3s"]

PLUGINS_CONFIG = {
    "netbox_k3s": {
        "top_level_menu": True,
    },
}
