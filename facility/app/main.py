from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ffl.sqlite"
STATIC_PATH = ROOT / "static"

app = FastAPI(title="FFL License Mapper")
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="SQLite database not found. Run: ../.venv/bin/python -m app.import_data",
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def split_license_types(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().zfill(2) for item in value.split(",") if item.strip()]


def build_filters(
    *,
    north: float | None = None,
    south: float | None = None,
    east: float | None = None,
    west: float | None = None,
    state: str | None = None,
    license_type: str | None = None,
    q: str | None = None,
    require_coordinates: bool = False,
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if require_coordinates:
        clauses.append("lat IS NOT NULL")
        clauses.append("lon IS NOT NULL")

    if north is not None and south is not None:
        clauses.append("lat BETWEEN ? AND ?")
        params.extend([south, north])

    if east is not None and west is not None:
        if west <= east:
            clauses.append("lon BETWEEN ? AND ?")
            params.extend([west, east])
        else:
            clauses.append("(lon >= ? OR lon <= ?)")
            params.extend([west, east])

    if state:
        clauses.append("premise_state = ?")
        params.append(state.strip().upper())

    license_types = split_license_types(license_type)
    if license_types:
        placeholders = ", ".join("?" for _ in license_types)
        clauses.append(f"lic_type IN ({placeholders})")
        params.extend(license_types)

    if q:
        terms = [term.lower() for term in q.strip().split() if term.strip()]
        for term in terms[:6]:
            clauses.append("search_text LIKE ?")
            params.append(f"%{term}%")

    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params


def display_name(row: sqlite3.Row) -> str:
    return row["business_name"] or row["license_name"] or row["ffl_number"]


def row_to_license(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "ffl_number": row["ffl_number"],
        "display_name": display_name(row),
        "business_name": row["business_name"],
        "license_name": row["license_name"],
        "license_type": row["lic_type"],
        "type_label": row["type_label"],
        "expiry_code": row["lic_xprdte"],
        "address": row["premise_street"],
        "city": row["premise_city"],
        "state": row["premise_state"],
        "zip": row["premise_zip_code"],
        "phone": row["voice_phone"],
        "lat": row["lat"],
        "lon": row["lon"],
        "geo_source": row["geo_source"],
    }


def cluster_step(zoom: int) -> float:
    if zoom <= 3:
        return 14.0
    if zoom == 4:
        return 8.0
    if zoom == 5:
        return 4.0
    if zoom == 6:
        return 2.0
    if zoom == 7:
        return 1.0
    if zoom == 8:
        return 0.45
    if zoom == 9:
        return 0.22
    if zoom == 10:
        return 0.11
    return 0.05


def cluster_rows(rows: list[sqlite3.Row], zoom: int) -> list[dict[str, Any]]:
    step = cluster_step(zoom)
    clusters: dict[tuple[int, int], dict[str, Any]] = {}

    for row in rows:
        lat = float(row["lat"])
        lon = float(row["lon"])
        key = (math.floor(lat / step), math.floor(lon / step))
        cluster = clusters.setdefault(
            key,
            {
                "kind": "cluster",
                "count": 0,
                "lat_sum": 0.0,
                "lon_sum": 0.0,
                "states": {},
                "samples": [],
            },
        )
        cluster["count"] += 1
        cluster["lat_sum"] += lat
        cluster["lon_sum"] += lon
        cluster["states"][row["premise_state"]] = cluster["states"].get(row["premise_state"], 0) + 1
        if len(cluster["samples"]) < 3:
            cluster["samples"].append(display_name(row))

    markers = []
    for index, cluster in enumerate(clusters.values()):
        count = cluster["count"]
        states = sorted(cluster["states"].items(), key=lambda item: item[1], reverse=True)
        markers.append(
            {
                "id": f"cluster-{index}",
                "kind": "cluster",
                "count": count,
                "lat": cluster["lat_sum"] / count,
                "lon": cluster["lon_sum"] / count,
                "primary_state": states[0][0] if states else "",
                "samples": cluster["samples"],
            }
        )
    return sorted(markers, key=lambda marker: marker["count"], reverse=True)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_PATH / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": DB_PATH.exists(), "db": str(DB_PATH)}


@app.get("/api/stats")
def stats() -> dict[str, Any]:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
        geocoded = conn.execute(
            "SELECT COUNT(*) FROM licenses WHERE lat IS NOT NULL AND lon IS NOT NULL"
        ).fetchone()[0]
        by_state = [
            dict(row)
            for row in conn.execute(
                """
                SELECT premise_state AS state, COUNT(*) AS count
                FROM licenses
                GROUP BY premise_state
                ORDER BY count DESC, state
                """
            )
        ]
        by_type = [
            dict(row)
            for row in conn.execute(
                """
                SELECT lic_type AS license_type, type_label, COUNT(*) AS count
                FROM licenses
                GROUP BY lic_type, type_label
                ORDER BY count DESC, lic_type
                """
            )
        ]
        metadata = {
            row["key"]: row["value"]
            for row in conn.execute("SELECT key, value FROM metadata ORDER BY key")
        }

    return {
        "total": total,
        "geocoded": geocoded,
        "missing_coordinates": total - geocoded,
        "by_state": by_state,
        "by_type": by_type,
        "metadata": metadata,
    }


@app.get("/api/filters")
def filters() -> dict[str, Any]:
    with connect() as conn:
        states = [
            dict(row)
            for row in conn.execute(
                """
                SELECT premise_state AS state, COUNT(*) AS count
                FROM licenses
                GROUP BY premise_state
                ORDER BY premise_state
                """
            )
        ]
        license_types = [
            dict(row)
            for row in conn.execute(
                """
                SELECT lic_type AS license_type, type_label, COUNT(*) AS count
                FROM licenses
                GROUP BY lic_type, type_label
                ORDER BY lic_type
                """
            )
        ]
    return {"states": states, "license_types": license_types}


@app.get("/api/markers")
def markers(
    request: Request,
    north: float = Query(...),
    south: float = Query(...),
    east: float = Query(...),
    west: float = Query(...),
    zoom: int = Query(4, ge=1, le=18),
    state: str | None = None,
    license_type: str | None = None,
    q: str | None = None,
) -> dict[str, Any]:
    where, params = build_filters(
        north=north,
        south=south,
        east=east,
        west=west,
        state=state,
        license_type=license_type,
        q=q,
        require_coordinates=True,
    )
    sql = f"""
        SELECT id, ffl_number, lic_type, type_label, lic_xprdte, license_name,
               business_name, premise_street, premise_city, premise_state,
               premise_zip_code, voice_phone, lat, lon, geo_source
        FROM licenses
        {where}
    """

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    total = len(rows)
    individual_limit = 1200
    should_show_individual = zoom >= 11 and total <= individual_limit

    if should_show_individual:
        payload = [dict(row_to_license(row), kind="license", count=1) for row in rows]
        mode = "licenses"
    else:
        payload = cluster_rows(rows, zoom)
        mode = "clusters"

    return {
        "mode": mode,
        "total": total,
        "returned": len(payload),
        "markers": payload,
        "url": str(request.url),
    }


@app.get("/api/licenses")
def licenses(
    north: float | None = None,
    south: float | None = None,
    east: float | None = None,
    west: float | None = None,
    state: str | None = None,
    license_type: str | None = None,
    q: str | None = None,
    limit: int = Query(75, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    has_bounds = north is not None or south is not None or east is not None or west is not None
    where, params = build_filters(
        north=north,
        south=south,
        east=east,
        west=west,
        state=state,
        license_type=license_type,
        q=q,
        require_coordinates=has_bounds,
    )
    count_sql = f"SELECT COUNT(*) FROM licenses {where}"
    list_sql = f"""
        SELECT id, ffl_number, lic_type, type_label, lic_xprdte, license_name,
               business_name, premise_street, premise_city, premise_state,
               premise_zip_code, voice_phone, lat, lon, geo_source
        FROM licenses
        {where}
        ORDER BY premise_state, premise_city,
                 business_name COLLATE NOCASE, license_name COLLATE NOCASE
        LIMIT ? OFFSET ?
    """

    with connect() as conn:
        total = conn.execute(count_sql, params).fetchone()[0]
        rows = conn.execute(list_sql, [*params, limit, offset]).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "licenses": [row_to_license(row) for row in rows],
    }


@app.get("/api/licenses/{license_id}")
def license_detail(license_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, ffl_number, lic_type, type_label, lic_xprdte, license_name,
                   business_name, premise_street, premise_city, premise_state,
                   premise_zip_code, voice_phone, lat, lon, geo_source
            FROM licenses
            WHERE id = ?
            """,
            (license_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="License not found")
    return row_to_license(row)
