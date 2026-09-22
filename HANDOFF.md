# Development Handoff

Last updated: 2026-09-22

## Current objective

Maintain the Garmin Connect Home Assistant integration and its fork-specific recovery and training-data enhancements.

## Current state

`main` is synchronized with `origin/main` at release 3.0.18.0. The integration pins the matching `ha-garmin` fork release and exposes additive training-load, HRV-range, and data-provenance fields without changing existing entity IDs.

## Work completed

- Released 3.0.18.0 with `ha-garmin` 0.1.48+zs1.
- Added training-load sensors and preserved recovery-data provenance.
- Preserved Recorder behavior for scalar and timeline data.

## Remaining work

Continue compatibility maintenance with upstream and validate future changes against Home Assistant, HACS, and the pinned library release.

## Important decisions and context

This is a long-lived fork. Preserve existing unique IDs and treat the matching `ha-garmin` release as a cross-repository dependency.

## Validation

No new code was present, so this handoff performed Git-level checks only. The release commit records the prior integration validation.

## Known issues / blockers

None identified in the working tree.

## Resume here

Check upstream changes and the sibling `ha-garmin` status before starting integration work.
