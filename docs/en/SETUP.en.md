[日本語](../SETUP.md) | English

# MCP Server Setup Guide

## Startup Procedure

### 1. Environment Variable Configuration

Copy `.env.example` to `.env` and edit as needed.

```bash
cp .env.example .env
```

### 2. Start Docker Containers

```bash
docker compose up -d
```

On first startup, the image will be built and the database will be initialized.

### 3. Check Logs

```bash
docker compose logs -f web
```

Once startup is complete, the default administrator's Bearer token will be displayed in the logs.

### 4. Access Web Admin Interface

Open **https://localhost/** in your browser (no port number). Caddy reverse-proxies ports
80/443; the app's port 5000 itself is not published to the host, so `:5000` will not work.
You'll see a self-signed certificate warning — choose "Advanced" → "Proceed" to continue
(see [Scaling & Containers](SCALING.en.md#https) if you want to remove the warning).

If you started directly with `python run.py` (no Docker), use `http://localhost:5000/` instead.

**Default Administrator Account:**

- Login ID: `admin`
- Password: `admin`

**Note**: The admin UI is routed by path, so `https://localhost/`, `https://lvh.me/`, and
`https://admin.lvh.me/` all show the same screen. Only MCP services are distinguished by subdomain.

## Basic Usage

### 1. Service Registration

1. Click "Service Management" from the dashboard
2. Click "New Service Registration"
3. Enter the following:
   - Service Name: Any name
   - Subdomain: Connection path for MCP clients (e.g., `myservice`)
   - Common Headers: Headers used by all Capabilities (JSON format)

**Subdomain Example:**

```
Subdomain: myservice
→ MCP Endpoint: https://myservice.lvh.me/mcp   (Docker Compose, via Caddy)
→ MCP Endpoint: http://myservice.lvh.me:5000/mcp  (when run directly with python run.py)
```

### 2. Capability Registration

1. Click "Capabilities Management" from the service details screen
2. Click "New Capability Registration"
3. Enter the following:
   - Capability Name: Name displayed as MCP Tool
   - Connection Type: API or MCP
   - Connection URL: URL of the relay destination API/MCP server
   - Header Parameters: Individual header settings
   - Body Parameters: Default parameters

**API Capability Example:**

```
Capability Name: get_weather
Connection Type: API
Connection URL: https://api.weather.com/v1/current
Header Parameters:
  X-API-Key: your-api-key
Body Parameters:
  units: metric
```

**MCP Capability Example:**

```
Capability Name: search_database
Connection Type: MCP
Connection URL: http://other-mcp-server:5000/mcp/db
```

### 3. User Registration

1. Click "Account Management" from the dashboard
2. Click "New Account Registration"
3. Enter login ID and password, then register
4. After registration, check the Bearer token on the account details screen

### 4. Permission Setup

1. On the account details screen, click "Add Permission"
2. Select service and capability
3. Click "Add"

Now the account can use the specified capability.

## Connecting from MCP Clients

The URLs below are for **Docker Compose (via Caddy, `https://`, no port number)**. If you
started directly with `python run.py` (no Docker), use `http://` + `:5000` instead.

### Subdomain-Based Access (Recommended)

#### Using lvh.me Domain

`lvh.me` is a public domain for local development that always resolves to 127.0.0.1.

```bash
# Get Capabilities (curl needs -k since the cert is self-signed)
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  https://myservice.lvh.me/mcp

# Execute Tool
curl -k -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_weather", "arguments": {"param": "value"}}}' \
  https://myservice.lvh.me/mcp
```

#### Using Query Parameters

```bash
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  https://localhost/mcp?subdomain=myservice
```

### MCP Client Configuration Examples

#### Dify

```json
{
  "mcp_servers": {
    "my_service": {
      "url": "https://myservice.lvh.me/mcp",
      "auth": {
        "type": "bearer",
        "token": "YOUR_BEARER_TOKEN"
      }
    }
  }
}
```

#### Claude Desktop

```json
{
  "mcpServers": {
    "my-service": {
      "url": "https://myservice.lvh.me/mcp",
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

### Legacy Endpoint (Backward Compatibility)

```json
{
  "mcpServers": {
    "my-service": {
      "url": "https://localhost/mcp/myservice",
      "headers": {
        "Authorization": "Bearer YOUR_BEARER_TOKEN"
      }
    }
  }
}
```

### stdio Connection

```json
{
  "mcpServers": {
    "my-service": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp_server",
        "python",
        "stdio_server.py",
        "myservice",
        "<User's Bearer Token>"
      ]
    }
  }
}
```

## Use Cases

### 1. External API Relay

Example of using a weather API via MCP:

1. Register Service:
   - Name: Weather Service
   - Subdomain: weather

2. Register Capability:
   - Name: get_current_weather
   - Type: API
   - URL: https://api.openweathermap.org/data/2.5/weather
   - Headers: `appid: YOUR_API_KEY`
   - Body Parameters: `units: metric`

3. Grant permission to account

4. From MCP client:

```
User: Tell me the weather in Tokyo
AI: (Uses get_current_weather tool to retrieve weather information)
```

### 2. Integrating Multiple MCP Servers

Example of integrating database MCP server and filesystem MCP server:

1. Register Service: Integration Hub
2. Register Capabilities:
   - database_query (MCP, http://db-mcp:5000/mcp/db)
   - file_read (MCP, http://fs-mcp:5002/mcp/files)
3. Grant only necessary capabilities per account

## Troubleshooting

### Database Connection Error

```bash
# Check MySQL container logs
docker compose logs db

# Wait for database to start
docker compose restart web
```

### Port Conflict

Only the `caddy` service's ports 80/443 are published to the host (`web`/`mcp` port 5000 is
internal-only). If 80/443 conflict with something else, change the `caddy` service's `ports`
in `compose.yaml`:

```yaml
ports:
  - "8080:80"
  - "8443:443"
```

### Certificate warning on `https://localhost/`

This is expected: Caddy issues a self-signed certificate automatically for local development.
See [Scaling & Containers](SCALING.en.md#https) for details.

### Invalid Token

Click "Regenerate Token" on the account details screen to issue a new token.

## Security

### Production Environment Settings

1. **Change SECRET_KEY**

   ```bash
   # .env file
   SECRET_KEY=random-long-string
   ```

2. **Change Administrator Password**
   - After login, change password on the account details screen

3. **Use HTTPS**
   - SSL/TLS termination with reverse proxy (Nginx, Traefik)

4. **Change Database Password**
   - Change MYSQL_PASSWORD etc. in `compose.yaml`

## Data Backup

```bash
# Backup database
docker compose exec db mysqldump -u mcpuser -pmcppassword mcpdb > backup.sql

# Restore database
docker compose exec -T db mysql -u mcpuser -pmcppassword mcpdb < backup.sql
```

## Development Mode

For local development:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start development server
export DATABASE_URL=mysql+pymysql://mcpuser:mcppassword@localhost:3306/mcpdb
python run.py
```

## API Reference

### Service API

- `GET /api/services` - Service list
- `POST /api/services` - Create service
- `GET /api/services/{id}` - Service details
- `PUT /api/services/{id}` - Update service
- `DELETE /api/services/{id}` - Delete service

### Capability API

- `GET /api/services/{id}/capabilities` - Capability list
- `POST /api/services/{id}/capabilities` - Create capability
- `GET /api/capabilities/{id}` - Capability details
- `PUT /api/capabilities/{id}` - Update capability
- `DELETE /api/capabilities/{id}` - Delete capability

### Account API

- `GET /api/users` - Account list
- `POST /api/users` - Create account
- `GET /api/users/{id}` - Account details
- `PUT /api/users/{id}` - Update account
- `DELETE /api/users/{id}` - Delete account
- `POST /api/users/{id}/regenerate_token` - Regenerate token

### Permission API

- `GET /api/users/{id}/permissions` - Account permission list
- `POST /api/users/{id}/permissions` - Add permission
- `DELETE /api/permissions/{id}` - Delete permission

### MCP API

- `POST /mcp` (with subdomain) / `POST /{identifier}/mcp` - MCP request processing
  - Authorization: Bearer {token}
  - Content-Type: application/json
