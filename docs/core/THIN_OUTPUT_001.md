# THIN_OUTPUT_001

## Purpose

Define one thin output bridge above the tightened core.

It is not a new control surface.
It is one smaller operator-facing translation layer over:

- `state`
- `report`
- optional `repair_packet`
- optional `doctor`
- optional verified checkpoint

## Modes

- `default`
  - short human-readable diagnosis plus next step
- `dev`
  - the same bridge plus compact technical lines for debugging

## Current reading

- thin output now helps read key non-green outcomes without replacing runtime truth
- verified checkpoint availability can now also surface in the default diagnosis
- checkpoint availability only counts when the verified checkpoint matches the same run/task contour
