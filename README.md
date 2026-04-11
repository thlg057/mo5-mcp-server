# MO5 MCP Server (RAG Connector)

This MCP server (Model Context Protocol) acts as a bridge between modern AI agents (Claude Desktop, Augment, Cursor) and the Thomson MO5 ecosystem.  
It allows access to an expert knowledge base and manipulation of MO5 heritage files.

It provides semantic search tools, documentation resources, and expert prompts to facilitate development around the Thomson MO5 microcomputer.

## 🏗️ MO5 Development Ecosystem

This server is part of a complete toolchain for modern 6809 development:

- **SDK MO5** : https://github.com/thlg057/sdk_mo5  
  C library optimized for CMOC.
- **MO5 Project Template** : https://github.com/thlg057/mo5_template  
  Project template with automated Makefile.
- **This MCP Server** : The assistant that connects everything, answers technical questions, and generates assets.

## 🌐 RAG Infrastructure (Artificial Intelligence)

The server relies on a Retrieval-Augmented Generation architecture to provide accurate answers based on real technical documentation.

## 🚀 Features

- **Semantic Search**: Intelligent search within the MO5 technical documentation.
- **Resources Explorer**: Direct access to the list of documents, tags, and indexing status.
- **Expert Prompt**: A preconfigured "Expert Thomson MO5" mode for the AI.
- **Build Tools**: Generate bootable `.fd` disk images, convert `.fd` to `.sd` for SDDrive, and convert PNG assets to C sprite headers.
- **Robustness**: Native handling of timeouts (30s) and retry policy for unstable network environments (NAS).

---

## 🌐 Public MO5 RAG Server

The MO5 RAG server is now **publicly deployed and accessible on the Internet**.

👉 https://retrocomputing-ai.cloud/

This MCP server is designed to work **out of the box** with the public RAG instance.

For most users, this means:
- no RAG server to install
- no Docker setup
- no local infrastructure to maintain

Simply configure the MCP server to point to the public URL and start using it from your coding agent.

Self-hosting a RAG server is still possible if you want to:
- experiment with the internals
- customize the knowledge base
- run everything offline

But it is no longer required for normal usage.

## 🛠️ Requirements

- Node.js (v18 or higher)
- Python 3 with [Pillow](https://pypi.org/project/Pillow/) (`pip install Pillow`) — required only for the `png_to_mo5_sprite` tool.

The official public MO5 RAG server is available at: https://retrocomputing-ai.cloud/

You can use this public instance directly, there is no need to host your own RAG server.

## 📦 Installation & Setup

### Option 1 — Via npx (recommended, no installation required)

Configure your agent to run the server directly from npm. No `git clone` or `npm install` needed.

```json
{
  "mcpServers": {
    "mo5-server": {
      "command": "npx",
      "args": [
        "-y",
        "@thlg057/mo5-rag-mcp"
      ],
      "env": {
        "RAG_BASE_URL": "https://retrocomputing-ai.cloud"
      }
    }
  }
}
```

### Option 2 — From source

```bash
git clone https://github.com/thlg057/mo5-mcp-server.git
cd mo5-mcp-server
npm install
```

Then configure your agent:

```json
{
  "mcpServers": {
    "mo5-rag": {
      "command": "node",
      "args": ["C:\\your\\path\\to\\mo5-mcp-server\\index.js"],
      "env": {
        "RAG_BASE_URL": "https://retrocomputing-ai.cloud"
      }
    }
  }
}
```

> Note for Windows: Use double backslashes `\\` or single slashes `/` in the path to avoid JSON formatting errors.

## 🤖 Integration into an Agent (e.g., Augment, Claude Desktop)

Add one of the configurations above to your MCP configuration file (e.g., `augment_config.json` or `claude_desktop_config.json`).

## 🧪 Local Testing

It is recommended to test the server before integration to ensure proper communication with the RAG API.

### Via the MCP Inspector (Recommended)

```bash
# Windows (PowerShell)
$env:RAG_BASE_URL="https://retrocomputing-ai.cloud"; npx @modelcontextprotocol/inspector node index.js
```

### Via Command Line

```bash
echo {"jsonrpc":"2.0","method":"tools/list","id":1} | node index.js
```

## 📂 Project Structure

- `index.js`: Main source code of the MCP server.
- `scripts/`: Python scripts for build tools (`makefd.py`, `fd2sd.py`, `png2mo5.py`).
- `package.json`: Dependencies (MCP SDK).
- `.gitignore`: Ignores `node_modules` and environment files.

## 🏗️ MO5 Development Ecosystem

This server is part of a suite of tools designed to modernize development on the Thomson MO5:

- **[SDK MO5](https://github.com/thlg057/sdk_mo5)**: A C library for CMOC that provides easy access to the hardware (video, keyboard, monitor) without writing assembly.
- **[Project Template](https://github.com/thlg057/mo5_template)**: A ready-to-use project skeleton with an automated Makefile that compiles, links the SDK, and generates a bootable disk image in a single command. Also includes this MCP server as a dev dependency so your coding agent has full context and build capabilities out of the box.

This project is part of the digital preservation ecosystem for the Thomson MO5 microcomputer.