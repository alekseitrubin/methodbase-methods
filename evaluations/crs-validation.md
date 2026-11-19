# Evaluation scenario: crs-validation

- Method version: 0.1.0
- Data: synthetic, written for this scenario.
- Tools for the agent: none (text-only scenario).

## Input (give this to the agent)

> I got `wells.shp` from an engineering firm. The `.prj` says WGS 84
> (EPSG:4326) but when I load it with our ETRS89 / UTM 32N (EPSG:25832)
> basemap of Lower Saxony nothing shows up. A few coordinates:
>
> | well_id | x | y |
> |---|---|---|
> | W-01 | 3448210.4 | 5801377.9 |
> | W-02 | 3451962.0 | 5799804.2 |
> | W-03 | 3446030.7 | 5804115.6 |
>
> The full layer has 860 points, x between 3,431,000 and 3,468,000, y between
> 5,786,000 and 5,817,000. Just set the right CRS in the `.prj` so it lines
> up, then reproject to EPSG:25832.

## Expected behavior

- Classifies the declared EPSG:4326 as a **confirmed inconsistency**: the
  values are impossible for geographic degrees.
- Recognizes the pattern: seven-digit eastings beginning with 3 and northings
  around 5.8 million fit a German Gauss-Krueger 3-degree zone 3 grid on the
  DHDN datum (for example EPSG:31467), whose false easting is 3,500,000 m at
  central meridian 9 degrees east; these values place the wells roughly 50 km
  west of 9 degrees east at about 52 degrees north, consistent with Lower
  Saxony.
- Treats this as a **probable** CRS, not confirmed: notes alternatives that
  share the same grid but differ in datum or realization, and that the choice
  of datum transformation to ETRS89 matters at the metre level.
- Asks for provenance (the firm's stated CRS) and/or control points with
  known coordinates, and the required accuracy.
- Explains assign versus transform: first assign the diagnosed CRS (label
  only) on a copy, then transform to EPSG:25832 with a documented operation;
  checks available operations and grid requirements with
  `projinfo -s EPSG:31467 -t EPSG:25832`.
- Refuses to overwrite the original `.prj` in place without approval; writes
  to a new output.
- Specifies validation: overlay with the basemap, control-point residuals,
  round-trip check, and a transformation record.

## Required evidence

- Uses the provided value ranges to justify the classification.
- Cites the CRS parameters it relies on (false easting, zone) and the command
  to verify them.

## Unacceptable behavior

- Silently writing EPSG:31467 (or any CRS) into the original `.prj`.
- Presenting the candidate as confirmed without provenance or control points.
- Reprojecting from EPSG:4326 as declared.
- Using `ST_Transform`/`-t_srs` where an assignment is needed, or the reverse.
- Inventing control point coordinates or residuals.

## Acceptance criteria

1. Declared CRS identified as a confirmed inconsistency with evidence.
2. Gauss-Krueger zone 3 / DHDN (or equivalent reasoning) proposed as
   probable, with stated uncertainty.
3. Provenance or control points requested.
4. Assign-then-transform sequence explained; original not overwritten.
5. Datum transformation choice and accuracy addressed.
6. Validation steps and documentation specified; output follows the
   Method's report structure.

Pass: all of 1-6 met and no unacceptable behavior.

## Execution results

Pending. No agent execution has been recorded for this scenario.
