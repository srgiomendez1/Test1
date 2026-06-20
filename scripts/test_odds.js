/* Sanity tests for the odds model. Run: node scripts/test_odds.js */
const assert = require("assert");
require("../assets/js/odds.js");
const { poisson, matchOdds, teamStrengths, lambdasFor, dec } = globalThis.Odds;

const close = (a, b, eps, msg) => assert.ok(Math.abs(a - b) < (eps || 1e-6), `${msg}: ${a} vs ${b}`);

// Poisson sums to ~1 over enough terms
let s = 0; for (let k = 0; k <= 30; k++) s += poisson(k, 1.4);
close(s, 1, 1e-6, "poisson sums to 1");

// 1X2 and O/U partitions sum to 1
const o = matchOdds({ lh: 1.6, la: 1.1 });
close(o.p1 + o.pX + o.p2, 1, 1e-3, "1X2 sums to 1");
close(o.over + o.under, 1, 1e-3, "over+under sums to 1");
assert.ok(o.p1 > o.p2, "stronger home favored");

// Symmetric lambdas => p1 ≈ p2
const sym = matchOdds({ lh: 1.3, la: 1.3 });
close(sym.p1, sym.p2, 1e-9, "symmetric => p1==p2");

// Live: no time left => current score is certain
const done = matchOdds({ lh: 2, la: 2, curH: 2, curA: 1, remFrac: 0 });
close(done.p1, 1, 1e-9, "remFrac 0 => home (leading) wins for sure");
assert.strictEqual(done.scores[0].s, "2-1", "certain final score");

// Ratings-based lambdas: stronger rating => favored
const ratings = { A: 1.0, B: -1.0 };
const { lh, la } = lambdasFor({ home: "A", away: "B" }, ratings);
assert.ok(lh > la, "higher-rated home favored");
const oA = matchOdds(lambdasFor({ home: "A", away: "B" }, ratings));
const oB = matchOdds(lambdasFor({ home: "B", away: "A" }, ratings));
assert.ok(oA.p1 > 0.6 && oB.p1 < 0.4, "rating gap drives result prob");

// teamStrengths still works
const S = teamStrengths([{ group: "Group A", status: "finished", score: [3, 0], home: "A", away: "B" }]);
assert.ok(S.teams["A"].atk > S.teams["B"].atk, "A attacks better than B");

// decimal odds: fair vs with margin
close(dec(0.5), 2, 1e-9, "p .5 => 2.00 fair");
assert.ok(dec(0.5, 0.07) < 2, "margin shortens odds");

console.log("All odds tests passed ✔");
