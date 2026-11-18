from crewai.tools import tool
import markdown

def render_markdown_to_html(markdown_content: str) -> str:
    """
    Core deterministic markdown-to-HTML transformation function.
    """
    html_output = markdown.markdown(
        markdown_content, 
        extensions=['extra', 'tables', 'nl2br']
    )
    return f"<article class='markdown-body'>{html_output}</article>"

@tool("Markdown_to_HTML_Converter")
def convert_markdown_to_html(markdown_content: str) -> str:
    """
    Converts raw markdown text into properly formatted semantic HTML.
    Input MUST be a valid markdown string. Use this tool as the final step 
    to format the output for web presentation.
    """
    return render_markdown_to_html(markdown_content)