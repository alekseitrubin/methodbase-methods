# Sentinel-2 product facts to check

Supporting reference for the `sentinel2-preprocessing` Method. Summarized
from Copernicus SentiWiki pages listed in `SKILL.md`. Values can change with
new processing baselines; read them from each product's metadata and verify
against current documentation.

## Product levels

| Level | Content | Notes |
|-------|---------|-------|
| L1C | Top-of-atmosphere reflectance, orthorectified, in tiles | Includes B10 (cirrus) |
| L2A | Surface reflectance (formerly called bottom-of-atmosphere reflectance), produced with Sen2Cor | Adds Scene Classification (SCL), aerosol optical thickness, water vapour and other quality layers; no B10 |

Tiles are delivered in UTM projection on the WGS 84 datum and overlap their
neighbours, so one acquisition can appear in more than one tile.

## Bands and native resolution

| Resolution | Bands |
|------------|-------|
| 10 m | B2 (blue), B3 (green), B4 (red), B8 (near infrared, broad) |
| 20 m | B5, B6, B7 (red edge), B8A (narrow near infrared), B11, B12 (shortwave infrared) |
| 60 m | B1 (coastal aerosol), B9 (water vapour), B10 (cirrus, L1C only) |

L2A distributions commonly also provide bands resampled to coarser
resolutions (for example 20 m and 60 m versions). Prefer the native
resolution as input to your own resampling unless the provider's resampled
product is documented and fits your target grid.

Spectral response functions differ slightly between the Sentinel-2 units;
use the unit-specific characteristics from Copernicus documentation when
that matters for the analysis.

## Product identifiers

A product name such as
`S2B_MSIL2A_20250612T103629_N0511_R008_T32UNE_20250612T131512` (synthetic
example) encodes the platform, level, sensing start, processing baseline
(`N0511`), relative orbit (`R008`), tile (`T32UNE`) and a product
discriminator time. Record the full identifier, not just the date and tile.

## Radiometric scaling

- Digital numbers are converted to reflectance with a quantification value
  (10000 by default) and, from processing baseline 04.00 onward (operational
  since 25 January 2022), a band-dependent additive offset:
  `reflectance = (DN + offset) / quantification_value`.
- The offset is negative. It allows encoding reflectance slightly below zero
  over very dark surfaces.
- L1C metadata names the offset `RADIO_ADD_OFFSET`; L2A documentation refers
  to `BOA_ADD_OFFSET`. Read the values from the product's metadata file
  rather than hard-coding them.
- Products from baselines before 04.00 have no offset. Series spanning the
  change need per-product handling.
- Saturated and nodata pixels use special values declared in the metadata;
  mask them before conversion.

## Scene Classification (SCL) classes (L2A)

| Value | Class |
|-------|-------|
| 0 | No data |
| 1 | Saturated or defective |
| 2 | Cast shadows (topographic; called "dark area pixels" in older documentation) |
| 3 | Cloud shadows |
| 4 | Vegetation |
| 5 | Not vegetated |
| 6 | Water |
| 7 | Unclassified |
| 8 | Cloud, medium probability |
| 9 | Cloud, high probability |
| 10 | Thin cirrus |
| 11 | Snow or ice |

Known limitations documented by Copernicus include imperfect cloud criteria
(bright surfaces and geometric effects), snow on mountains detected as cloud,
cirrus detection that is probabilistic and limited by elevation, and mask
dilation rules. SCL is produced at 20 m. It is designed to separate clear,
cloudy and water pixels for processing, not as a land-cover map.

## Metadata to record per product

- Full product identifier and provider
- Platform, sensing time, tile, relative orbit
- Processing baseline and processing level
- Quantification value and per-band offsets used
- Special values (nodata, saturated) used for masking
- Product-level cloud percentage (informational only)
- AOI-level clear-pixel fraction (computed)
