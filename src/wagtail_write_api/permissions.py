from wagtail.permission_policies.pages import PagePermissionPolicy

_policy = PagePermissionPolicy()

ACTIONS = ["add", "change", "publish", "delete"]


def get_user_page_permissions(user, page) -> list[str]:
    """Return list of permission actions the user has on this page."""
    if user.is_superuser:
        return ACTIONS[:]
    return [
        action
        for action in ACTIONS
        if _policy.user_has_permission_for_instance(user, action, page)
    ]
