# 🚄 MCP Server for Renfe (Spain)

An MCP (Model Context Protocol) server for searching Spanish national train schedules from **Renfe**. Covers AVE (high-speed), ALVIA, Intercity, and Media Distancia trains across all of Spain.

## 📊 Data Source

Uses official **GTFS data** from [Renfe Open Data](https://data.renfe.com):
- 🏛️ **1,000+ stations** across Spain
- 🚆 **660+ routes** (AVE, ALVIA, Intercity, Media Distancia)
- 📅 **7,000+ trips** with full timetables
- ⏱️ **61,000+ stop times**

## 🛠️ Tools

| Tool | Description |
|------|-------------|
| `search_stations` | Search stations by name (returns IDs) |
| `search_trains` | Find trains between two stations on a date |
| `list_train_types` | List available train types |

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
git clone https://github.com/YOUR_USER/mcp-renfe.git
cd mcp-renfe

# Create venv and install deps
uv venv
source .venv/bin/activate
uv pip install mcp httpx

# Download GTFS data
./update_gtfs.sh
```

### Usage (stdio mode - for MCP clients)

```bash
python server_gtfs.py
```

### Configuration (mcporter / Claude Desktop / etc.)

Add to your MCP client config:

```json
{
  "mcpServers": {
    "renfe": {
      "command": "/path/to/mcp-renfe/.venv/bin/python",
      "args": ["/path/to/mcp-renfe/server_gtfs.py"]
    }
  }
}
```

## 📖 Examples

### Search stations
```
> search_stations query="Madrid"

• Madrid-Chamartín-Clara Campoamor (ID: 17000) ♿
• Madrid Pta.Atocha - Almudena Grandes (ID: 60000) ♿
• Madrid-Nuevos Ministerios (ID: 18002) ♿
...
```

### Search trains
```
> search_trains origin_id=60000 destination_id=71801 date="2026-04-10" from_time="10:00" to_time="14:00"

🚄 AVE 03303
   🕐 10:27:00 → 13:44:00
   ⏱️ 3h 17min (direct)

🚄 AVE 03113
   🕐 11:27:00 → 15:11:00
   ⏱️ 3h 44min (2 stops) ♿
```

## 🔄 Updating GTFS Data

Run the update script to download the latest schedules:

```bash
./update_gtfs.sh
```

## 📄 License

MIT

## 🙏 Credits

- Data: [Renfe Open Data](https://data.renfe.com) (GTFS format)
- Protocol: [Model Context Protocol](https://modelcontextprotocol.io)
