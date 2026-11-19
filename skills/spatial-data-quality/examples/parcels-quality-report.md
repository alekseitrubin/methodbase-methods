# Example: parcel layer quality report (synthetic)

The dataset, counts and findings below are synthetic, written for
illustration.

## Spatial data quality report

- **Dataset:** `parcels.gpkg`, layer `parcels`, supplier delivery 2026-04,
  GeoPackage, 12,480 features.
- **Declared CRS:** EPSG:25832 (ETRS89 / UTM zone 32N).
- **Extent (observed):** x 561,200 to 574,900; y 5,931,000 to 5,944,300.
- **Intended use:** municipal land-use statistics per district; required
  positional accuracy 2 m. Not used for legal boundary decisions.
- **Tools:** GDAL 3.x, PostGIS 3.x with GEOS 3.x (exact versions recorded in
  the run log).

### Summary

**Fit with conditions** for district land-use statistics: after repairing 37
invalid polygons on a copy and confirming two overlap clusters with the
supplier. Positional accuracy was not assessed (no reference data).

### Checks

| Check | Method | Result | Status |
|-------|--------|--------|--------|
| Geometry types | `ST_GeometryType` group count | 12,301 MultiPolygon, 179 Polygon | warning (mixed single/multi) |
| Null / empty | null and `ST_IsEmpty` counts | 0 null, 2 empty (IDs 88412, 90117) | failed |
| Validity | `ST_IsValid`, `ST_IsValidDetail` | 12,441 valid, 37 invalid (31 self-intersection, 6 ring self-intersection) | failed |
| Count reconciliation | valid + invalid + null + empty | 12,441 + 37 + 0 + 2 = 12,480 | passed |
| CRS consistency | `Find_SRID`, `ST_SRID`, extent vs expected area | All 25832; extent inside the municipality's UTM 32N range | passed |
| Duplicate IDs | group by `parcel_id` | 0 | passed |
| Exact geometric duplicates | `md5(ST_AsBinary(geom))` | 4 pairs | warning |
| Overlaps | `ST_Relate '2********'` on valid features | 212 pairs; 205 under 0.5 m2; 7 between 40 and 610 m2 in two clusters | warning |
| Gaps vs municipal boundary | `ST_Difference` | 1,032 polygons, 1,029 under 1 m2; 3 larger gaps (roads and a lake) | finding for review |
| Attribute `land_use` | domain check | 0 null, 14 invalid code `X` | failed |
| Positional accuracy | no reference data | - | not assessed |

### Findings

1. **Invalid geometries (37).** Examples: 10233, 10871, 11420. Proposed:
   `ST_MakeValid` on a copy; report area changes per feature. Area-based
   statistics are unreliable for these features until repaired.
2. **Empty geometries (2).** IDs 88412, 90117 have attributes but no
   geometry. Ask the supplier whether these parcels were retired.
3. **Two overlap clusters (7 pairs, up to 610 m2).** Likely duplicated
   digitizing after a subdivision. Ask the supplier; do not delete.
4. **Small overlaps and gaps.** 205 overlaps under 0.5 m2 and 1,029 gaps
   under 1 m2 are consistent with boundary digitizing differences. Effect on
   district statistics is negligible relative to the 2 m requirement;
   recorded, no repair proposed.
5. **Three large gaps** coincide with road and water areas on the municipal
   map; likely by design (not parcels). Confirm with the supplier.
6. **Exact duplicates (4 pairs)** with different `parcel_id` values. Possible
   stacked records; confirm before removal.
7. **Invalid land-use code `X` (14).** Not in the data dictionary; ask the
   supplier for its meaning.

### Not assessed

- Positional accuracy (no reference data; metadata states capture at
  1:1,000 but no accuracy figure).
- Temporal validity (no per-feature update dates).

### Repairs applied

None. Repairs await approval.
