# Room sizes by room type (houses and flats)

## Goal
Rooms in houses and flats get sizes that fit their type: a bathroom is small, a living room is big.
Sizes and room mix vary from home to home.

## Problem (measured, 150 houses + 150 flat blocks, median tiles)
- Flats: bathroom 15, bedroom 16, kitchen 20, living 24; 1,202 bathrooms vs 1,002 bedrooms.
- Houses: bathroom 9, living 30, bedroom 20, but hall 21, laundry 16, storage 16.
- Cause: `_split` cuts the floor into similar-sized pieces and kinds are assigned afterwards
  (`_assign_flat_kinds`, `_assign_house_kinds`), so a room's size does not depend on its type.
- Measuring script: scratchpad `measure.py` (re-run after the change to compare).

## In scope
- New `knoxbuild/sizing.py`:
  - size table per room kind: min / target / max tiles and max aspect, derived from the "kinds"
    table in `knoxbuild/room_solver.json` (m2 converted with the project's metres-per-tile).
  - `programme_for_flat(area, rng)` -> list of room kinds (studio, 1-bed, 2-bed, 3-bed by area).
  - `programme_for_house_floor(area, level, levels, rng)` -> list of room kinds (house path).
  - `split_by_targets(box, kinds, rng, mask)` -> rooms cut in proportion to their targets
    (recursive guillotine split: divide the kinds into two groups, cut at the ratio of their
    target areas, respect min size, minimum side `MIN_ROOM`).
- Flats first: `_apartment_rooms` cuts each flat with `split_by_targets`; kinds are set at creation
  and the room is marked `fixed`, so `_assign_flat_kinds` keeps them.
- Then houses, non-solver path only: `build_plan` house floors.

## Out of scope
- The OR-Tools solver (`room_solver`) and its dependency.
- Furniture placement (separate spec).
- Non-home buildings, hotels, exteriors.

## Must keep
- Every flat opens onto the corridor; the room at the door is the living room; flats touch the corridor.
- Stair, lift, window and door rules, party walls, open-plan flats, hotel flats unchanged.
- Floors with no fitting programme fall back to the current splitter (never fail a build).
- Deterministic for a given seed; CRLF line endings.

## Testing
- `tests/test_sizing.py`: size ranges respected per kind; bathroom median < bedroom median < living
  median over many seeds; programme counts by area; split fills the box exactly with no overlaps;
  fallback when the box is too small.
- Existing walkability/layout tests and `tools/selftest.py` pass.
- Re-run the 150+150 measurement and report the before/after medians.
