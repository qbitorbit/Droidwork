cat > ~/.deepagents/agent/skills/confluence/mcp_server/server.py << 'EOF'
"""
Confluence MCP Server

Exposes Confluence operations as MCP tools for deepagents.
Uses FastMCP framework with Pydantic validation.
"""

import json
import sys
import os
from typing import Optional, List
from enum import Enum

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from confluence_client import ConfluenceClient, PageContent


# =============================================================================
# INITIALIZE MCP SERVER
# =============================================================================

mcp = FastMCP("confluence_mcp")

# Lazy-loaded client (initialized on first use)
_client: Optional[ConfluenceClient] = None


def get_client() -> ConfluenceClient:
    """Get or create the Confluence client."""
    global _client
    if _client is None:
        _client = ConfluenceClient()
    return _client


# =============================================================================
# RESPONSE FORMAT
# =============================================================================

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


# =============================================================================
# INPUT MODELS
# =============================================================================

class SearchInput(BaseModel):
    """Input for confluence_search tool."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    query: str = Field(
        ..., 
        description="Search query text (e.g., 'deployment guide', 'API documentation')",
        min_length=1,
        max_length=500
    )
    space_key: Optional[str] = Field(
        default=None,
        description="Limit search to a specific space (e.g., 'DEV', 'QA', 'INFRA')"
    )
    limit: int = Field(
        default=20,
        description="Maximum number of results to return",
        ge=1,
        le=100
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for readable or 'json' for structured"
    )


class GetPageInput(BaseModel):
    """Input for confluence_get_page tool."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    page_id: Optional[str] = Field(
        default=None,
        description="Page ID (e.g., '12345678'). Use this OR space_key+title."
    )
    space_key: Optional[str] = Field(
        default=None,
        description="Space key (e.g., 'DEV'). Required if using title instead of page_id."
    )
    title: Optional[str] = Field(
        default=None,
        description="Page title. Required if using space_key instead of page_id."
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for readable or 'json' for structured"
    )


class GetPageTextInput(BaseModel):
    """Input for confluence_get_page_text tool."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    page_id: Optional[str] = Field(
        default=None,
        description="Page ID. Use this OR space_key+title."
    )
    space_key: Optional[str] = Field(
        default=None,
        description="Space key. Required if using title."
    )
    title: Optional[str] = Field(
        default=None,
        description="Page title. Required if using space_key."
    )


class GetPageImagesInput(BaseModel):
    """Input for confluence_get_page_images tool."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    page_id: str = Field(
        ...,
        description="Page ID to extract images from"
    )


class GetTableInput(BaseModel):
    """Input for confluence_get_table tool."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    page_id: str = Field(
        ...,
        description="Page ID containing the table"
    )
    table_index: int = Field(
        default=0,
        description="Which table to get (0-indexed, default is first table)",
        ge=0
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for readable or 'json' for structured"
    )


class UpdateTableCellInput(BaseModel):
    """Input for confluence_update_table_cell tool."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    page_id: str = Field(..., description="Page ID containing the table")
    table_index: int = Field(default=0, description="Which table (0-indexed)", ge=0)
    row_index: int = Field(..., description="Row to update (0-indexed)", ge=0)
    col_index: int = Field(..., description="Column to update (0-indexed)", ge=0)
    new_value: str = Field(..., description="New cell value")


class CreatePageInput(BaseModel):
    """Input for confluence_create_page tool."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    space_key: str = Field(
        ...,
        description="Target space key (e.g., 'DEV', 'QA')"
    )
    title: str = Field(
        ...,
        description="Page title",
        min_length=1,
        max_length=255
    )
    body: str = Field(
        ...,
        description="Page content (HTML or plain text)"
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="Optional parent page ID to nest under"
    )


class UpdatePageInput(BaseModel):
    """Input for confluence_update_page tool."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    page_id: str = Field(..., description="Page ID to update")
    title: str = Field(..., description="Page title (can be unchanged)")
    body: str = Field(..., description="New page content (HTML)")


class GetChildrenInput(BaseModel):
    """Input for confluence_get_children tool."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    page_id: str = Field(..., description="Parent page ID")
    limit: int = Field(default=25, description="Max children to return", ge=1, le=100)


class ListSpacesInput(BaseModel):
    """Input for confluence_list_spaces tool."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    
    limit: int = Field(default=50, description="Max spaces to return", ge=1, le=200)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )


# =============================================================================
# FORMATTING HELPERS
# =============================================================================

def format_search_results(results: dict, fmt: ResponseFormat) -> str:
    """Format search results for output."""
    if fmt == ResponseFormat.JSON:
        return json.dumps(results, indent=2)
    
    # Markdown format
    lines = [f"## Search Results ({results['total']} total)\n"]
    
    for item in results["results"]:
        lines.append(f"### {item['title']}")
        lines.append(f"- **Space:** {item['space_name']} ({item['space_key']})")
        lines.append(f"- **URL:** {item['url']}")
        lines.append(f"- **ID:** {item['page_id']}")
        if item.get("excerpt"):
            lines.append(f"- **Excerpt:** {item['excerpt'][:200]}...")
        lines.append("")
    
    if results["has_more"]:
        lines.append(f"*Showing {len(results['results'])} of {results['total']} results. Use offset to see more.*")
    
    return "\n".join(lines)


def format_page_content(page: PageContent, fmt: ResponseFormat) -> str:
    """Format page content for output."""
    if fmt == ResponseFormat.JSON:
        return json.dumps(vars(page), indent=2)
    
    # Markdown format
    lines = [
        f"# {page.title}",
        "",
        f"**Space:** {page.space_key}",
        f"**URL:** {page.url}",
        f"**Page ID:** {page.page_id}",
        f"**Version:** {page.version}",
        f"**Last Modified:** {page.last_modified} by {page.last_modifier}",
        f"**Has Images:** {'Yes (' + str(len(page.image_urls)) + ')' if page.has_images else 'No'}",
        "",
        "---",
        "",
        page.body_text
    ]
    
    return "\n".join(lines)


def format_table(table: List[List[str]], fmt: ResponseFormat) -> str:
    """Format table for output."""
    if fmt == ResponseFormat.JSON:
        return json.dumps({"rows": table}, indent=2)
    
    if not table:
        return "*(Empty table)*"
    
    # Markdown table
    lines = []
    
    # Header row
    header = table[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    
    # Data rows
    for row in table[1:]:
        # Pad row if needed
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[:len(header)]) + " |")
    
    return "\n".join(lines)


def format_spaces(spaces: List[dict], fmt: ResponseFormat) -> str:
    """Format spaces list for output."""
    if fmt == ResponseFormat.JSON:
        return json.dumps(spaces, indent=2)
    
    lines = ["## Available Spaces\n"]
    for space in spaces:
        lines.append(f"- **{space['name']}** (`{space['key']}`) - {space['type']}")
    
    return "\n".join(lines)


# =============================================================================
# MCP TOOLS
# =============================================================================

@mcp.tool(
    name="confluence_search",
    annotations={
        "title": "Search Confluence",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def confluence_search(params: SearchInput) -> str:
    """
    Search Confluence pages by text query.
    
    Use this to find pages containing specific content, documentation,
    guides, or any information stored in Confluence.
    
    Args:
        params: SearchInput containing query, optional space_key, limit, and response_format
        
    Returns:
        List of matching pages with titles, URLs, and excerpts
    """
    client = get_client()
    results = client.search(
        query=params.query,
        space_key=params.space_key,
        limit=params.limit
    )
    return format_search_results(results, params.response_format)


@mcp.tool(
    name="confluence_get_page",
    annotations={
        "title": "Get Confluence Page",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def confluence_get_page(params: GetPageInput) -> str:
    """
    Get full content of a Confluence page.
    
    Retrieves the complete page including text content, metadata,
    and information about embedded images. Use page_id for direct
    access or space_key+title to find by name.
    
    NOTE: If the page contains diagrams/flowcharts/images, use
    confluence_get_page_images to get the images for visual analysis.
    
    Args:
        params: GetPageInput with page_id OR (space_key AND title)
        
    Returns:
        Full page content with metadata
    """
    client = get_client()
    page = client.get_page(
        page_id=params.page_id,
        space_key=params.space_key,
        title=params.title
    )
    return format_page_content(page, params.response_format)


@mcp.tool(
    name="confluence_get_page_text",
    annotations={
        "title": "Get Page Text Only",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def confluence_get_page_text(params: GetPageTextInput) -> str:
    """
    Get page content as plain text only (no HTML, no images).
    
    Use this when you only need the text content, especially
    for summarization with text-only models.
    
    Args:
        params: GetPageTextInput with page_id OR (space_key AND title)
        
    Returns:
        Plain text content of the page
    """
    client = get_client()
    return client.get_page_text_only(
        page_id=params.page_id,
        space_key=params.space_key,
        title=params.title
    )


@mcp.tool(
    name="confluence_get_page_images",
    annotations={
        "title": "Get Page Images",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def confluence_get_page_images(params: GetPageImagesInput) -> str:
    """
    Get all images from a Confluence page as base64.
    
    Use this to extract diagrams, flowcharts, architecture images,
    and other visual content for analysis with a vision model (VLM).
    
    Returns images as base64-encoded data that can be sent to
    Qwen3-VL or similar vision-language models.
    
    Args:
        params: GetPageImagesInput with page_id
        
    Returns:
        JSON array of images with base64 data and media types
    """
    client = get_client()
    images = client.get_page_images_base64(params.page_id)
    
    # Return summary + JSON
    result = {
        "page_id": params.page_id,
        "image_count": len(images),
        "images": images
    }
    
    return json.dumps(result, indent=2)


@mcp.tool(
    name="confluence_get_table",
    annotations={
        "title": "Get Table from Page",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def confluence_get_table(params: GetTableInput) -> str:
    """
    Extract a table from a Confluence page.
    
    Retrieves table data as structured rows and columns.
    Use table_index to specify which table if page has multiple.
    
    Args:
        params: GetTableInput with page_id and optional table_index
        
    Returns:
        Table data as markdown or JSON
    """
    client = get_client()
    tables = client.get_tables_from_page(params.page_id)
    
    if not tables:
        return "No tables found on this page."
    
    if params.table_index >= len(tables):
        return f"Table index {params.table_index} out of range. Page has {len(tables)} table(s)."
    
    table = tables[params.table_index]
    
    if params.response_format == ResponseFormat.JSON:
        return json.dumps({
            "page_id": params.page_id,
            "table_index": params.table_index,
            "total_tables": len(tables),
            "rows": table
        }, indent=2)
    
    result = [
        f"*Table {params.table_index + 1} of {len(tables)}*\n",
        format_table(table, params.response_format)
    ]
    return "\n".join(result)


@mcp.tool(
    name="confluence_update_table_cell",
    annotations={
        "title": "Update Table Cell",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def confluence_update_table_cell(params: UpdateTableCellInput) -> str:
    """
    Update a specific cell in a Confluence table.
    
    Modifies a single cell value in a table. Useful for
    updating status, values, or other tabular data.
    
    Args:
        params: UpdateTableCellInput with page_id, table/row/col indices, and new_value
        
    Returns:
        Confirmation of update with page details
    """
    client = get_client()
    result = client.update_table_cell(
        page_id=params.page_id,
        table_index=params.table_index,
        row_index=params.row_index,
        col_index=params.col_index,
        new_value=params.new_value
    )
    return json.dumps(result, indent=2)


@mcp.tool(
    name="confluence_create_page",
    annotations={
        "title": "Create Confluence Page",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def confluence_create_page(params: CreatePageInput) -> str:
    """
    Create a new Confluence page.
    
    Creates a new page in the specified space. Can optionally
    be nested under a parent page.
    
    Args:
        params: CreatePageInput with space_key, title, body, optional parent_id
        
    Returns:
        New page details including ID and URL
    """
    client = get_client()
    result = client.create_page(
        space_key=params.space_key,
        title=params.title,
        body=params.body,
        parent_id=params.parent_id
    )
    return json.dumps(result, indent=2)


@mcp.tool(
    name="confluence_update_page",
    annotations={
        "title": "Update Confluence Page",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def confluence_update_page(params: UpdatePageInput) -> str:
    """
    Update an existing Confluence page.
    
    Replaces the content of an existing page. The title
    can be changed or kept the same.
    
    Args:
        params: UpdatePageInput with page_id, title, body
        
    Returns:
        Updated page details including new version
    """
    client = get_client()
    result = client.update_page(
        page_id=params.page_id,
        title=params.title,
        body=params.body
    )
    return json.dumps(result, indent=2)


@mcp.tool(
    name="confluence_get_children",
    annotations={
        "title": "Get Child Pages",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def confluence_get_children(params: GetChildrenInput) -> str:
    """
    Get child pages of a parent page.
    
    Retrieves pages nested under a specific parent page.
    Useful for navigating page hierarchies.
    
    Args:
        params: GetChildrenInput with page_id and optional limit
        
    Returns:
        List of child pages with IDs and titles
    """
    client = get_client()
    children = client.get_child_pages(params.page_id, params.limit)
    
    if not children:
        return "No child pages found."
    
    lines = ["## Child Pages\n"]
    for child in children:
        lines.append(f"- **{child['title']}** (ID: {child['page_id']})")
        lines.append(f"  {child['url']}")
    
    return "\n".join(lines)


@mcp.tool(
    name="confluence_list_spaces",
    annotations={
        "title": "List Spaces",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def confluence_list_spaces(params: ListSpacesInput) -> str:
    """
    List all accessible Confluence spaces.
    
    Returns a list of spaces the user has access to.
    Use this to discover available spaces before searching.
    
    Args:
        params: ListSpacesInput with optional limit and response_format
        
    Returns:
        List of spaces with keys, names, and types
    """
    client = get_client()
    spaces = client.list_spaces(params.limit)
    return format_spaces(spaces, params.response_format)


@mcp.tool(
    name="confluence_test_connection",
    annotations={
        "title": "Test Connection",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def confluence_test_connection() -> str:
    """
    Test the Confluence connection.
    
    Verifies that credentials are valid and Confluence is accessible.
    Use this to troubleshoot connection issues.
    
    Returns:
        Connection status and server info
    """
    client = get_client()
    result = client.test_connection()
    return json.dumps(result, indent=2)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Confluence MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                       help="Transport method (default: stdio)")
    parser.add_argument("--port", type=int, default=8080,
                       help="Port for HTTP transport (default: 8080)")
    args = parser.parse_args()
    
    if args.transport == "http":
        mcp.run(transport="streamable_http", port=args.port)
    else:
        mcp.run()
EOF

echo "✅ server.py created"
echo ""
echo "File location: ~/.deepagents/agent/skills/confluence/mcp_server/server.py"
wc -l ~/.deepagents/agent/skills/confluence/mcp_server/server.py
