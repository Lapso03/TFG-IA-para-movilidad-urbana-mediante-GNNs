#!/usr/bin/env python3
"""
MCP Server for Renfe (Spain) - Based on official GTFS data
Covers: AVE, ALVIA, Intercity, Media Distancia (national long/medium distance)
Data source: https://data.renfe.com
"""

import asyncio
import csv
import os
from datetime import datetime
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

GTFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtfs", "ave_ld")

app = Server("renfe")

# Cache
_stops = None
_routes = None
_trips = None
_stop_times_by_trip = None
_calendar = None
_calendar_dates = None


def load_csv(filename):
    filepath = os.path.join(GTFS_DIR, filename)
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        return [{k.strip(): v.strip() for k, v in row.items()} for row in reader]


def get_stops():
    global _stops
    if _stops is None:
        _stops = load_csv("stops.txt")
    return _stops


def get_routes():
    global _routes
    if _routes is None:
        _routes = load_csv("routes.txt")
    return _routes


def get_trips():
    global _trips
    if _trips is None:
        _trips = load_csv("trips.txt")
    return _trips


def get_stop_times_by_trip():
    global _stop_times_by_trip
    if _stop_times_by_trip is None:
        _stop_times_by_trip = {}
        for st in load_csv("stop_times.txt"):
            tid = st['trip_id']
            if tid not in _stop_times_by_trip:
                _stop_times_by_trip[tid] = []
            _stop_times_by_trip[tid].append(st)
    return _stop_times_by_trip


def get_calendar():
    global _calendar
    if _calendar is None:
        try:
            _calendar = load_csv("calendar.txt")
        except FileNotFoundError:
            _calendar = []
    return _calendar


def get_calendar_dates():
    global _calendar_dates
    if _calendar_dates is None:
        try:
            raw = load_csv("calendar_dates.txt")
            _calendar_dates = {}
            for cd in raw:
                sid = cd['service_id']
                if sid not in _calendar_dates:
                    _calendar_dates[sid] = []
                _calendar_dates[sid].append(cd)
        except FileNotFoundError:
            _calendar_dates = {}
    return _calendar_dates


def get_active_services(date_str):
    """Get all service_ids active on a given date (YYYY-MM-DD)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    date_compact = date_str.replace('-', '')  # YYYYMMDD
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_of_week = day_names[dt.weekday()]

    calendar = get_calendar()
    calendar_dates = get_calendar_dates()

    active = set()

    # Check calendar.txt: service runs on this day of week within date range
    for svc in calendar:
        start = svc.get('start_date', '')
        end = svc.get('end_date', '')
        if start <= date_compact <= end and svc.get(day_of_week) == '1':
            active.add(svc['service_id'])

    # Check calendar_dates.txt for exceptions
    for sid in list(active):
        if sid in calendar_dates:
            for exc in calendar_dates[sid]:
                if exc['date'] == date_compact and exc['exception_type'] == '2':
                    active.discard(sid)  # Remove service on this date

    # Also add services that are ADDED on this date (exception_type=1)
    for sid, exceptions in calendar_dates.items():
        for exc in exceptions:
            if exc['date'] == date_compact and exc['exception_type'] == '1':
                active.add(sid)

    return active


def find_trains(origin_id, destination_id, date=None, from_time=None, to_time=None):
    """Find trains between two stations on a given date"""
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    # Get active services for this date
    active_services = get_active_services(date)

    # Build service_id -> trip_ids mapping
    trips = get_trips()
    routes = get_routes()
    route_map = {r['route_id']: r for r in routes}

    active_trip_ids = set()
    trip_map = {}
    for t in trips:
        trip_map[t['trip_id']] = t
        if t['service_id'] in active_services:
            active_trip_ids.add(t['trip_id'])

    # Search stop_times for active trips
    trip_stops = get_stop_times_by_trip()
    results = []
    seen = set()

    for tid in active_trip_ids:
        stops = trip_stops.get(tid)
        if not stops:
            continue

        origin_stop = None
        dest_stop = None

        for stop in stops:
            if stop['stop_id'] == origin_id:
                origin_stop = stop
            if stop['stop_id'] == destination_id and origin_stop is not None:
                dest_stop = stop
                break

        if origin_stop and dest_stop:
            if int(origin_stop['stop_sequence']) < int(dest_stop['stop_sequence']):
                dep_time = origin_stop.get('departure_time', '')
                arr_time = dest_stop.get('arrival_time', '')

                if from_time and dep_time < from_time:
                    continue
                if to_time and dep_time > to_time:
                    continue

                trip = trip_map.get(tid, {})
                route_id = trip.get('route_id', '')
                route = route_map.get(route_id, {})
                train_type = route.get('route_short_name', 'Unknown')
                train_number = trip.get('trip_short_name', '')

                # Deduplicate
                key = (train_type, train_number, dep_time, arr_time)
                if key in seen:
                    continue
                seen.add(key)

                # Duration
                try:
                    dep_parts = dep_time.split(':')
                    arr_parts = arr_time.split(':')
                    dep_min = int(dep_parts[0]) * 60 + int(dep_parts[1])
                    arr_min = int(arr_parts[0]) * 60 + int(arr_parts[1])
                    dur_min = arr_min - dep_min
                    if dur_min < 0:
                        dur_min += 24 * 60
                    duration = f"{dur_min // 60}h {dur_min % 60:02d}min"
                except (ValueError, IndexError):
                    duration = "N/A"

                origin_seq = int(origin_stop['stop_sequence'])
                dest_seq = int(dest_stop['stop_sequence'])

                results.append({
                    'train_type': train_type,
                    'train_number': train_number,
                    'departure': dep_time,
                    'arrival': arr_time,
                    'duration': duration,
                    'stops': dest_seq - origin_seq - 1,
                    'accessible': trip.get('wheelchair_accessible', '0') == '1'
                })

    results.sort(key=lambda x: x['departure'])
    return results


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_stations",
            description="Search Renfe stations by name. Returns station IDs needed for train search. Covers all Spain: AVE, ALVIA, Intercity, Media Distancia.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Station name to search (e.g., 'Madrid', 'Barcelona', 'Sevilla')"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_train_types",
            description="List all available Renfe train types (AVE, ALVIA, Intercity, etc.)",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="search_trains",
            description="Search for Renfe trains between two stations on a specific date. Use search_stations first to get station IDs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin_id": {
                        "description": "Origin station ID (from search_stations)"
                    },
                    "destination_id": {
                        "description": "Destination station ID (from search_stations)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Travel date in YYYY-MM-DD format (defaults to today)"
                    },
                    "from_time": {
                        "type": "string",
                        "description": "Earliest departure time HH:MM (optional)"
                    },
                    "to_time": {
                        "type": "string",
                        "description": "Latest departure time HH:MM (optional)"
                    }
                },
                "required": ["origin_id", "destination_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_stations":
        query = arguments.get("query", "")
        if not query:
            return [TextContent(type="text", text="Error: query is required")]
        stations = search_stops(query)
        if not stations:
            return [TextContent(type="text", text=f"No stations found matching '{query}'")]
        result = f"Stations matching '{query}':\n\n"
        for s in stations[:20]:
            acc = " ♿" if s.get('wheelchair_boarding') == '1' else ""
            result += f"• {s['stop_name']} (ID: {s['stop_id']}){acc}\n"
        if len(stations) > 20:
            result += f"\n... and {len(stations) - 20} more"
        return [TextContent(type="text", text=result)]

    elif name == "list_train_types":
        routes = get_routes()
        types = sorted(set(r.get('route_short_name', '').strip() for r in routes if r.get('route_short_name', '').strip()))
        result = "Renfe Train Types:\n\n"
        for t in types:
            result += f"🚆 {t}\n"
        return [TextContent(type="text", text=result)]

    elif name == "search_trains":
        origin_id = str(arguments.get("origin_id", ""))
        destination_id = str(arguments.get("destination_id", ""))
        date = arguments.get("date")
        from_time = arguments.get("from_time")
        to_time = arguments.get("to_time")

        if not all([origin_id, destination_id]):
            return [TextContent(type="text", text="Error: origin_id and destination_id are required")]

        stops = get_stops()
        origin_name = next((s['stop_name'] for s in stops if s['stop_id'] == origin_id), origin_id)
        dest_name = next((s['stop_name'] for s in stops if s['stop_id'] == destination_id), destination_id)

        trains = find_trains(origin_id, destination_id, date=date, from_time=from_time, to_time=to_time)

        if not trains:
            return [TextContent(type="text", text=f"No trains found from {origin_name} to {dest_name} on {date or 'today'}")]

        result = f"🚆 {origin_name} → {dest_name}\n"
        result += f"📅 {date or 'today'}"
        if from_time:
            result += f" | ⏰ {from_time}"
        if to_time:
            result += f"–{to_time}"
        result += f"\n{'─' * 45}\n\n"

        for t in trains[:20]:
            acc = " ♿" if t['accessible'] else ""
            stops_info = f"({t['stops']} stops)" if t['stops'] > 0 else "(direct)"
            result += f"🚄 {t['train_type']} {t['train_number']}\n"
            result += f"   {t['departure']} → {t['arrival']}  ⏱️ {t['duration']}  {stops_info}{acc}\n\n"

        if len(trains) > 20:
            result += f"... and {len(trains) - 20} more"
        result += f"\n📊 {len(trains)} trains found"
        return [TextContent(type="text", text=result)]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


def search_stops(query):
    query_lower = query.lower()
    return [s for s in get_stops() if query_lower in s.get('stop_name', '').lower()]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
