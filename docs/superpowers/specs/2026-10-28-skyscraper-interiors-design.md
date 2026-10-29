# Skyscraper interiors and the 32-storey limit

## Goal
Office towers get a real tower interior (central core, open floors, lobby, plant floor) instead of
stacked ordinary floors, and maps can build up to Build 42's height limit of 32 storeys.

## In scope
- New `knoxbuild/tower.py`, called from `build_building` in `knoxbuild/layout.py`.
- `LIMITS["max_levels"]` in `knoxbuild/settings.py`: 30 -> 32. Update the hint in `static/js/app.js`
  (`max_levels`) and any test that pins 30 (`tests/test_suggested.py`).
- `Plan.shaft` / `Plan.shaft_door` become lists so a building can have several lifts.

## Out of scope
- Exterior shape, facades, crowns, podiums. Existing glass facade and setback rules stay.
- Flat and hotel towers (`kind == "apartment"`) keep today's layout.
- A second fire stair. Towers keep one stair, as buildings do now.

## Trigger
`kind == "civic"` and `levels >= 12` and `min(width, height) >= 14`. Otherwise the current path runs
unchanged.

## Layout (identical core on every floor)
- **Core:** one rectangle near the footprint centre, wholly inside the mask (and inside the
  setback's upper mask). Holds the stair hall, a lift bank of 2-4 shafts (2x2 each, doors facing the
  lift lobby, as `_pick_shaft` does now), toilets, and a riser room.
- **Upper floors:** the ring around the core is cut into a few large office areas (`office` kind,
  few partitions). Every area has a door onto the lift lobby.
- **Ground floor:** lobby is the front room with the entrance and reception; core as above.
- **Plant floor:** at `round(levels * 0.9)`. Storage/mechanical rooms, no offices.
- Floors that share a footprint share a seed, as apartments do, so windows line up.

## Error handling
If no central core fits the mask, fall back to the existing path (never fail a build).

## Testing
- Unit tests (`tests/test_tower.py`): core identical on every floor; shafts inside the footprint;
  every office area reaches the lift lobby by a door; plant floor has no offices; fallback on a
  footprint with no room for a core.
- A 32-storey build through `build_building`; `max_levels` clamp at 32.
- `tools/selftest.py` and `python -m unittest discover -s tests` pass.
- Acceptance: 100 Summer Street, Boston MA (32 storeys). Overpass is unreachable from this machine,
  so the footprint needs the user's data or a hand-built fixture. Needs a look in the game: that a
  32-storey roof loads, and that the lifts work with the Elevators mod.
