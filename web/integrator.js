// The simulator's integrator in plain JavaScript. The Python version in
// src/lagrangepointsimulator/numba_funcs.py is the reference: keep the two in step.
// A drift-kick-drift (leapfrog) step of the star, planet and satellite, as in Python.

const STATE_SIZE = 18; // star pos, star vel, planet pos, planet vel, sat pos, sat vel: 3 numbers each

// state: Float64Array(18) holding the first row. gStar and gPlanet are G times the masses.
// Returns every `step`-th row of the integration, from row 0, as a flat Float64Array of 18 numbers per row.
function integrate(timeStep, numSteps, gStar, gPlanet, state, step) {
  const half = 0.5 * timeStep;
  const rows = Math.floor(numSteps / step) + 1;
  const out = new Float64Array(rows * STATE_SIZE);
  out.set(state);

  let [sx, sy, sz, svx, svy, svz, px, py, pz, pvx, pvy, pvz, tx, ty, tz, tvx, tvy, tvz] = state;

  for (let k = 1; k <= numSteps; k++) {
    sx += svx * half; sy += svy * half; sz += svz * half;
    px += pvx * half; py += pvy * half; pz += pvz * half;
    tx += tvx * half; ty += tvy * half; tz += tvz * half;

    const ax = sx - px, ay = sy - py, az = sz - pz; // planet to star
    const bx = sx - tx, by = sy - ty, bz = sz - tz; // satellite to star
    const cx = px - tx, cy = py - ty, cz = pz - tz; // satellite to planet

    const d1 = Math.pow(Math.sqrt(ax * ax + ay * ay + az * az), -3);
    const d2 = Math.pow(Math.sqrt(bx * bx + by * by + bz * bz), -3);
    const d3 = Math.pow(Math.sqrt(cx * cx + cy * cy + cz * cz), -3);

    const starCoeff = -gPlanet * d1;
    const planetCoeff = gStar * d1;
    const satStarCoeff = gStar * d2;
    const satPlanetCoeff = gPlanet * d3;

    svx += starCoeff * ax * timeStep; svy += starCoeff * ay * timeStep; svz += starCoeff * az * timeStep;
    pvx += planetCoeff * ax * timeStep; pvy += planetCoeff * ay * timeStep; pvz += planetCoeff * az * timeStep;
    tvx += (satStarCoeff * bx + satPlanetCoeff * cx) * timeStep;
    tvy += (satStarCoeff * by + satPlanetCoeff * cy) * timeStep;
    tvz += (satStarCoeff * bz + satPlanetCoeff * cz) * timeStep;

    sx += svx * half; sy += svy * half; sz += svz * half;
    px += pvx * half; py += pvy * half; pz += pvz * half;
    tx += tvx * half; ty += tvy * half; tz += tvz * half;

    if (k % step === 0) {
      out.set([sx, sy, sz, svx, svy, svz, px, py, pz, pvx, pvy, pvz, tx, ty, tz, tvx, tvy, tvz], (k / step) * STATE_SIZE);
    }
  }

  return out;
}

// lets Node load this file in a test as well as the worker
if (typeof module !== "undefined") module.exports = { integrate, STATE_SIZE };
