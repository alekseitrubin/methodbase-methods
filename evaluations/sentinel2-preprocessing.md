# Evaluation scenario: sentinel2-preprocessing

- Method version: 0.1.0
- Data: synthetic, written for this scenario. Product identifiers are
  invented and do not describe real acquisitions.
- Tools for the agent: none (text-only scenario).

## Input (give this to the agent)

> I want to show NDVI change between summer 2021 and summer 2023 for a
> 30 x 20 km agricultural area that straddles two UTM zones (31 and 32). I
> downloaded L2A products: the 2021 ones from provider A, the 2023 ones from
> provider B (provider B says its files are "analysis-ready, harmonized").
> Examples:
>
> - `S2A_MSIL2A_20210712T103031_N0301_R108_T31UGU_...`
> - `S2A_MSIL2A_20210712T103031_N0301_R108_T32ULD_...`
> - `S2B_MSIL2A_20230714T103629_N0509_R008_T32ULD_...`
>
> My plan: keep only scenes with less than 20% cloud cover (from the product
> metadata), convert everything with `(DN - 1000) / 10000`, resample all
> bands including SCL to 10 m with bilinear interpolation, compute NDVI per
> tile, and subtract 2021 from 2023. Can you check my plan and write the
> processing steps?

## Expected behavior

- Points out that the 2021 products (processing baseline 03.01, before
  04.00) have no additive offset, so subtracting 1000 would bias them; the
  offset must be read per product from metadata.
- Notes that provider B's "harmonized" data may already have offsets
  applied or values shifted; requires checking provider B's documentation
  before any conversion, to avoid applying the offset twice.
- Explains that the product cloud percentage refers to the whole tile, not
  the AOI, and that 20% is not a universal standard; proposes AOI-level
  clear-pixel fractions with a threshold justified by the objective.
- Rejects bilinear resampling of SCL (categorical); nearest neighbour for
  SCL and masks.
- Requires a single target CRS and grid for the AOI spanning two zones,
  with one reprojection per band, instead of per-tile NDVI.
- Requires nodata masking before offset application, and SCL-based masking
  with documented class choices and known SCL limitations.
- Flags cross-provider and cross-baseline consistency as a risk for change
  detection and proposes a check on stable targets.
- Produces processing steps and a preprocessing record structure, with
  validation checks.

## Required evidence

- Uses the processing baseline numbers from the product names.
- Names the specific plan steps that are wrong and why.

## Unacceptable behavior

- Endorsing the plan as written.
- Applying one offset formula to all products.
- Claiming the resulting NDVI change is real without addressing
  baseline/provider consistency and residual cloud.
- Inventing provider B's convention instead of asking or directing to its
  documentation.
- Presenting any fixed cloud threshold as a standard.

## Acceptance criteria

1. Offset handling corrected per baseline (pre-04.00 vs 04.00+).
2. Provider harmonization risk identified (no double offset).
3. Tile-level cloud percentage and universal threshold issues identified.
4. SCL resampling corrected to nearest neighbour.
5. Single target grid across UTM zones required.
6. Nodata-before-offset and SCL limitations addressed.
7. Validation and preprocessing record specified.

Pass: all of 1-7 met and no unacceptable behavior.

## Execution results

Pending. No agent execution has been recorded for this scenario.
