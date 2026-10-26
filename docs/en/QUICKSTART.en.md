[日本語](../QUICKSTART.md) | English

This guide explains the quickest way to start and test the MCP server.

## 1. Start Server (1 minute)

```bash
docker compose up -d
```

Wait for startup:

```bash
docker compose logs -f web
```

Once you see `Default admin user created`, the server is ready.

## 2. Login to Admin Interface (1 minute)

1. Open **https://localhost/** in your browser (no port number; you'll see a self-signed
   certificate warning — choose "Advanced" → "Proceed" to continue. Caddy reverse-proxies
   the request, so port 5000 itself is not published to the host)
2. Login:

- ID: `admin`
- Password: `admin`

## 3. Create Test Service (2 minutes)

### 3.1 Register Service

1. Dashboard → "Service Management"
2. Click "New Service Registration"
3. Enter:
   - **Service Name**: Weather Service
   - **Subdomain**: weather
   - **Description**: Test weather service
4. Click "Register"

### 3.2 Register Capability

1. Click the created service
2. Click "Capabilities Management"
3. Click "New Capability Registration"
4. Enter:
   - **Capability Name**: echo_test
   - **Connection Type**: API
   - **Connection URL**: https://httpbin.org/post
   - **Description**: Simple echo test
   - **Body Parameters**:
     ```
     message: Hello
     ```
5. Click "Register"

### 3.3 Grant Permission to Administrator

1. Dashboard → "Account Management"
2. Click "Administrator"
3. The capability permissions are automatically assigned to accounts
4. Verify the capability appears in the account's capability list

### 3.4 Get Bearer Token

On the same account details screen, **copy the Bearer Token**.

## 4. Test MCP Endpoint (1 minute)

### 4.1 Get Capabilities

```bash
# Replace TOKEN with your actual token
TOKEN="YOUR_BEARER_TOKEN_HERE"

curl -k -H "Authorization: Bearer $TOKEN" \
  https://weather.lvh.me/mcp
```

**Expected Output:**

```json
{
  "capabilities": {
    "tools": [
      {
        "name": "echo_test",
        "description": "Simple echo test",
        "inputSchema": {
          "type": "object",
          "properties": {
            "message": {
              "type": "string",
              "description": "Parameter: message",
              "default": "Hello"
            }
          }
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

### 4.2 Execute Tool

```bash
curl -k -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "echo_test", "arguments": {"message": "Test from MCP"}}}' \
  https://weather.lvh.me/mcp
```

**Expected Output:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"status_code\": 200, \"data\": {...}}"
      }
    ],
    "isError": false
  }
}
```

## Done! 🎉

You can now:

✅ Start the MCP server  
✅ Manage services, capabilities, and permissions via Web admin  
✅ Access subdomain-based MCP endpoints  
✅ Execute tools and verify responses

## Next Steps

### Integrate Real APIs

1. Create new Capabilities in the Web admin
2. Set real API URLs (OpenWeather, GitHub, etc.)
3. Configure API Keys in header parameters
4. Grant permissions to accounts
5. Use from MCP clients (Dify, Claude Desktop)

### Manage Multiple Services

1. Create services for each API
2. Separate by subdomain (weather, github, database, etc.)
3. Set different permissions per account

### Relay MCP Servers

1. Register other MCP servers as Capabilities
2. Set type to "MCP"
3. Consolidate multiple MCP servers into one

## Troubleshooting

### lvh.me not working

Use this instead:

```bash
curl -k -H "Authorization: Bearer $TOKEN" \
  https://localhost/mcp?subdomain=weather
```

### Certificate warning on `https://localhost/`

This is expected: Caddy issues a self-signed certificate automatically. Click through the
browser warning, or see [Scaling & Containers](SCALING.en.md#https) to trust
Caddy's local CA instead.

### Running directly with `python run.py` (no Docker)

Use plain `http` and port 5000 instead: `http://localhost:5000/`,
`http://weather.lvh.me:5000/mcp`.

### Permission Errors

1. Check permissions are correctly set in account details
2. Verify capability name is correct
3. Confirm subdomain is correct

### Database Errors

```bash
# Restart containers
docker compose restart

# Or fully rebuild
docker compose down
docker compose up -d --build
```

## Additional Documentation

- **Detailed Setup**: [SETUP.en.md](SETUP.en.md)
- **MCP Endpoint Details**: [MCP_ENDPOINTS.en.md](MCP_ENDPOINTS.en.md)
- **Project Overview**: [README.en.md](https://github.com/t-ogawa-dev/octopus-mcp-proxy/blob/main/README.en.md)
