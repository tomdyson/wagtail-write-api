import json
import uuid

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from wagtail_write_api.models import ApiToken
from wagtail.models import GroupPagePermission, Page, Site

from testapp.models import (
    BlogIndexPage,
    BlogPage,
    BlogPageAuthor,
    EventPage,
    SimplePage,
)


class Command(BaseCommand):
    help = "Seed the database with demo content and users"

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        # Users
        admin = self._create_user("admin", is_superuser=True)
        editor = self._create_user("editor")
        moderator = self._create_user("moderator")
        reviewer = self._create_user("reviewer")

        # Page tree
        root = Page.objects.filter(depth=1).first()
        # Delete existing children via individual deletion to keep treebeard consistent
        for child in root.get_children():
            child.delete()
        # Refresh root from DB after tree modifications
        root = Page.objects.filter(depth=1).first()

        home = root.add_child(title="Home", slug="home")
        Site.objects.update_or_create(
            is_default_site=True,
            defaults={"hostname": "localhost", "root_page": home},
        )

        about = home.add_child(instance=SimplePage(title="About", slug="about", body="<p>About us</p>"))
        about.save_revision().publish()

        # Blog
        blog_index = home.add_child(
            instance=BlogIndexPage(title="Blog", slug="blog", intro="<p>Our blog</p>")
        )
        blog_index.save_revision().publish()

        for i in range(1, 6):
            blog = blog_index.add_child(
                instance=BlogPage(
                    title=f"Blog Post {i}",
                    slug=f"blog-post-{i}",
                    published_date=f"2026-0{i}-01",
                    body=json.dumps(
                        [
                            {
                                "type": "heading",
                                "value": {"text": f"Heading for post {i}", "size": "h2"},
                                "id": str(uuid.uuid4()),
                            },
                            {
                                "type": "paragraph",
                                "value": f"<p>Content of blog post {i}.</p>",
                                "id": str(uuid.uuid4()),
                            },
                        ]
                    ),
                )
            )
            blog.save_revision().publish()

            BlogPageAuthor.objects.create(page=blog, name=f"Author {i}", role="Writer", sort_order=0)

        # Events
        events_index = home.add_child(instance=SimplePage(title="Events", slug="events", body=""))
        events_index.save_revision().publish()

        for i in range(1, 4):
            event = events_index.add_child(
                instance=EventPage(
                    title=f"Event {i}",
                    slug=f"event-{i}",
                    start_date=f"2026-0{i + 3}-15T10:00:00Z",
                    location=f"Venue {i}",
                    body=json.dumps(
                        [
                            {
                                "type": "text",
                                "value": f"<p>Details about event {i}.</p>",
                                "id": str(uuid.uuid4()),
                            }
                        ]
                    ),
                )
            )
            event.save_revision().publish()

        # Groups + permissions (Wagtail 7+ uses permission FK, not permission_type)
        from django.contrib.auth.models import Permission as AuthPermission
        from django.contrib.contenttypes.models import ContentType

        page_ct = ContentType.objects.get_for_model(Page)

        editors_group, _ = Group.objects.get_or_create(name="Editors")
        for codename in ["add_page", "change_page"]:
            perm = AuthPermission.objects.get(content_type=page_ct, codename=codename)
            GroupPagePermission.objects.get_or_create(
                group=editors_group, page=blog_index, permission=perm
            )
        editor.groups.add(editors_group)

        mods_group, _ = Group.objects.get_or_create(name="Moderators")
        for codename in ["add_page", "change_page", "publish_page"]:
            perm, _ = AuthPermission.objects.get_or_create(
                content_type=page_ct, codename=codename
            )
            GroupPagePermission.objects.get_or_create(
                group=mods_group, page=home, permission=perm
            )
        moderator.groups.add(mods_group)

        # Print tokens
        self.stdout.write("\n--- API Tokens ---")
        for user in [admin, editor, moderator, reviewer]:
            token, _ = ApiToken.objects.get_or_create(user=user)
            self.stdout.write(f"  {user.username}: {token.key}")

        self.stdout.write(f"\nCreated {Page.objects.count()} pages")
        self.stdout.write(self.style.SUCCESS("Done!"))

    def _create_user(self, username, is_superuser=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@example.com",
                "is_superuser": is_superuser,
                "is_staff": True,
                "is_active": True,
            },
        )
        if created:
            user.set_password("password")
            user.save()
        return user
