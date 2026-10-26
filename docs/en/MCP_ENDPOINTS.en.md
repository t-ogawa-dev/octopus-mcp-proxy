[日本語](../MCP_ENDPOINTS.md) | English

# MCP Endpoint Detailed Guide

This document explains the detailed usage of each MCP server endpoint.

## Overview

This MCP server provides 2 main endpoints:

1. **GET /mcp** - Get Capabilities list
2. **POST /mcp** - Process MCP protocol requests

Tools are executed with `tools/call` on `POST /mcp`. The legacy endpoints `POST /tools/<tool_id>` and `POST /mcp/<subdomain>` have been removed.

All endpoints support subdomain-based routing.
The URLs below are for **Docker Compose (via Caddy, `https://`, no port number)**. If you
started directly with `python run.py` (no Docker), use `http://` + `:5000` instead. Since the
certificate is self-signed, `curl` needs `-k` (skip certificate verification).

The admin interface is accessible at `https://localhost/` (or `https://lvh.me/`).

## Subdomain Specification Methods

### Method 1: lvh.me Domain (Recommended)

`lvh.me` always points to 127.0.0.1, making it convenient for local development.

```
https://<subdomain>.lvh.me/mcp
```

**Examples:**

- `https://weather.lvh.me/mcp` - weather service MCP endpoint
- `https://myapi.lvh.me/mcp` - myapi service MCP endpoint
- `https://localhost/` - Admin interface (routed by path, so any hostname works)

### Method 2: Query Parameters

```
https://localhost/mcp?subdomain=<subdomain>
```

### Method 3: Custom Header

```bash
curl -k -H "X-Subdomain: myservice" https://localhost/mcp
```

## Authentication

All requests require an `Authorization` header:

```
Authorization: Bearer <USER_BEARER_TOKEN>
```

The account's Bearer token can be found on the account details page in the web admin interface.

---

## 1. GET /mcp - Get Capabilities

Retrieve the list of Tools available to the account.

### Request

```bash
curl -k -H "Authorization: Bearer abc123..." \
  https://myservice.lvh.me/mcp
```

### Response

```json
{
  "capabilities": {
    "tools": [
      {
        "name": "get_weather",
        "description": "Get current weather information",
        "inputSchema": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "Parameter: city",
              "default": "Tokyo"
            },
            "units": {
              "type": "string",
              "description": "Parameter: units",
              "default": "metric"
            }
          },
          "required": []
        }
      }
    ]
  },
  "serverInfo": {
    "name": "Weather Service",
    "version": "1.0.0"
  }
}
```

### Behavior

1. Identify service from subdomain
2. Identify account from Bearer token
3. Return only enabled Tools the account has permission for (same result as `tools/list`)
4. Each Tool's InputSchema is auto-generated from registered Body parameters
5. Internal settings such as URLs and headers are not returned

---

## 2. POST /mcp - MCP Protocol Requests

Process requests according to the standard MCP protocol.

With the `2026-07-28` protocol, clients can send stateless requests without an `initialize`
handshake or `Mcp-Session-Id` header. Use `server/discover` to check the supported protocol
versions. The `2024-11-05` initialize-and-session flow remains supported for backward compatibility.

### Supported Methods

- `server/discover` - Get supported protocol versions
- `initialize` - Initialize a session for legacy clients
- `tools/list` - Get Tool list (equivalent to GET /mcp)
- `tools/call` - Execute Tool

### 2.1 server/discover

#### Request

```bash
curl -k -X POST \
  -H "Authorization: Bearer abc123..." \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"server/discover"}' \
  https://myservice.lvh.me/mcp
```

#### Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersions": ["2026-07-28", "2024-11-05"]
  }
}
```

### 2.2 tools/list

#### Request

```bash
curl -k -X POST \
  -H "Authorization: Bearer abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }' \
  https://myservice.lvh.me/mcp
```

#### Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {
        "name": "get_weather",
        "description": "Get current weather information",
        "inputSchema": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "Parameter: city"
            }
          }
        }
      }
    ]
  }
}
```

### 2.3 tools/call

#### Request

```bash
curl -k -X POST \
  -H "Authorization: Bearer abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "get_weather",
      "arguments": {
        "city": "Tokyo"
      }
    }
  }' \
  https://myservice.lvh.me/mcp
```

#### Response (Success)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"data\": {\"temperature\": 25, \"condition\": \"sunny\"}}"
      }
    ]
  }
}
```

#### Response (Permission Error)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32000,
    "message": "Permission denied for tool: get_weather"
  }
}
```

---

## Error Code List

| Code   | Description                                    |
| ------ | ---------------------------------------------- |
| -32700 | Parse error - Invalid JSON                     |
| -32600 | Invalid Request - Subdomain not specified      |
| -32601 | Method not found - Unsupported method          |
| -32602 | Invalid params - Tool not found                |
| -32603 | Internal error - Execution error               |
| -32000 | Server error - Authentication/Permission error |
| -32001 | Server error - Service not found               |

---

## Usage Examples

### Example 1: Dify Configuration

```json
{
  "mcp_servers": {
    "weather_service": {
      "url": "https://weather.lvh.me/mcp",
      "auth": {
        "type": "bearer",
        "token": "YOUR_BEARER_TOKEN"
      }
    }
  }
}
```

### Example 2: Claude Desktop Configuration

```json
{
  "mcpServers": {
    "weather": {
      "url": "https://weather.lvh.me/mcp",
      "transport": {
        "type": "http"
      },
      "headers": {
        "Authorization": "Bearer YOUR_BEARER_TOKEN"
      }
    }
  }
}
```

### Example 3: Python Script Usage

```python
import requests

headers = {
    'Authorization': 'Bearer YOUR_BEARER_TOKEN',
    'Content-Type': 'application/json'
}

# Get Capabilities
response = requests.get(
    'https://myservice.lvh.me/mcp',
    headers=headers
)
capabilities = response.json()
print(capabilities)

# Execute Tool (MCP protocol tools/call)
response = requests.post(
    'https://myservice.lvh.me/mcp',
    headers=headers,
    json={
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {'name': 'get_weather', 'arguments': {'city': 'Tokyo'}},
    }
)
result = response.json()
print(result)
```

### Example 4: Complete Workflow with cURL

```bash
# 1. Get Capabilities
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  https://myservice.lvh.me/mcp

# 2. Execute Tool via MCP protocol
curl -k -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_weather",
      "arguments": {"city": "Tokyo"}
    }
  }' \
  https://myservice.lvh.me/mcp
```

---

## Implementation Flow

### GET /mcp or POST /mcp (tools/list)

```
1. Receive request
   ↓
2. Extract subdomain (lvh.me, query parameter, header)
   ↓
3. Verify Bearer token
   ↓
4. Search for Service by subdomain
   ↓
5. Get Capabilities with permissions by account ID and Service ID
   ↓
6. Format and return Capability list
```

### POST /mcp (tools/call)

```
1. Receive request
   ↓
2. Extract subdomain
   ↓
3. Verify Bearer token
   ↓
4. Search for Service by subdomain
   ↓
5. Search for Capability by params.name
   ↓
6. Check account permissions
   ↓
7. With permission → Execute Capability
   Without permission → JSON-RPC error response
   ↓
8. Return result in JSON-RPC format
```

---

## Troubleshooting

### Subdomain Not Recognized

**Problem:** Subdomain is not recognized when accessing via lvh.me

**Solution:**

1. Check DNS settings (`ping myservice.lvh.me` should return 127.0.0.1)
2. Use query parameter instead: `?subdomain=myservice`
3. Confirm you're using the right scheme/port: `https://myservice.lvh.me/mcp` via Docker
   Compose (Caddy), or `http://myservice.lvh.me:5000/mcp` when running directly with
   `python run.py`
4. If `curl` reports a certificate error, add `-k` (the certificate is self-signed)

### Authentication Error

**Problem:** `Invalid bearer token` error

**Solution:**

1. Verify Bearer token (Web admin interface > Account details)
2. Check `Authorization: Bearer ` format (includes space)
3. Regenerate token

### Permission Error

**Problem:** `Permission denied for tool: xxx`

**Solution:**

1. Check account permissions in web admin interface
2. Add the relevant Capability in Account details > Permission management

### Tool Not Found Error

**Problem:** `Tool not found: xxx`

**Solution:**

1. Confirm Capability is properly registered
2. Check for spelling errors in Tool name
3. Verify accessing the correct service (subdomain)
