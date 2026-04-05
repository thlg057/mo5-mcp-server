#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  ListPromptsRequestSchema,
  GetPromptRequestSchema
} from "@modelcontextprotocol/sdk/types.js";

// Récupération de l'URL du NAS avec fallback
const RAG_BASE_URL = process.env.RAG_BASE_URL ?? "http://nas:8080";

/**
 * Utilitaire fetch avec Timeout et Retry
 */
async function fetchWithRetry(url, options = {}, retries = 3, backoff = 1000) {
  const { timeout = 30000, ...fetchOptions } = options;

  for (let i = 0; i < retries; i++) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal
      });
      
      clearTimeout(id);
      return response;
    } catch (err) {
      clearTimeout(id);
      const isLastAttempt = i === retries - 1;
      
      if (isLastAttempt) throw err;
      
      // Attente exponentielle avant la prochaine tentative
      const delay = backoff * Math.pow(2, i);
      console.error(`Tentative ${i + 1} échouée, nouvel essai dans ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

/**
 * Initialisation du serveur MCP
 */
const server = new Server(
  {
    name: "mo5-rag-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
      prompts: {},
    },
  }
);

/* ============================================================
   TOOLS (Outils actionnables par l'IA)
============================================================ */

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "semantic_search",
        description: "Recherche sémantique dans la documentation MO5 (base de connaissances)",
        inputSchema: {
          type: "object",
          properties: {
            query: { type: "string", description: "La question ou les mots-clés de recherche" },
            tags: { type: "array", items: { type: "string" }, description: "Filtres par thématiques" },
            maxResults: { type: "number", default: 5 },
            minSimilarityScore: { type: "number", default: 0.7 },
          },
          required: ["query"],
        },
      },
      {
        name: "list_official_docs",
        description: "Liste les documents officiels et de développement Thomson MO5 (manuels, guides techniques). Utile pour identifier quelles ressources existent avant de faire une recherche sémantique ciblée, ou pour fournir un lien de téléchargement direct à l'utilisateur.",
        inputSchema: {
          type: "object",
          properties: {
            tag: { type: "string", description: "Filtrer par tag (ex: 'basic', 'assembleur', 'hardware'). Optionnel." },
          },
          required: [],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // --- Tool : semantic_search ---
  if (name === "semantic_search") {
    try {
      const res = await fetchWithRetry(`${RAG_BASE_URL}/api/Search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: args.query,
          tags: args.tags,
          maxResults: args.maxResults ?? 5,
          minSimilarityScore: args.minSimilarityScore ?? 0.7,
          includeMetadata: true,
        }),
        timeout: 30000
      }, 3);

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Erreur API NAS (${res.status}): ${errorText}`);
      }

      const data = await res.json();
      console.error("DEBUG NAS DATA:", JSON.stringify(data).substring(0, 200));

      const results = data.results || [];
      const text = results.length > 0
        ? results.map(r => `${r.content}\n(Source: ${r.document?.fileName}, score: ${r.similarityScore})`).join("\n\n")
        : "L'API a répondu avec succès mais aucun résultat n'a été trouvé.";

      return { content: [{ type: "text", text }] };

    } catch (error) {
      console.error("Erreur semantic_search:", error.message);
      return {
        content: [{ type: "text", text: `Désolé, le serveur de recherche ne répond pas après plusieurs tentatives (Erreur: ${error.message}).` }],
        isError: true
      };
    }
  }

  // --- Tool : list_official_docs ---
  if (name === "list_official_docs") {
    try {
      const res = await fetchWithRetry(`${RAG_BASE_URL}/api/documents/official`, {
        timeout: 15000
      }, 3);

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Erreur API NAS (${res.status}): ${errorText}`);
      }

      const docs = await res.json();

      const filtered = args.tag
        ? docs.filter(d => d.tags?.some(t => t.toLowerCase().includes(args.tag.toLowerCase())))
        : docs;

      const text = filtered.length > 0
        ? filtered.map(d =>
            `**${d.title ?? d.fileName}** (ID: ${d.id})\n` +
            `Tags: ${(d.tags ?? []).join(", ") || "aucun"}\n` +
            `Résumé: ${d.summary ?? "N/A"}\n` +
            `📥 Télécharger: ${RAG_BASE_URL}/api/documents/official/${d.id}/file`
          ).join("\n\n")
        : "Aucun document officiel trouvé.";

      return { content: [{ type: "text", text }] };

    } catch (error) {
      console.error("Erreur list_official_docs:", error.message);
      return {
        content: [{ type: "text", text: `Impossible de récupérer les documents officiels (Erreur: ${error.message}).` }],
        isError: true
      };
    }
  }

  throw new Error(`Outil inconnu : ${name}`);
});

/* ============================================================
   RESOURCES (Données consultables)
============================================================ */

server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      { uri: "documents://list", name: "Liste des documents", description: "Liste tous les fichiers indexés (chunks)" },
      { uri: "documents://tags", name: "Tags", description: "Liste des thématiques disponibles" },
      { uri: "documents://official", name: "Documentation officielle MO5", description: "Manuels, guides et docs de développement officiels Thomson MO5" },
      { uri: "ingestion://status", name: "Statut", description: "État de santé de l'indexation RAG" },
    ],
  };
});

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const uri = request.params.uri;

  try {
    let text = "";

    if (uri === "documents://list") {
      const res = await fetch(`${RAG_BASE_URL}/api/Documents`);
      const docs = await res.json();
      text = docs.map((d) => `- ${d.fileName} (ID: ${d.id})`).join("\n");
    }
    else if (uri === "documents://tags") {
      const res = await fetch(`${RAG_BASE_URL}/api/Documents/tags`);
      const tags = await res.json();
      text = tags.map((t) => t.name).join(", ");
    }
    else if (uri === "documents://official") {
      const res = await fetch(`${RAG_BASE_URL}/api/documents/official`);
      const docs = await res.json();
      text = docs.map(d =>
        `## ${d.title ?? d.fileName}\n` +
        `- ID: ${d.id}\n` +
        `- Tags: ${(d.tags ?? []).join(", ") || "aucun"}\n` +
        `- Résumé: ${d.summary ?? "N/A"}\n` +
        `- Modifié: ${d.lastModified}\n` +
        `- 📥 Télécharger: ${RAG_BASE_URL}/api/documents/official/${d.id}/file`
      ).join("\n\n");
    }
    else if (uri.startsWith("documents://official/")) {
      const id = uri.replace("documents://official/", "");
      const res = await fetch(`${RAG_BASE_URL}/api/documents/official/${id}`);
      if (!res.ok) throw new Error("Document officiel introuvable");
      const doc = await res.json();
      text =
        `# ${doc.title ?? doc.fileName}\n\n` +
        `${doc.summary ?? ""}\n\n` +
        `Tags: ${(doc.tags ?? []).join(", ") || "aucun"}\n` +
        `Fichier: ${doc.fileName}\n` +
        `Modifié: ${doc.lastModified}\n` +
        `📥 Télécharger: ${RAG_BASE_URL}/api/documents/official/${doc.id}/file`;
    }
    else if (uri === "ingestion://status") {
      const res = await fetch(`${RAG_BASE_URL}/api/Index/status`);
      const status = await res.json();
      text = JSON.stringify(status, null, 2);
    }
    else if (uri.startsWith("documents://")) {
      const id = uri.replace("documents://", "");
      const res = await fetch(`${RAG_BASE_URL}/api/Documents/${id}`);
      if (!res.ok) throw new Error("Document introuvable");
      const doc = await res.json();
      text = `# ${doc.title}\n\n${doc.content}\n\nSource: ${doc.fileName}`;
    }
    else {
      throw new Error("Ressource inconnue");
    }

    return {
      contents: [
        {
          uri: uri,
          mimeType: "text/plain",
          text: text
        }
      ]
    };

  } catch (error) {
    throw new Error(`Erreur ressource (${uri}) : ${error.message}`);
  }
});

/* ============================================================
   PROMPTS (Modèles de conversation)
============================================================ */

server.setRequestHandler(ListPromptsRequestSchema, async () => {
  return {
    prompts: [
      {
        name: "mo5_expert",
        description: "Assistant expert Thomson MO5 utilisant la base documentaire.",
      },
    ],
  };
});

server.setRequestHandler(GetPromptRequestSchema, async (request) => {
  if (request.params.name !== "mo5_expert") {
    throw new Error("Prompt inconnu");
  }

  return {
    description: "Expert MO5",
    messages: [
      {
        role: "user",
        content: {
          type: "text",
          text: `Tu es un expert du micro-ordinateur Thomson MO5.
Tu as accès à deux types de sources :
1. **semantic_search** : recherche sémantique dans les chunks indexés de la base documentaire.
2. **list_official_docs** : liste les documents officiels disponibles (manuels, guides de développement), avec résumés, tags et liens de téléchargement. Utilise cet outil en premier quand l'utilisateur cherche une référence précise (ex: "le manuel BASIC", "la doc du 6809"), puis oriente ta recherche sémantique avec les tags pertinents.
Cite toujours tes sources (fileName, score de similarité) et propose les liens de téléchargement quand c'est pertinent.`
        }
      }
    ]
  };
});

/* ============================================================
   DÉMARRAGE DU SERVEUR
============================================================ */

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Serveur MCP MO5-RAG démarré sur STDIO");
}

main().catch((error) => {
  console.error("Erreur fatale au démarrage:", error);
  process.exit(1);
});