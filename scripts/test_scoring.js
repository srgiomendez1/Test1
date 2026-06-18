/* Minimal no-dependency test for the scoring rules. Run: node scripts/test_scoring.js */
const assert = require("assert");
require("../assets/js/scoring.js"); // sets globalThis.Scoring
const { scoreOne, computeStandings } = globalThis.Scoring;

// scoreOne
assert.deepStrictEqual(scoreOne([2, 0], [2, 0]), { points: 3, exact: true, outcome: true }, "exact -> 3 (2+1)");
assert.deepStrictEqual(scoreOne([3, 1], [2, 0]), { points: 1, exact: false, outcome: true }, "home win -> 1");
assert.deepStrictEqual(scoreOne([1, 1], [2, 2]), { points: 1, exact: false, outcome: true }, "draw outcome -> 1");
assert.deepStrictEqual(scoreOne([0, 1], [2, 0]), { points: 0, exact: false, outcome: false }, "wrong -> 0");
assert.deepStrictEqual(scoreOne([1, 1], [2, 0]), { points: 0, exact: false, outcome: false }, "draw vs win -> 0");
assert.deepStrictEqual(scoreOne(null, [2, 0]), { points: 0, exact: false, outcome: false }, "no pred -> 0");

// computeStandings
const bets = {
  players: ["Ana", "Beto"],
  predictions: {
    "d|A|B": { Ana: [2, 0], Beto: [1, 0] }, // actual 2-0: Ana exact(2), Beto outcome(1)
    "d|C|D": { Ana: [0, 0], Beto: [1, 1] }, // live 1-1: counted only if countLive
  },
};
const results = {
  matches: {
    "d|A|B": { score: [2, 0], status: "finished" },
    "d|C|D": { score: [1, 1], status: "live" },
  },
};
const noLive = computeStandings(bets, results, false);
assert.strictEqual(noLive[0].player, "Ana");
assert.strictEqual(noLive.find((r) => r.player === "Ana").points, 3, "Ana exact = 3 w/o live");
assert.strictEqual(noLive.find((r) => r.player === "Beto").points, 1, "Beto outcome = 1 w/o live");

const withLive = computeStandings(bets, results, true);
const beto = withLive.find((r) => r.player === "Beto");
assert.strictEqual(beto.points, 4, "Beto 1 + live exact 3 = 4");
assert.strictEqual(beto.provisional, 3, "Beto provisional 3");

console.log("All scoring tests passed ✔");
