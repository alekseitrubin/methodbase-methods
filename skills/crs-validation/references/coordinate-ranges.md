# Coordinate ranges and symptom patterns

Supporting reference for the `crs-validation` Method. Ranges are approximate
plausibility bounds for quick screening, not definitions. Always confirm with
the CRS definition and its area of use (`projinfo EPSG:<code>`).

## Typical value ranges

| Coordinate type | x / first value | y / second value | Notes |
|-----------------|-----------------|------------------|-------|
| Geographic, degrees (lon, lat) | -180 to 180 (sometimes 0 to 360) | -90 to 90 | Order depends on CRS definition and tool convention |
| UTM, metres, northern hemisphere | about 160,000 to 840,000 within the zone | 0 to about 9,350,000 | False easting 500,000 at the central meridian |
| UTM, metres, southern hemisphere | as above | about 1,100,000 to 10,000,000 | False northing 10,000,000 |
| Web Mercator (EPSG:3857), metres | -20,037,508 to 20,037,508 | about the same bound | Latitude limited to about ±85 degrees |
| National or regional grids | Varies; check false easting/northing and area of use | | Often designed to keep values positive in the region |

## Symptom patterns

| Symptom | Likely cause | Check |
|---------|--------------|-------|
| Data appears in the wrong hemisphere or ocean, mirrored across the diagonal | Latitude and longitude swapped | Swap known points; check axis mapping in GDAL output |
| Latitude values greater than 90 in a geographic CRS | Swap, or projected values labeled geographic | Value ranges |
| All data in a tiny area near 0,0 in a projected map | Degrees labeled as metres | Value ranges |
| Data spread over thousands of degrees or rejected by tools | Metres labeled as degrees | Value ranges |
| Constant offset of a few to tens or hundreds of metres | Datum mismatch, or missing/ballpark datum transformation | `projinfo -s -t` operations and accuracy |
| Offset of exactly a false easting or northing (for example 500,000 m) | Wrong projection parameters or wrong zone | Zone and parameters vs location |
| Wrong UTM zone: offset by roughly the width of a zone in longitude | Zone mislabeled | Transform with neighboring zones |
| Scaled by about 3.28 | Metre/foot confusion | Units in definition |
| Small proportional error growing with distance from origin | Foot definition mismatch (international vs US survey) or wrong scale factor | Units and parameters |
| Areas far too large at high latitudes | Measuring in Web Mercator | Use geodesic or equal-area calculation |

## Distinguishable versus indistinguishable differences

If two candidate CRSs place the same coordinates less apart than the
positional accuracy of the data (or of the reference data), the data cannot
show which is correct. Report this as insufficient information and rely on
provenance. Typical examples are realizations of closely related geodetic
datums whose differences are at the metre level or below, compared with data
digitized at much lower accuracy.
