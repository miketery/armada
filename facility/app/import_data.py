from __future__ import annotations

import argparse
import csv
import hashlib
import io
import math
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = ROOT / "0426-ffl-list.csv"
DEFAULT_GAZETTEER_PATH = ROOT / "data" / "2025_Gaz_zcta_national.zip"
DEFAULT_DB_PATH = ROOT / "data" / "ffl.sqlite"
ZCTA_SOURCE_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2025_Gazetteer/2025_Gaz_zcta_national.zip"
)

TYPE_LABELS = {
    "01": "Dealer",
    "02": "Pawnbroker",
    "03": "Collector",
    "06": "Ammo manufacturer",
    "07": "Firearms manufacturer",
    "08": "Importer",
    "09": "Destructive device dealer",
    "10": "Destructive device manufacturer",
    "11": "Destructive device importer",
}

STATE_FALLBACK_CENTROIDS = {
    "AL": (32.806671, -86.791130),
    "AK": (61.370716, -152.404419),
    "AZ": (33.729759, -111.431221),
    "AR": (34.969704, -92.373123),
    "CA": (36.116203, -119.681564),
    "CO": (39.059811, -105.311104),
    "CT": (41.597782, -72.755371),
    "DE": (39.318523, -75.507141),
    "DC": (38.897438, -77.026817),
    "FL": (27.766279, -81.686783),
    "GA": (33.040619, -83.643074),
    "HI": (21.094318, -157.498337),
    "ID": (44.240459, -114.478828),
    "IL": (40.349457, -88.986137),
    "IN": (39.849426, -86.258278),
    "IA": (42.011539, -93.210526),
    "KS": (38.526600, -96.726486),
    "KY": (37.668140, -84.670067),
    "LA": (31.169546, -91.867805),
    "ME": (44.693947, -69.381927),
    "MD": (39.063946, -76.802101),
    "MA": (42.230171, -71.530106),
    "MI": (43.326618, -84.536095),
    "MN": (45.694454, -93.900192),
    "MS": (32.741646, -89.678696),
    "MO": (38.456085, -92.288368),
    "MT": (46.921925, -110.454353),
    "NE": (41.125370, -98.268082),
    "NV": (38.313515, -117.055374),
    "NH": (43.452492, -71.563896),
    "NJ": (40.298904, -74.521011),
    "NM": (34.840515, -106.248482),
    "NY": (42.165726, -74.948051),
    "NC": (35.630066, -79.806419),
    "ND": (47.528912, -99.784012),
    "OH": (40.388783, -82.764915),
    "OK": (35.565342, -96.928917),
    "OR": (44.572021, -122.070938),
    "PA": (40.590752, -77.209755),
    "PR": (18.220833, -66.590149),
    "RI": (41.680893, -71.511780),
    "SC": (33.856892, -80.945007),
    "SD": (44.299782, -99.438828),
    "TN": (35.747845, -86.692345),
    "TX": (31.054487, -97.563461),
    "UT": (40.150032, -111.862434),
    "VT": (44.045876, -72.710686),
    "VA": (37.769337, -78.169968),
    "WA": (47.400902, -121.490494),
    "WV": (38.491226, -80.954453),
    "WI": (44.268543, -89.616508),
    "WY": (42.755966, -107.302490),
    "GU": (13.444304, 144.793731),
    "MP": (15.097900, 145.673900),
    "VI": (18.335765, -64.896335),
}


def clean(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split())


def zip5(value: str | None) -> str:
    value = clean(value)
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits[:5] if len(digits) >= 5 else digits


def ffl_number(row: dict[str, str]) -> str:
    parts = [
        clean(row.get("LIC_REGN")),
        clean(row.get("LIC_DIST")),
        clean(row.get("LIC_CNTY")),
        clean(row.get("LIC_TYPE")),
        clean(row.get("LIC_XPRDTE")),
        clean(row.get("LIC_SEQN")),
    ]
    return "-".join(parts)


def jitter_point(
    lat: float,
    lon: float,
    key: str,
    max_radius: float = 0.012,
) -> tuple[float, float]:
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    angle = int.from_bytes(digest[:4], "big") / 2**32 * 2 * math.pi
    radius = 0.0008 + int.from_bytes(digest[4:], "big") / 2**32 * max_radius
    lon_scale = max(math.cos(math.radians(lat)), 0.25)
    return (
        lat + math.cos(angle) * radius,
        lon + math.sin(angle) * radius / lon_scale,
    )


def read_zcta_centroids(path: Path) -> dict[str, tuple[float, float, int, int]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing Census ZCTA gazetteer: {path}")

    centroids: dict[str, tuple[float, float, int, int]] = {}
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".txt")]
        if not names:
            raise ValueError(f"No .txt file found in {path}")
        with archive.open(names[0]) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8")
            reader = csv.DictReader(text, delimiter="|")
            for row in reader:
                geoid = clean(row["GEOID"])
                centroids[geoid] = (
                    float(row["INTPTLAT"]),
                    float(row["INTPTLONG"]),
                    int(row["ALAND"]),
                    int(row["AWATER"]),
                )
    return centroids


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS licenses;
        DROP TABLE IF EXISTS zctas;
        DROP TABLE IF EXISTS metadata;

        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE zctas (
            zip5 TEXT PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            aland INTEGER NOT NULL,
            awater INTEGER NOT NULL
        );

        CREATE TABLE licenses (
            id INTEGER PRIMARY KEY,
            ffl_number TEXT NOT NULL UNIQUE,
            lic_regn TEXT NOT NULL,
            lic_dist TEXT NOT NULL,
            lic_cnty TEXT NOT NULL,
            lic_type TEXT NOT NULL,
            type_label TEXT NOT NULL,
            lic_xprdte TEXT NOT NULL,
            lic_seqn TEXT NOT NULL,
            license_name TEXT NOT NULL,
            business_name TEXT NOT NULL,
            premise_street TEXT NOT NULL,
            premise_city TEXT NOT NULL,
            premise_state TEXT NOT NULL,
            premise_zip_code TEXT NOT NULL,
            premise_zip5 TEXT NOT NULL,
            mail_street TEXT NOT NULL,
            mail_city TEXT NOT NULL,
            mail_state TEXT NOT NULL,
            mail_zip_code TEXT NOT NULL,
            voice_phone TEXT NOT NULL,
            lat REAL,
            lon REAL,
            geo_source TEXT NOT NULL,
            search_text TEXT NOT NULL
        );
        """
    )


def create_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX idx_licenses_state ON licenses (premise_state);
        CREATE INDEX idx_licenses_type ON licenses (lic_type);
        CREATE INDEX idx_licenses_zip ON licenses (premise_zip5);
        CREATE INDEX idx_licenses_city ON licenses (premise_state, premise_city);
        CREATE INDEX idx_licenses_lat_lon ON licenses (lat, lon);
        """
    )


def build_search_text(row: dict[str, str], number: str, zip_code: str) -> str:
    fields = [
        number,
        row.get("LICENSE_NAME", ""),
        row.get("BUSINESS_NAME", ""),
        row.get("PREMISE_STREET", ""),
        row.get("PREMISE_CITY", ""),
        row.get("PREMISE_STATE", ""),
        zip_code,
        row.get("VOICE_PHONE", ""),
    ]
    return " ".join(clean(value).lower() for value in fields if clean(value))


def import_database(csv_path: Path, gazetteer_path: Path, db_path: Path) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    zctas = read_zcta_centroids(gazetteer_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        create_schema(conn)
        conn.executemany(
            "INSERT INTO zctas (zip5, lat, lon, aland, awater) VALUES (?, ?, ?, ?, ?)",
            [(code, lat, lon, aland, awater) for code, (lat, lon, aland, awater) in zctas.items()],
        )

        inserted = 0
        geocoded = 0
        fallback = 0
        missing = 0
        records = []

        with csv_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            for row in reader:
                number = ffl_number(row)
                premise_zip5 = zip5(row.get("PREMISE_ZIP_CODE"))
                premise_state = clean(row.get("PREMISE_STATE")).upper()
                lic_type = clean(row.get("LIC_TYPE")).zfill(2)
                center = zctas.get(premise_zip5)
                geo_source = "none"
                lat = None
                lon = None

                if center:
                    lat, lon = jitter_point(center[0], center[1], number)
                    geo_source = "census_zcta_2025"
                    geocoded += 1
                elif premise_state in STATE_FALLBACK_CENTROIDS:
                    state_lat, state_lon = STATE_FALLBACK_CENTROIDS[premise_state]
                    lat, lon = jitter_point(state_lat, state_lon, number, max_radius=0.2)
                    geo_source = "state_centroid_fallback"
                    fallback += 1
                else:
                    missing += 1

                records.append(
                    (
                        number,
                        clean(row.get("LIC_REGN")),
                        clean(row.get("LIC_DIST")),
                        clean(row.get("LIC_CNTY")),
                        lic_type,
                        TYPE_LABELS.get(lic_type, f"Type {lic_type}"),
                        clean(row.get("LIC_XPRDTE")),
                        clean(row.get("LIC_SEQN")),
                        clean(row.get("LICENSE_NAME")),
                        clean(row.get("BUSINESS_NAME")),
                        clean(row.get("PREMISE_STREET")),
                        clean(row.get("PREMISE_CITY")).upper(),
                        premise_state,
                        clean(row.get("PREMISE_ZIP_CODE")),
                        premise_zip5,
                        clean(row.get("MAIL_STREET")),
                        clean(row.get("MAIL_CITY")).upper(),
                        clean(row.get("MAIL_STATE")).upper(),
                        clean(row.get("MAIL_ZIP_CODE")),
                        clean(row.get("VOICE_PHONE")),
                        lat,
                        lon,
                        geo_source,
                        build_search_text(row, number, premise_zip5),
                    )
                )

                if len(records) >= 5000:
                    conn.executemany(LICENSE_INSERT_SQL, records)
                    inserted += len(records)
                    records.clear()

        if records:
            conn.executemany(LICENSE_INSERT_SQL, records)
            inserted += len(records)

        create_indexes(conn)
        metadata = {
            "generated_at": datetime.now(UTC).isoformat(),
            "csv_file": str(csv_path),
            "zcta_gazetteer": str(gazetteer_path),
            "zcta_source_url": ZCTA_SOURCE_URL,
            "coordinate_note": (
                "FFL rows are plotted by Census ZCTA centroid, with state fallback "
                "only where no ZCTA exists."
            ),
        }
        conn.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            metadata.items(),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "licenses": inserted,
        "zctas": len(zctas),
        "zcta_geocoded": geocoded,
        "state_fallback": fallback,
        "missing_coordinates": missing,
    }


LICENSE_INSERT_SQL = """
    INSERT INTO licenses (
        ffl_number,
        lic_regn,
        lic_dist,
        lic_cnty,
        lic_type,
        type_label,
        lic_xprdte,
        lic_seqn,
        license_name,
        business_name,
        premise_street,
        premise_city,
        premise_state,
        premise_zip_code,
        premise_zip5,
        mail_street,
        mail_city,
        mail_state,
        mail_zip_code,
        voice_phone,
        lat,
        lon,
        geo_source,
        search_text
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load the FFL CSV and ZCTA centroids into SQLite.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--gazetteer", type=Path, default=DEFAULT_GAZETTEER_PATH)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = import_database(args.csv, args.gazetteer, args.db)
    print(f"Loaded {result['licenses']:,} licenses into {args.db}")
    print(
        "Coordinates: "
        f"{result['zcta_geocoded']:,} ZCTA, "
        f"{result['state_fallback']:,} state fallback, "
        f"{result['missing_coordinates']:,} missing"
    )
    print(f"Loaded {result['zctas']:,} Census ZCTA centroids")


if __name__ == "__main__":
    main()
