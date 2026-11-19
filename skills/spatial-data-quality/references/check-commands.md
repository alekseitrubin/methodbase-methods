# Check commands

Supporting reference for the `spatial-data-quality` Method. Examples assume
a synthetic layer `parcels` with identifier `parcel_id` and geometry column
`geom`. Function availability depends on PostGIS, GEOS and GDAL versions;
record the versions used (`SELECT postgis_full_version();`,
`ogrinfo --version`).

All commands below read data. Commands that write go to a separate schema or
file and are marked.

## Inventory with GDAL

```bash
ogrinfo -so -al parcels.gpkg
```

Reports layers, geometry type, feature count, extent, CRS and fields without
listing features.

```bash
ogrinfo parcels.gpkg -sql "SELECT count(*) FROM parcels WHERE geom IS NULL" -dialect SQLite
```

The SQLite dialect gives SQL over any OGR source. Spatial functions such as
`ST_IsValid` in this dialect are available only when GDAL is built with
SpatiaLite.

## Loading a working copy into PostGIS (writes to a QA schema)

```bash
ogr2ogr -f PostgreSQL PG:"dbname=qa" parcels.gpkg -nln qa.parcels_raw -lco GEOMETRY_NAME=geom
```

Do not add type-changing options (such as `-nlt PROMOTE_TO_MULTI`) or
reprojection (`-t_srs`) to the raw copy; checks must see the data as
delivered. Authenticate through the environment or a password file, never
in the command line.

## Inventory with PostGIS

```sql
SELECT Find_SRID('qa', 'parcels_raw', 'geom') AS declared_srid;

SELECT ST_GeometryType(geom) AS geom_type,
       ST_SRID(geom)         AS srid,
       ST_NDims(geom)        AS dims,
       count(*)
FROM qa.parcels_raw
GROUP BY 1, 2, 3
ORDER BY 4 DESC;

SELECT ST_Extent(geom) FROM qa.parcels_raw;
```

## Null and empty geometries

```sql
SELECT count(*)                                    AS total,
       count(*) FILTER (WHERE geom IS NULL)        AS null_geom,
       count(*) FILTER (WHERE ST_IsEmpty(geom))    AS empty_geom
FROM qa.parcels_raw;
```

## Validity

```sql
SELECT count(*) FILTER (WHERE ST_IsValid(geom))     AS valid,
       count(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalid
FROM qa.parcels_raw
WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom);

SELECT (d).reason, count(*), min(parcel_id) AS example_id
FROM (
  SELECT parcel_id, ST_IsValidDetail(geom) AS d
  FROM qa.parcels_raw
  WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)
) AS x
GROUP BY (d).reason
ORDER BY 2 DESC;
```

## Duplicates

```sql
-- Identical geometry encoding (exact duplicates).
SELECT md5(ST_AsBinary(geom)) AS geom_hash, count(*), array_agg(parcel_id)
FROM qa.parcels_raw
WHERE geom IS NOT NULL
GROUP BY 1
HAVING count(*) > 1;

-- Duplicate identifiers.
SELECT parcel_id, count(*)
FROM qa.parcels_raw
GROUP BY parcel_id
HAVING count(*) > 1;
```

Binary equality misses geometries that are spatially equal but stored with a
different start vertex or orientation. `ST_Equals` tests spatial equality;
use it on candidate pairs found with a bounding-box join.

## Overlaps in a polygon coverage

Pairs whose interiors intersect with a two-dimensional overlap:

```sql
SELECT a.parcel_id AS a_id,
       b.parcel_id AS b_id,
       ST_Area(ST_Intersection(a.geom, b.geom)) AS overlap_area
FROM qa.parcels_raw AS a
JOIN qa.parcels_raw AS b
  ON a.parcel_id < b.parcel_id
 AND a.geom && b.geom
 AND ST_Relate(a.geom, b.geom, '2********')
ORDER BY overlap_area DESC;
```

Run on valid geometries only; intersections of invalid geometries can fail
or be wrong. Areas are in CRS units; in a geographic CRS they are square
degrees and meaningless. Cast to `geography` or use an appropriate
equal-area projection for area values.

PostGIS 3.4 and later (with GEOS 3.12 or later) also provide
`ST_CoverageInvalidEdges`, a window function that reports edges breaking
coverage rules within a tolerance.

## Gaps inside an expected boundary

```sql
SELECT (ST_Dump(ST_Difference(b.geom, u.geom))).geom AS gap
FROM qa.municipality_boundary AS b,
     (SELECT ST_Union(geom) AS geom FROM qa.parcels_raw) AS u;
```

Each resulting polygon is a candidate gap. Classify by area and shape; tiny
slivers often come from boundary digitizing differences rather than missing
features.

## Network endpoints (line layers)

```sql
-- Endpoints that touch no other line: candidate dangles or undershoots.
WITH ends AS (
  SELECT road_id, ST_StartPoint(geom) AS pt FROM qa.roads_raw
  UNION ALL
  SELECT road_id, ST_EndPoint(geom) FROM qa.roads_raw
)
SELECT e.road_id, ST_AsText(e.pt)
FROM ends AS e
WHERE NOT EXISTS (
  SELECT 1 FROM qa.roads_raw AS r
  WHERE r.road_id <> e.road_id AND ST_DWithin(r.geom, e.pt, :tolerance)
);
```

`ST_StartPoint` and `ST_EndPoint` apply to LineStrings; dump MultiLineStrings
first. Dead ends are legitimate in many networks; report them for review.

## Attribute checks

```sql
SELECT count(*) FILTER (WHERE land_use IS NULL)                     AS null_land_use,
       count(*) FILTER (WHERE land_use NOT IN ('R', 'C', 'I', 'A')) AS invalid_land_use,
       count(*) FILTER (WHERE area_declared_m2 <= 0)                AS nonpositive_area
FROM qa.parcels_raw;
```

Compare a declared area attribute with computed area in an appropriate CRS
to detect unit or CRS problems.

## Repairs (write to a copy, only with approval)

```sql
CREATE TABLE qa.parcels_repaired AS
SELECT parcel_id, ST_MakeValid(geom) AS geom, NOT ST_IsValid(geom) AS was_invalid
FROM qa.parcels_raw;

SELECT ST_GeometryType(geom), count(*)
FROM qa.parcels_repaired
WHERE was_invalid
GROUP BY 1;
```

```bash
ogr2ogr -makevalid parcels_repaired.gpkg parcels.gpkg
```

After repair, compare type counts and per-feature areas between raw and
repaired copies, and report every feature whose area or type changed.
