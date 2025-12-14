cat > ~/.deepagents/agent/skills/confluence/SKILL.md << 'EOF'
---
name: confluence
description: Search, read, and manage Confluence documentation. Use for finding technical docs, architecture diagrams, guides, and updating pages or tables.
version: 1.0.0
author: deepagents
---

# Confluence Skill

## Overview

This skill provides full access to Confluence for searching documentation, reading pages (including visual content like diagrams and flowcharts), and managing content.

## When to Use This Skill

Use Confluence tools when the user:
- Asks about internal documentation, guides, or technical specs
- Needs to find information in Confluence (search)
- Wants to read a specific page or document
- Asks about architecture diagrams, flowcharts, or visual documentation
- Needs to update or create documentation
- References "Confluence", "docs", "wiki", or "documentation"

## Available Tools

| Tool | Purpose | Read/Write |
|------|---------|------------|
| `confluence_search` | Search pages by text query | Read |
| `confluence_get_page` | Get full page content with metadata | Read |
| `confluence_get_page_text` | Get page as plain text only | Read |
| `confluence_get_page_images` | Get images as base64 for visual analysis | Read |
| `confluence_get_table` | Extract table data from a page | Read |
| `confluence_update_table_cell` | Update a specific cell in a table | Write |
| `confluence_create_page` | Create a new page | Write |
| `confluence_update_page` | Update existing page content | Write |
| `confluence_get_children` | Get child pages of a parent | Read |
| `confluence_list_spaces` | List all accessible spaces | Read |
| `confluence_test_connection` | Verify Confluence connection | Read |

## Multi-Model Routing

This skill works with multiple models based on content type:

### For Text Content
- **Qwen3-Coder**: Tool calling, searching, fetching pages
- **gpt-oss-120b**: Summarization, explanations (text-only, no tools)

### For Visual Content (Diagrams, Flowcharts, Architecture)
- **Qwen3-VL**: Analyzing images extracted from pages

### Routing Logic
```
User asks about documentation
         │
         ▼
    ┌─────────────┐
    │ Search/Fetch │ ← Use Qwen3-Coder (tool calling)
    │ Confluence   │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ Page has    │
    │ images?     │
    └──────┬──────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
   [YES]       [NO]
     │           │
     ▼           ▼
┌─────────┐  ┌─────────┐
│ Extract │  │ Text    │
│ Images  │  │ Summary │
│ → VLM   │  │ → LLM   │
└─────────┘  └─────────┘
```

## Usage Examples

### Example 1: Search for Documentation
```
User: "Find the deployment guide in Confluence"

Agent action:
1. Call confluence_search(query="deployment guide")
2. Return results with titles and links
```

### Example 2: Read a Page
```
User: "What does the API authentication page say?"

Agent action:
1. Call confluence_search(query="API authentication")
2. Call confluence_get_page(page_id=<found_id>)
3. Summarize content for user
```

### Example 3: Analyze Architecture Diagram
```
User: "Explain the system architecture diagram on the Infrastructure page"

Agent action:
1. Call confluence_get_page(space_key="INFRA", title="System Architecture")
2. Check if page has_images=True
3. Call confluence_get_page_images(page_id=<id>)
4. Send images to Qwen3-VL for analysis
5. Return visual explanation to user
```

### Example 4: Update a Table
```
User: "Update the status of server-01 to 'deployed' in the inventory table"

Agent action:
1. Call confluence_search(query="inventory table server")
2. Call confluence_get_table(page_id=<id>)
3. Find row with server-01, note row/col index
4. Call confluence_update_table_cell(page_id, row_index, col_index, "deployed")
```

### Example 5: Create Documentation
```
User: "Create a new page for the Q4 release notes in the DEV space"

Agent action:
1. Call confluence_create_page(space_key="DEV", title="Q4 Release Notes", body=<content>)
2. Return new page URL to user
```

## Handling Visual Content

When a page contains diagrams, flowcharts, or architecture images:

1. **Detect**: Check `has_images` field in page response
2. **Extract**: Use `confluence_get_page_images` to get base64 images
3. **Analyze**: Send to Qwen3-VL with appropriate prompt
4. **Respond**: Combine visual analysis with text content

### Visual Analysis Prompt Template

When sending images to VLM, use this prompt structure:
```
Analyze this technical diagram/flowchart from Confluence.

Context: [Page title and any surrounding text]

Please describe:
1. What type of diagram this is (architecture, flowchart, sequence, etc.)
2. The main components or steps shown
3. The relationships or flow between components
4. Any important details or annotations

Be specific and technical in your explanation.
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing credentials" | .env not configured | Check CONFLUENCE_BASE_URL, USERNAME, PASSWORD |
| "Page not found" | Invalid page_id or title | Use search first to find correct page |
| "Permission denied" | User lacks access | Check space permissions in Confluence |
| "SSL error" | Certificate issue | verify_ssl=False is already set |

## MCP Server

The Confluence MCP server runs as a subprocess and exposes all tools via MCP protocol.

**Location:** `~/.deepagents/agent/skills/confluence/mcp_server/server.py`

**Start command:**
```bash
python ~/.deepagents/agent/skills/confluence/mcp_server/server.py
```

**Environment variables required:**
- `CONFLUENCE_BASE_URL` - Confluence server URL
- `CONFLUENCE_USERNAME` - Username for authentication  
- `CONFLUENCE_PASSWORD` - Password for authentication
EOF

echo "✅ SKILL.md created"
echo ""
echo "File location: ~/.deepagents/agent/skills/confluence/SKILL.md"
wc -l ~/.deepagents/agent/skills/confluence/SKILL.md
