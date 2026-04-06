import re

import markdown


def convert_rich_text_input(value) -> str:
    """
    Convert a RichTextInput value to Wagtail's internal format.

    Accepts either:
    - A plain string (passed through as-is)
    - A dict with {"format": "html"|"markdown"|"wagtail", "content": "..."}
    """
    if isinstance(value, str):
        return value

    if not isinstance(value, dict):
        return str(value)

    fmt = value.get("format", "html")
    content = value.get("content", "")

    if fmt == "wagtail":
        return content
    elif fmt == "html":
        return content
    elif fmt == "markdown":
        return markdown_to_wagtail(content)
    else:
        return content


def markdown_to_wagtail(md_text: str) -> str:
    """Convert Markdown to Wagtail's internal rich text format."""
    # Pre-process wagtail:// links before markdown conversion
    # Convert [text](wagtail://page/N) to placeholder that survives markdown
    def replace_wagtail_link(match):
        text = match.group(1)
        link_type = match.group(2)
        link_id = match.group(3)
        return f'<a linktype="{link_type}" id="{link_id}">{text}</a>'

    # Process wagtail:// links in markdown format
    processed = re.sub(
        r"\[([^\]]+)\]\(wagtail://(page|document|image)/(\d+)\)",
        replace_wagtail_link,
        md_text,
    )

    # Convert markdown to HTML
    html = markdown.markdown(processed)

    # The wagtail links are already in the output as <a linktype="..." id="...">
    # because we replaced them before markdown processing
    return html
