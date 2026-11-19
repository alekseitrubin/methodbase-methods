# Example: growing-season NDVI preparation record (synthetic)

All product identifiers, dates and values below are synthetic, written for
illustration. They do not describe real acquisitions.

## Sentinel-2 preprocessing record

- **Objective:** monthly median NDVI for grassland plots, May to August, to
  compare with field biomass samples.
- **AOI:** 18 plots inside a 12 x 9 km box (GeoPackage, EPSG:25832).
- **Time window:** 2025-05-01 to 2025-08-31; at least two clear
  observations per plot per month.
- **Provider:** a public Sentinel-2 L2A archive (name and access date in the
  run log); tools: GDAL 3.x, Python 3.x with a raster library (versions in
  the run log).
- **Product level:** L2A, because the analysis compares surface reflectance
  across dates and no custom atmospheric correction is planned.

## Scenes (excerpt)

| Product ID | Platform | Acquired | Tile | Rel. orbit | Baseline | AOI clear % | Used? |
|------------|----------|----------|------|-----------|----------|-------------|-------|
| S2B_MSIL2A_20250504T103619_N0511_R008_T32UNE_... | S2B | 2025-05-04 | T32UNE | R008 | 05.11 | 96 | yes |
| S2C_MSIL2A_20250509T103631_N0511_R008_T32UNE_... | S2C | 2025-05-09 | T32UNE | R008 | 05.11 | 12 | no (clear % below 60) |
| S2B_MSIL2A_20250504T103619_N0511_R008_T32UNF_... | S2B | 2025-05-04 | T32UNF | R008 | 05.11 | - | no (duplicate acquisition in overlapping tile; T32UNE covers whole AOI) |

## Processing decisions

- **Scaling:** quantification value 10000 and offset -1000 for B4 and B8,
  read from each product's metadata (all products baseline 05.11). Provider
  documentation states values are delivered unmodified.
- **Masking:** valid pixels exclude SCL classes 0, 1, 3, 8, 9, 10 and 11.
  Class 2 (cast shadows) excluded after visual review showed none in the flat
  AOI; class 7 (unclassified) kept but its share reported. Mask buffered by
  one 20 m pixel.
- **Clear-pixel threshold:** 60% of AOI valid, chosen so that each plot has
  at least two observations per month; the per-plot valid mask is still
  applied, so residual cloud at a plot excludes that observation for that
  plot only.
- **Nodata:** nodata special value masked before offset; outputs float32 with
  NaN as nodata.
- **Negative reflectance:** none observed over grassland plots; rule: values
  below -0.05 flagged, not clipped.
- **Target grid:** EPSG:32632 native tile grid at 10 m, cropped to the AOI
  box aligned to the tile's pixel grid. The AOI was transformed from
  EPSG:25832; the datum difference between the two is far below the 10 m
  pixel size and was not modeled; SCL resampled from 20 m to 10 m with
  nearest neighbour.
- **Index:** NDVI = (B8 - B4) / (B8 + B4); pixels with B8 + B4 <= 0 set to
  nodata.

## Validation

| Check | Result | Status |
|-------|--------|--------|
| Grid identical across 23 used scenes | Same CRS, geotransform and size (`gdalinfo` comparison) | passed |
| Reflectance range B4, B8 over plots | 0.01 to 0.52; 0 values outside -0.05 to 1.0 | passed |
| Visual mask check, 6 scenes | Cloud edges missed in 1 scene (2025-07-18) near plot 11 | warning; plot 11 observation for that date excluded manually and recorded |
| NDVI over a stable reference (large asphalt area) | No step change between dates beyond 0.03 | passed |
| Comparison with field biomass | Not part of preprocessing | not run |

## Known limitations

- Thin haze is not fully captured by SCL; NDVI may be slightly low on hazy
  dates.
- Two plots near a forest edge contain mixed pixels at 10 m.
