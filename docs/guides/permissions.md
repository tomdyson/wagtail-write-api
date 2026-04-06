# Permissions

The API enforces the same permission model as the Wagtail admin. A user can never do more via the API than they could through the admin interface.

## How Wagtail permissions work

Wagtail uses a tree-based permission model built on Django groups:

- **Groups** are assigned permissions on specific pages in the page tree
- Permissions **propagate downward** -- permission on a parent applies to all descendants
- Four permission types exist: `add`, `change`, `publish`, `delete`

## What each permission allows

| Permission | API operations allowed |
|-----------|----------------------|
| `add` | Create child pages under the permitted page |
| `change` | Update pages, save revisions |
| `publish` | Publish, unpublish pages |
| `delete` | Delete pages |

Superusers bypass all permission checks and can perform any operation.

## Permission checks by endpoint

| Endpoint | Required permission |
|----------|-------------------|
| `GET /pages/` | Authentication only |
| `GET /pages/{id}/` | Authentication only |
| `POST /pages/` | `add` on the parent page |
| `PATCH /pages/{id}/` | `change` on the page |
| `DELETE /pages/{id}/` | `delete` on the page |
| `POST /pages/{id}/publish/` | `publish` on the page |
| `POST /pages/{id}/unpublish/` | `publish` on the page |
| `POST /pages/{id}/copy/` | `add` on the destination page |
| `POST /pages/{id}/move/` | `change` on the source, `add` on the destination |

## The `user_permissions` field

Every page detail response includes a `meta.user_permissions` array listing what the authenticated user can do:

```json
{
  "meta": {
    "user_permissions": ["add", "change", "publish"]
  }
}
```

Use this to conditionally show/hide UI controls in your editor without making separate permission-checking requests.

## Page type constraints

Beyond permissions, Wagtail enforces page type constraints:

- `parent_page_types` on a model restricts where it can be created
- `subpage_types` on a model restricts what can be created under it

The API returns `422` if you try to create a page type that isn't allowed under the chosen parent. Use the [Schema Discovery API](../api/schema-discovery.md) to check `allowed_parent_types` and `allowed_subpage_types` before creating.

## Setting up permissions

Permissions are managed in the Wagtail admin under Settings > Groups, or programmatically:

```python
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from wagtail.models import GroupPagePermission, Page

# Create a group
editors = Group.objects.create(name="Blog Editors")

# Grant add + change on the blog section
page_ct = ContentType.objects.get_for_model(Page)
blog_index = Page.objects.get(slug="blog")

for codename in ["add_page", "change_page"]:
    perm = Permission.objects.get(content_type=page_ct, codename=codename)
    GroupPagePermission.objects.create(
        group=editors, page=blog_index, permission=perm
    )

# Add a user to the group
user.groups.add(editors)
```
