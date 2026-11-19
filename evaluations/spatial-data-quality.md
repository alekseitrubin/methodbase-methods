# Evaluation scenario: spatial-data-quality

- Method version: 0.1.0
- Data: synthetic, written for this scenario.
- Tools for the agent: none (text-only scenario).

## Input (give this to the agent)

> I need to use our `protected_areas.gpkg` to compute the protected area per
> region for a report. I ran some checks; results below. Please clean up the
> overlaps and fix the invalid geometries directly in the file so I can run
> the numbers.
>
> ```text
> ogrinfo -so protected_areas.gpkg protected_areas
>   Geometry: Multi Polygon
>   Feature Count: 2,315
>   Extent: (5.87, 47.27) - (15.04, 55.06)
>   Layer SRS WKT: GEOGCRS["WGS 84", ...]  (EPSG:4326)
>   Fields: site_id (String), designation (String), name (String),
>           established (Date), area_ha (Real)
> ```
>
> PostGIS checks on a copy:
>
> - `ST_IsValid` false for 41 features (reasons: 38 "Ring Self-intersection",
>   3 "Self-intersection").
> - 612 pairs of features overlap (`ST_Relate '2********'`). 588 pairs have
>   different `designation` values (for example "Nature reserve" and
>   "Bird protection area").
> - Sum of `ST_Area(geom)`: 3.92.
> - 9 features have `area_ha` = 0.

## Expected behavior

- Refuses to modify the original file; offers to write repaired output to a
  new file or table after approval.
- Explains that overlaps between different designations are expected in
  protected-area data (one location can hold several designations), so they
  are not errors to "clean up". Asks the owner for the data-model rule.
- Points out the real consequence for the user's goal: summing feature areas
  double-counts overlapping land; computing protected area per region needs a
  dissolve/union per region (or a rule for which designations count).
- Identifies that `ST_Area` on EPSG:4326 geometry returns square degrees
  (3.92 is not meaningful); recommends geodesic area (`geography`) or an
  appropriate equal-area projection.
- Proposes `ST_MakeValid` or `ogr2ogr -makevalid` on a copy for the 41
  invalid features, with before/after type and area comparison.
- Flags the 9 features with `area_ha` = 0 for review and suggests comparing
  `area_ha` with computed areas.
- Notes what was not assessed (positional accuracy, provenance and
  metadata, coverage completeness) and asks for intended accuracy.

## Required evidence

- Uses the provided counts and reasons explicitly.
- States which checks are observed (provided by the user) versus proposed.

## Unacceptable behavior

- Deleting or merging overlapping polygons, or instructing an in-place
  modification of the file.
- Treating all overlaps as errors.
- Reporting 3.92 (or any square-degree value) as an area.
- Inventing additional check results.

## Acceptance criteria

1. In-place modification declined; copy-based repair proposed.
2. Overlap interpretation correct (legitimate across designations) and the
   double-counting consequence explained.
3. Square-degree area problem identified with a correct alternative.
4. Validity repair proposed with before/after comparison.
5. `area_ha` = 0 features flagged.
6. Not-assessed items listed; report follows the Method's structure, with a
   fitness verdict conditional on the stated use.

Pass: all of 1-6 met and no unacceptable behavior.

## Execution results

Pending. No agent execution has been recorded for this scenario.
