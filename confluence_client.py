cat > ~/.deepagents/agent/skills/confluence/mcp_server/confluence_client.py << 'EOF'
"""
Confluence Client Wrapper

Wraps atlassian-python-api for use in MCP server.
Handles authentication, SSL, and common operations.
"""

import os
import base64
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from atlassian import Confluence
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import httpx


@dataclass
class PageContent:
    """Structured page content."""
    page_id: str
    title: str
    space_key: str
    body_text: str
    body_html: str
    url: str
    version: int
    last_modified: str
    last_modifier: str
    image_urls: List[str]
    has_images: bool


@dataclass 
class SearchResult:
    """Search result item."""
    page_id: str
    title: str
    space_key: str
    space_name: str
    url: str
    excerpt: str
    last_modified: str


class ConfluenceClient:
    """
    Confluence API client wrapper.
    
    Handles:
    - Authentication (username/password from env)
    - SSL verification (disabled for self-signed certs)
    - Common operations (search, get, create, update)
    - Image extraction for VLM analysis
    """
    
    def __init__(self):
        """Initialize client with credentials from environment."""
        load_dotenv()
        
        self.base_url = os.getenv("CONFLUENCE_BASE_URL")
        self.username = os.getenv("CONFLUENCE_USERNAME")
        self.password = os.getenv("CONFLUENCE_PASSWORD")
        
        if not all([self.base_url, self.username, self.password]):
            raise ValueError(
                "Missing Confluence credentials. "
                "Set CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, CONFLUENCE_PASSWORD in .env"
            )
        
        self.client = Confluence(
            url=self.base_url,
            username=self.username,
            password=self.password,
            verify_ssl=False  # For self-signed certs
        )
    
    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================
    
    def search(
        self,
        query: str,
        space_key: Optional[str] = None,
        limit: int = 20,
        start: int = 0
    ) -> Dict[str, Any]:
        """
        Search Confluence pages.
        
        Args:
            query: Search text (CQL or simple text)
            space_key: Optional space to limit search
            limit: Max results (1-100)
            start: Offset for pagination
            
        Returns:
            Dict with results, total, and pagination info
        """
        # Build CQL query
        cql = f'text ~ "{query}"'
        if space_key:
            cql = f'space = "{space_key}" AND {cql}'
        
        results = self.client.cql(cql, limit=limit, start=start)
        
        items = []
        for item in results.get("results", []):
            content = item.get("content", item)
            items.append(SearchResult(
                page_id=content.get("id", ""),
                title=content.get("title", ""),
                space_key=content.get("space", {}).get("key", "") if isinstance(content.get("space"), dict) else "",
                space_name=content.get("space", {}).get("name", "") if isinstance(content.get("space"), dict) else "",
                url=f"{self.base_url}/wiki{content.get('_links', {}).get('webui', '')}",
                excerpt=item.get("excerpt", ""),
                last_modified=content.get("version", {}).get("when", "") if isinstance(content.get("version"), dict) else ""
            ))
        
        total = results.get("totalSize", len(items))
        
        return {
            "results": [vars(item) for item in items],
            "total": total,
            "start": start,
            "limit": limit,
            "has_more": (start + len(items)) < total
        }
    
    def list_spaces(self, limit: int = 50) -> List[Dict[str, str]]:
        """
        List all accessible Confluence spaces.
        
        Returns:
            List of spaces with key, name, and type
        """
        spaces = self.client.get_all_spaces(limit=limit)
        
        return [
            {
                "key": space.get("key", ""),
                "name": space.get("name", ""),
                "type": space.get("type", ""),
                "url": f"{self.base_url}/wiki/spaces/{space.get('key', '')}"
            }
            for space in spaces.get("results", [])
        ]
    
    # =========================================================================
    # PAGE OPERATIONS
    # =========================================================================
    
    def get_page(
        self,
        page_id: Optional[str] = None,
        space_key: Optional[str] = None,
        title: Optional[str] = None,
        expand: str = "body.storage,version,space"
    ) -> PageContent:
        """
        Get a Confluence page by ID or by space+title.
        
        Args:
            page_id: Page ID (preferred)
            space_key: Space key (required if using title)
            title: Page title (required if not using page_id)
            expand: Fields to expand
            
        Returns:
            PageContent with full page details
        """
        if page_id:
            page = self.client.get_page_by_id(page_id, expand=expand)
        elif space_key and title:
            page = self.client.get_page_by_title(space_key, title, expand=expand)
        else:
            raise ValueError("Must provide page_id OR (space_key AND title)")
        
        if not page:
            raise ValueError(f"Page not found: {page_id or f'{space_key}/{title}'}")
        
        body_html = page.get("body", {}).get("storage", {}).get("value", "")
        body_text = self._html_to_text(body_html)
        image_urls = self._extract_image_urls(body_html, page.get("id", ""))
        
        return PageContent(
            page_id=page.get("id", ""),
            title=page.get("title", ""),
            space_key=page.get("space", {}).get("key", ""),
            body_text=body_text,
            body_html=body_html,
            url=f"{self.base_url}/wiki{page.get('_links', {}).get('webui', '')}",
            version=page.get("version", {}).get("number", 1),
            last_modified=page.get("version", {}).get("when", ""),
            last_modifier=page.get("version", {}).get("by", {}).get("displayName", ""),
            image_urls=image_urls,
            has_images=len(image_urls) > 0
        )
    
    def get_page_text_only(
        self,
        page_id: Optional[str] = None,
        space_key: Optional[str] = None,
        title: Optional[str] = None
    ) -> str:
        """
        Get page content as plain text (no HTML, no images).
        Useful for text-only models like gpt-oss-120b.
        
        Returns:
            Plain text content
        """
        page = self.get_page(page_id, space_key, title)
        return page.body_text
    
    def get_child_pages(
        self,
        page_id: str,
        limit: int = 25
    ) -> List[Dict[str, str]]:
        """
        Get child pages of a parent page.
        
        Returns:
            List of child pages with id, title, url
        """
        children = self.client.get_page_child_by_type(page_id, type="page", limit=limit)
        
        return [
            {
                "page_id": child.get("id", ""),
                "title": child.get("title", ""),
                "url": f"{self.base_url}/wiki{child.get('_links', {}).get('webui', '')}"
            }
            for child in children.get("results", [])
        ]
    
    def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        parent_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create a new Confluence page.
        
        Args:
            space_key: Target space
            title: Page title
            body: Page content (HTML or plain text)
            parent_id: Optional parent page ID
            
        Returns:
            Dict with page_id, title, url
        """
        result = self.client.create_page(
            space=space_key,
            title=title,
            body=body,
            parent_id=parent_id
        )
        
        return {
            "page_id": result.get("id", ""),
            "title": result.get("title", ""),
            "url": f"{self.base_url}/wiki{result.get('_links', {}).get('webui', '')}",
            "message": f"Page '{title}' created successfully"
        }
    
    def update_page(
        self,
        page_id: str,
        title: str,
        body: str
    ) -> Dict[str, str]:
        """
        Update an existing Confluence page.
        
        Args:
            page_id: Page ID to update
            title: New title (can be same as old)
            body: New content (HTML)
            
        Returns:
            Dict with page_id, title, url, version
        """
        result = self.client.update_page(
            page_id=page_id,
            title=title,
            body=body
        )
        
        return {
            "page_id": result.get("id", ""),
            "title": result.get("title", ""),
            "url": f"{self.base_url}/wiki{result.get('_links', {}).get('webui', '')}",
            "version": result.get("version", {}).get("number", 0),
            "message": f"Page '{title}' updated successfully"
        }
    
    # =========================================================================
    # TABLE OPERATIONS
    # =========================================================================
    
    def get_tables_from_page(self, page_id: str) -> List[List[List[str]]]:
        """
        Extract all tables from a page.
        
        Returns:
            List of tables, each table is a list of rows,
            each row is a list of cell values.
        """
        page = self.get_page(page_id)
        soup = BeautifulSoup(page.body_html, "html.parser")
        
        tables = []
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = []
                for td in tr.find_all(["td", "th"]):
                    cells.append(td.get_text(strip=True))
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        
        return tables
    
    def update_table_cell(
        self,
        page_id: str,
        table_index: int,
        row_index: int,
        col_index: int,
        new_value: str
    ) -> Dict[str, Any]:
        """
        Update a specific cell in a table.
        
        Args:
            page_id: Page containing the table
            table_index: Which table (0-indexed)
            row_index: Which row (0-indexed)
            col_index: Which column (0-indexed)
            new_value: New cell value
            
        Returns:
            Dict with success status and updated page info
        """
        page = self.get_page(page_id)
        soup = BeautifulSoup(page.body_html, "html.parser")
        
        tables = soup.find_all("table")
        if table_index >= len(tables):
            raise ValueError(f"Table index {table_index} out of range (found {len(tables)} tables)")
        
        table = tables[table_index]
        rows = table.find_all("tr")
        if row_index >= len(rows):
            raise ValueError(f"Row index {row_index} out of range (found {len(rows)} rows)")
        
        cells = rows[row_index].find_all(["td", "th"])
        if col_index >= len(cells):
            raise ValueError(f"Column index {col_index} out of range (found {len(cells)} columns)")
        
        cells[col_index].string = new_value
        
        return self.update_page(page_id, page.title, str(soup))
    
    # =========================================================================
    # IMAGE OPERATIONS (for VLM)
    # =========================================================================
    
    def get_page_images_base64(self, page_id: str) -> List[Dict[str, str]]:
        """
        Get all images from a page as base64.
        For use with Qwen3-VL or other vision models.
        
        Returns:
            List of dicts with 'url', 'base64', 'media_type'
        """
        page = self.get_page(page_id)
        images = []
        
        for img_url in page.image_urls:
            try:
                img_data = self._download_image_base64(img_url)
                if img_data:
                    images.append(img_data)
            except Exception as e:
                # Skip failed images
                images.append({
                    "url": img_url,
                    "error": str(e),
                    "base64": None,
                    "media_type": None
                })
        
        return images
    
    def _download_image_base64(self, img_url: str) -> Dict[str, str]:
        """Download an image and return as base64."""
        # Handle relative URLs
        if img_url.startswith("/"):
            full_url = f"{self.base_url}{img_url}"
        else:
            full_url = img_url
        
        with httpx.Client(verify=False, auth=(self.username, self.password)) as client:
            response = client.get(full_url)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "image/png")
            base64_data = base64.b64encode(response.content).decode("utf-8")
            
            return {
                "url": img_url,
                "base64": base64_data,
                "media_type": content_type.split(";")[0]
            }
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()
        
        return soup.get_text(separator="\n", strip=True)
    
    def _extract_image_urls(self, html: str, page_id: str) -> List[str]:
        """Extract all image URLs from HTML content."""
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                urls.append(src)
        
        # Also check for ac:image (Confluence macro)
        for ac_img in soup.find_all("ac:image"):
            ri_att = ac_img.find("ri:attachment")
            if ri_att:
                filename = ri_att.get("ri:filename", "")
                if filename:
                    urls.append(f"/wiki/download/attachments/{page_id}/{filename}")
        
        return urls
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the Confluence connection.
        
        Returns:
            Dict with success status and server info
        """
        try:
            spaces = self.client.get_all_spaces(limit=1)
            return {
                "success": True,
                "message": "Connected to Confluence successfully",
                "base_url": self.base_url,
                "spaces_accessible": len(spaces.get("results", [])) > 0
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "base_url": self.base_url
            }
EOF

echo "✅ confluence_client.py created"
echo ""
echo "File location: ~/.deepagents/agent/skills/confluence/mcp_server/confluence_client.py"
wc -l ~/.deepagents/agent/skills/confluence/mcp_server/confluence_client.py
