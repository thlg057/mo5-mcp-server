# MO5 MCP Server (RAG Connector)

This MCP (Model Context Protocol) server allows an AI agent (like Claude Desktop, Augment, or Cursor) to interact with the MO5 project knowledge base via a RAG (Retrieval-Augmented Generation) API.

It provides semantic search tools, documentation resources, and expert prompts to facilitate development around the Thomson MO5 microcomputer.

## 🚀 Features

- **Semantic Search**: Intelligent search within the MO5 technical documentation.
- **Resources Explorer**: Direct access to the list of documents, tags, and indexing status.
- **Expert Prompt**: A preconfigured "Expert Thomson MO5" mode for the AI.
- **Robustness**: Native handling of timeouts (30s) and retry policy for unstable network environments (NAS).

## 🛠️ Requirements

- Node.js (v18 or higher)
- A functional MO5 RAG API server (official url comming soon).

## 📦 Installation & Setup

### Clone the repository

```bash
git clone https://github.com/votre-compte/mo5-mcp-server.git
cd mo5-mcp-server
```

### Download dependencies

```bash
npm install
```

## 🤖 Integration into an Agent (e.g., Augment, Claude Desktop)

To add this server to your agent, edit your MCP configuration file (e.g., `augment_config.json` or `claude_desktop_config.json`) with the following JSON:

```json
{
  "mcpServers": {
    "mo5-rag": {
      "command": "node",
      "args": ["C:\\your\\path\\to\\mo5-mcp-server\\index.js"],
      "env": {
        "RAG_BASE_URL": "http://nas:8080"
      }
    }
  }
}
```

> Note for Windows: Use double backslashes `\\` or single slashes `/` in the path to avoid JSON formatting errors.

## 🧪 Local Testing

It is recommended to test the server before integration to ensure proper communication with the RAG API.

### Via the MCP Inspector (Recommended)

```bash
# Windows (PowerShell)
$env:RAG_BASE_URL="http://nas:8080"; npx @modelcontextprotocol/inspector node index.js
```

### Via Command Line

```bash
echo {"jsonrpc":"2.0","method":"tools/list","id":1} | node index.js
```

## 📂 Project Structure

- `index.js`: Main source code of the MCP server.
- `package.json`: Dependencies (MCP SDK).
- `.gitignore`: Ignores `node_modules` and environment files.

This project is part of the digital preservation ecosystem for the Thomson MO5 microcomputer.