# THIN_OUTPUT_READING_TEST_001

Run one short reading pass on `thin-output + generate-prompt` over a non-green stop contour.

## Purpose

This is not a new UX layer.
It is a narrow check that the thin output bridge and prompt bridge actually reduce reading tax on a real non-green path.

## Canonical artifacts

- `fixtures/repair_convergence_run_004/report.json`
- `fixtures/repair_convergence_run_004/repair_packet.json`
- `fixtures/thin_output_reading_test_001/thin_output.json`
- `fixtures/thin_output_reading_test_001/prompt.json`
- `fixtures/thin_output_reading_test_001/reading.json`

## Expected reading

The reading record should show:
- key markers preserved
- current step preserved
- next step preserved
- a materially shorter bridge than raw `report + repair_packet`

This slice matters because a bridge only earns its place if it reduces reading burden without dropping the truth we actually need.
