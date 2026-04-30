export function parseFeatureInput(input) {
  return input
    .split(/[\s,]+/)
    .map((value) => Number.parseFloat(value))
    .filter((value) => Number.isFinite(value))
}