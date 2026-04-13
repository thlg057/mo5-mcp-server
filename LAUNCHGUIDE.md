# MO5 MCP Server

## Tagline
AI assistant for Thomson MO5 C development — 6809, CMOC, SDK, game patterns.

## Description
This MCP server connects AI coding agents (Claude Desktop, Cursor, Augment) to a curated knowledge base dedicated to Thomson MO5 development. It enables semantic search over technical documentation covering the 6809 CPU, the CMOC C compiler, the MO5 SDK, and game development patterns specific to the machine (VBL, sprites, collision detection, RLE compression, memory optimizations).

Beyond documentation, the server also exposes build tools: generate bootable floppy disk images, convert them to SD card format, and transform PNG images into C sprite headers, all without leaving your coding agent.

The server is part of a complete MO5 development toolchain:
- SDK MO5: a C library optimized for CMOC with sprite, video, and font support
- MO5 Project Template: a ready-to-use project scaffold with automated Makefile
- This MCP Server: the bridge that makes your AI agent an instant MO5 expert

A public RAG instance is available at retrocomputing-ai.cloud, no self-hosting required.

## Setup Requirements
- `RAG_BASE_URL` (required): URL of the MO5 RAG server. Use the public instance: https://retrocomputing-ai.cloud

## Category
Developer Tools

## Features
- Semantic search over Thomson MO5 official hardware and system documentation
- Access to CMOC C compiler reference (synthesized as Markdown)
- Full SDK MO5 module documentation queryable in natural language
- Game development how-tos: VBL sync, sprite transparency, RLE compression, collision detection, memory optimizations
- Automatic fallback search if no results found at the requested similarity threshold
- Generate bootable .fd floppy disk images directly from compiled .BIN files
- Convert .fd images to .sd format for SDDrive (SD card floppy emulator)
- Convert PNG images to C sprite headers (.h) for use with the MO5 SDK
- Preconfigured expert prompt: mo5_expert activates a full MO5 development assistant mode
- No self-hosting required, public RAG instance ready to use
- Published on npm, zero local installation needed (npx)
- Listed in the official MCP registry (registry.modelcontextprotocol.io)

## Getting Started
- "How do I initialize graphics mode on the MO5?"
- "What is the difference between mo5_sprite_bg.h and mo5_sprite.h?"
- "How do I implement VBL synchronization for a game loop?"
- "What are the memory constraints I need to respect on the MO5?"
- "Convert my player.png sprite to a C header for the MO5"
- Tool: semantic_search — Semantic search across all MO5 documentation (hardware, CMOC, SDK, how-tos). Automatic fallback if no results found at the requested threshold.
- Tool: get_chunk_context — Retrieves surrounding chunks when a result seems incomplete or truncated.
- Tool: list_official_docs — Lists all indexed official MO5 documents with summaries, tags, and download links.
- Tool: make_fd — Generates a bootable .fd floppy disk image from one or more CMOC-compiled .BIN files. Bootloader embedded, no external dependency.
- Tool: fd_to_sd — Converts a .fd floppy image to .sd format for use with SDDrive.
- Tool: png_to_mo5_sprite — Converts a PNG image to a C header file (.h) containing FORME and COULEUR arrays for the MO5 SDK.
- Prompt: mo5_expert — Activates a full MO5 expert assistant mode with guided tool usage order.

## Tags
mcp, mo5, thomson, retrocomputing, 6809, cmoc, c, game-development, rag, sdk, motorola-6809, retro, embedded, sprite, floppy-disk, sddrive

## Documentation URL
https://github.com/thlg057/mo5-mcp-server
