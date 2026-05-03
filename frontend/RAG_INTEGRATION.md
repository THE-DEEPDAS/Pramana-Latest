# RAG Backend Integration Guide

This guide explains how to integrate PowerMind frontend with your RAG (Retrieval-Augmented Generation) backend.

## Architecture Overview

```
Client (PowerMind Frontend)
    ↓
    ├─→ /api/chat (Next.js API Route)
    │   ↓
    └─→ Your RAG Backend
        ├─ Vector Database (Pinecone, Weaviate, etc.)
        ├─ Document Parser
        └─ LLM (OpenAI, Llama, etc.)
```

## Backend Requirements

Your RAG backend should expose the following endpoints:

### 1. Upload Documents Endpoint

**POST `/api/documents/upload`**

**Request:**
```json
{
  "file": "binary file content",
  "filename": "document.pdf"
}
```

**Response:**
```json
{
  "id": "doc_123",
  "filename": "document.pdf",
  "status": "indexing",
  "message": "Document uploaded and queued for processing"
}
```

### 2. Chat/Query Endpoint

**POST `/api/chat/query`**

**Request:**
```json
{
  "query": "What is in the document?",
  "documentIds": ["doc_123"],
  "topK": 5,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "answer": "The document contains...",
  "sources": [
    {
      "documentId": "doc_123",
      "filename": "document.pdf",
      "relevance": 0.95,
      "excerpt": "..."
    }
  ],
  "metadata": {
    "processingTime": 1234,
    "model": "gpt-3.5-turbo"
  }
}
```

### 3. List Documents Endpoint

**GET `/api/documents`**

**Response:**
```json
{
  "documents": [
    {
      "id": "doc_123",
      "filename": "document.pdf",
      "uploadedAt": "2024-05-02T10:00:00Z",
      "status": "indexed",
      "size": 1024000
    }
  ]
}
```

### 4. Delete Document Endpoint

**DELETE `/api/documents/{documentId}`**

**Response:**
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

## Frontend Integration

### Update API Service

Create `lib/api.ts`:

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL

export async function uploadDocument(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_URL}/documents/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) throw new Error('Upload failed')
  return response.json()
}

export async function queryRAG(query: string, documentIds: string[]) {
  const response = await fetch(`${API_URL}/chat/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      documentIds,
      topK: 5,
    }),
  })

  if (!response.ok) throw new Error('Query failed')
  return response.json()
}

export async function getDocuments() {
  const response = await fetch(`${API_URL}/documents`)
  if (!response.ok) throw new Error('Failed to fetch documents')
  return response.json()
}

export async function deleteDocument(documentId: string) {
  const response = await fetch(`${API_URL}/documents/${documentId}`, {
    method: 'DELETE',
  })

  if (!response.ok) throw new Error('Delete failed')
  return response.json()
}
```

### Update FileUploadSection Component

```typescript
import { uploadDocument } from '@/lib/api'

// In handleFileSelect or addFiles:
for (const file of uploadedFiles) {
  try {
    const result = await uploadDocument(file)
    setFiles((prev) =>
      prev.map((f) =>
        f.id === file.id
          ? { ...f, status: 'completed', backendId: result.id }
          : f
      )
    )
  } catch (error) {
    setFiles((prev) =>
      prev.map((f) =>
        f.id === file.id ? { ...f, status: 'failed' } : f
      )
    )
  }
}
```

### Update ChatInterface Component

```typescript
import { queryRAG } from '@/lib/api'

// In handleSendMessage:
const handleSendMessage = async () => {
  if (!input.trim()) return

  const userMessage: Message = {
    id: Date.now().toString(),
    type: 'user',
    content: input,
    timestamp: new Date(),
  }

  setMessages((prev) => [...prev, userMessage])
  setInput('')
  setIsLoading(true)

  try {
    const response = await queryRAG(input, documentIds)
    
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: response.answer,
      timestamp: new Date(),
    }
    
    setMessages((prev) => [...prev, assistantMessage])
  } catch (error) {
    const errorMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: 'Sorry, I encountered an error. Please try again.',
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, errorMessage])
  } finally {
    setIsLoading(false)
  }
}
```

## Recommended Backend Stacks

### Python Stack (Popular for RAG)

```
FastAPI (Web Framework)
├─ LangChain (RAG Framework)
├─ OpenAI / Ollama (LLM)
├─ Pinecone / Chroma (Vector DB)
└─ PyPDF2 / python-docx (Document Parsing)
```

**Example FastAPI endpoint:**

```python
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from langchain import OpenAI, PromptTemplate
import pinecone

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    documentIds: list[str]
    topK: int = 5

@app.post("/api/chat/query")
async def query_rag(request: QueryRequest):
    # Initialize Pinecone
    pinecone.init(api_key="...", environment="...")
    index = pinecone.Index("documents")
    
    # Get embeddings
    embeddings = OpenAI.embeddings(request.query)
    
    # Retrieve relevant docs
    results = index.query(
        vector=embeddings,
        top_k=request.topK,
        include_metadata=True
    )
    
    # Generate response with LLM
    context = "\n".join([r.metadata["content"] for r in results])
    
    llm = OpenAI(temperature=0.7)
    response = llm(f"Context: {context}\n\nQ: {request.query}\n\nA:")
    
    return {
        "answer": response,
        "sources": [
            {
                "documentId": r.metadata["doc_id"],
                "relevance": r.score
            }
            for r in results
        ]
    }
```

### JavaScript/Node Stack

```
Express.js / Fastify (Server)
├─ LangChain JS (RAG)
├─ OpenAI API (LLM)
├─ Pinecone (Vector DB)
└─ pdf-parse (PDF handling)
```

**Example Express endpoint:**

```javascript
const express = require('express')
const { OpenAIEmbeddings } = require('langchain/embeddings/openai')
const { Pinecone } = require('@pinecone-database/pinecone')

const app = express()
const pinecone = new Pinecone()

app.post('/api/chat/query', async (req, res) => {
  const { query, documentIds } = req.body
  
  // Get embeddings
  const embeddings = new OpenAIEmbeddings()
  const embedding = await embeddings.embedQuery(query)
  
  // Query Pinecone
  const index = pinecone.Index('documents')
  const results = await index.query({
    vector: embedding,
    topK: 5,
    filter: { doc_id: { $in: documentIds } }
  })
  
  // Generate response
  const answer = await generateResponse(query, results)
  
  res.json({
    answer,
    sources: results.matches.map(m => ({
      documentId: m.metadata.doc_id,
      relevance: m.score
    }))
  })
})
```

## Environment Variables

Create `.env.local`:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional Backend Credentials
API_KEY=your_api_key
```

## Testing Integration

### 1. Test Upload

```bash
curl -X POST http://localhost:3000/api/upload \
  -F "file=@document.pdf"
```

### 2. Test Query

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is this about?"}'
```

### 3. Use Thunder Client or Postman

- Import endpoints from your backend
- Test with sample documents
- Verify response format

## Common Issues

### CORS Errors

Add CORS headers to your backend:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Timeout Issues

Increase timeout for long-running queries:

```typescript
const response = await fetch(`${API_URL}/chat/query`, {
  method: 'POST',
  
  timeout: 30000, // 30 seconds
})
```

### File Size Limits

Configure in Next.js:

```javascript
// next.config.js
module.exports = {
  api: {
    bodyParser: {
      sizeLimit: '50mb',
    },
  },
}
```

## Performance Tips

1. **Batch queries** when possible
2. **Cache embeddings** to avoid recomputation
3. **Use async processing** for large documents
4. **Implement pagination** for document lists
5. **Add rate limiting** to prevent abuse

## Security

- ✅ Validate all file uploads
- ✅ Sanitize user input
- ✅ Use HTTPS in production
- ✅ Implement authentication
- ✅ Set API rate limits
- ✅ Store API keys securely
- ✅ Validate file types and sizes

## Monitoring

Add logging to track:
- Query latency
- Document processing time
- Error rates
- User activity

---

Need help? Check:
- [LangChain Docs](https://langchain.readthedocs.io/)
- [Pinecone Docs](https://docs.pinecone.io/)
- [Next.js API Routes](https://nextjs.org/docs/api-routes/introduction)
