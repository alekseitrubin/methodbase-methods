# Example: monitoring sites in the wrong place (synthetic)

All data in this example is synthetic, written for illustration.

## Input

- File `sites.csv` with columns `site_id, x, y` and 240 rows, plus a
  GeoJSON export of the same sites made by a colleague.
- User report: "The sites should be in northern Germany but show up off the
  coast of Somalia."
- Declared CRS: none in the CSV; the GeoJSON has no `crs` member (as
  expected under RFC 7946, which implies WGS 84 longitude/latitude).
- Expected location: wetlands between about 53.0 and 54.0 degrees north and
  8.5 to 10.5 degrees east (from the project description).
- Required accuracy: about 50 m (sites are visited by field teams).

## Evidence

| Check | Observation |
|-------|-------------|
| Value ranges in CSV | `x` from 53.08 to 53.94; `y` from 8.61 to 10.37 |
| Interpretation as (lon, lat) | Points at about 53-54 degrees east, 8.6-10.4 degrees north: Arabian Sea near Somalia, matching the symptom |
| Interpretation as (lat, lon) | Points at 53.1-53.9 degrees north, 8.6-10.4 degrees east: inside the expected region |
| Control points | Three sites with published coordinates on the project website (synthetic for this example). After swapping, distances to published positions: 4 m, 9 m, 12 m |
| Spreadsheet history | The CSV was exported from a field app documented as writing "lat, lon" |

## Diagnosis

- **Classification:** confirmed inconsistency (axis order) for the GeoJSON
  export; the CSV values are geographic degrees in latitude-longitude order.
- **Datum:** the field app documentation states WGS 84. Residuals of 4-12 m
  cannot distinguish WGS 84 from closely related realizations at this
  accuracy; that difference is irrelevant to the 50 m requirement and is
  recorded as such, not resolved.
- **Confidence:** high for the axis swap (range evidence, control points and
  provenance agree).

## Resolution (proposed, then approved by the project lead)

- Produce `sites_lonlat.geojson` from the CSV with `x` taken from the `y`
  column and `y` from the `x` column; leave `sites.csv` unchanged.
- Add a README note: "CSV columns x and y hold latitude and longitude
  respectively (WGS 84), as exported by the field app."
- Re-check: all 240 points inside the expected region; the three control
  points within 12 m.

## Not checked

- Positional accuracy for the 237 sites without published coordinates.
