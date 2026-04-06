from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.blocks import CharBlock, ChoiceBlock, ListBlock, RichTextBlock, StructBlock, URLBlock
from wagtail.fields import RichTextField, StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.blocks import PageChooserBlock
from wagtail.models import Orderable, Page


class SimplePage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]


class BlogIndexPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["testapp.BlogPage"]


class BlogPage(Page):
    published_date = models.DateField(null=True, blank=True)
    feed_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    body = StreamField(
        [
            (
                "heading",
                StructBlock(
                    [
                        ("text", CharBlock()),
                        (
                            "size",
                            ChoiceBlock(choices=[("h2", "H2"), ("h3", "H3"), ("h4", "H4")]),
                        ),
                    ]
                ),
            ),
            ("paragraph", RichTextBlock()),
            ("image", ImageChooserBlock()),
            (
                "gallery",
                ListBlock(
                    StructBlock(
                        [
                            ("image", ImageChooserBlock()),
                            ("caption", CharBlock(required=False)),
                        ]
                    )
                ),
            ),
            ("related_pages", ListBlock(PageChooserBlock())),
        ],
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("published_date"),
        FieldPanel("feed_image"),
        FieldPanel("body"),
        InlinePanel("authors", label="Authors"),
    ]

    parent_page_types = ["testapp.BlogIndexPage"]
    subpage_types = []


class BlogPageAuthor(Orderable):
    page = ParentalKey(BlogPage, related_name="authors", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=100, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("role"),
    ]


class EventPage(Page):
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255)
    legacy_id = models.CharField(max_length=50, blank=True)
    body = StreamField(
        [
            ("text", RichTextBlock()),
            ("map_embed", URLBlock()),
        ],
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("start_date"),
        FieldPanel("end_date"),
        FieldPanel("location"),
        FieldPanel("body"),
    ]

    write_api_exclude = ["legacy_id"]
