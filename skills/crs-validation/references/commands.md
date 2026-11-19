# Commands

Supporting reference for the `crs-validation` Method. Diagnostic commands
are read-only. Commands that write are marked and must target a new output
unless the owner approves an in-place change.

Command behavior differs between versions; record `projinfo --version`,
`gdalinfo --version` and `SELECT postgis_full_version();`.

## Inspect a CRS definition

```bash
projinfo EPSG:25832
```

Shows the WKT2 and PROJ representations, axis order and area of use.

```bash
gdalsrsinfo -o wkt2 parcels.gpkg
```

```bash
ogrinfo -so parcels.gpkg parcels
```

`ogrinfo` reports the layer CRS and the "Data axis to CRS axis mapping"
(for example `2,1` means the data stores longitude first while the CRS
defines latitude first).

## List candidate transformations and their accuracy

```bash
projinfo -s EPSG:4267 -t EPSG:4269 --spatial-test intersects
```

Lists coordinate operations between the two CRSs with stated accuracy and
whether grids are needed. Grid availability depends on local installation or
enabled PROJ network access.

## Transform sample points

```bash
echo "52.52 13.40" | cs2cs EPSG:4326 EPSG:25833
```

`cs2cs` follows the axis order of the CRS definition: EPSG:4326 input is
latitude then longitude. Use `-d <decimals>` to control output precision.

## Vector data with GDAL (writes a new file)

Assign a CRS without changing coordinates:

```bash
ogr2ogr -a_srs EPSG:25832 parcels_labeled.gpkg parcels.gpkg
```

Transform from a declared or overridden source CRS:

```bash
ogr2ogr -s_srs EPSG:25832 -t_srs EPSG:4326 parcels_wgs84.gpkg parcels.gpkg
```

Force a specific coordinate operation (GDAL 3 or later) when the default
choice is not the one you validated:

```bash
ogr2ogr -s_srs EPSG:4267 -t_srs EPSG:4269 -ct "<PROJ pipeline from projinfo>" out.gpkg in.gpkg
```

## Raster data with GDAL

- `gdal_translate -a_srs EPSG:xxxx in.tif out.tif` - assign, new file.
- `gdal_edit.py -a_srs EPSG:xxxx file.tif` - assign **in place**; needs
  approval and a backup.
- `gdalwarp -t_srs EPSG:xxxx in.tif out.tif` - transform (resamples pixels).

## PostGIS

```sql
-- Declared SRID of the column and of the values.
SELECT Find_SRID('public', 'sites', 'geom');
SELECT ST_SRID(geom), count(*) FROM public.sites GROUP BY 1;

-- What does the SRID mean in this database?
SELECT auth_name, auth_srid, srtext FROM spatial_ref_sys WHERE srid = 4326;

-- Extent and value ranges.
SELECT min(ST_XMin(geom)), max(ST_XMax(geom)),
       min(ST_YMin(geom)), max(ST_YMax(geom))
FROM public.sites;

-- Test an axis swap on a sample without changing data.
SELECT site_id, ST_AsText(geom) AS as_stored, ST_AsText(ST_FlipCoordinates(geom)) AS swapped
FROM public.sites
LIMIT 10;

-- Assign (label only) versus transform (new coordinates), as queries.
SELECT ST_SetSRID(geom, 25832) FROM public.sites;   -- assign
SELECT ST_Transform(geom, 4326) FROM public.sites;  -- transform

-- Geodesic length or area instead of degrees.
SELECT ST_Area(geom::geography) FROM public.parcels_wgs84;
```

`UpdateGeometrySRID` and `ALTER TABLE ... ALTER COLUMN geom TYPE ... USING
ST_SetSRID(...)` change the table in place; they are writes and need
approval.

## Round-trip check

Transform sample points to the target CRS and back with the same operation;
differences should be at numerical precision. A larger difference suggests a
non-invertible or different operation was chosen in one direction.
