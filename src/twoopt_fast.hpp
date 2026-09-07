#pragma once
#include <vector>
#include <algorithm>
#include <deque>
#include <cstddef>
#include "tsp.hpp"

// -----------------------------------------------------------------------------
// twoopt_fast.hpp: candidate-list 2-opt with don't-look bits (Bentley 1992).
//
// The reference two_opt() in src/ga.hpp scans ALL O(n^2) city pairs on every
// pass, most of which are hopeless (two far-apart cities essentially never
// participate in an improving 2-opt move once the tour is halfway decent).
// The classic fix, well established in the TSP local-search literature:
//
//   1. Precompute, for every city, a short list of its k nearest neighbours
//      (NeighbourLists::build). This is O(n^2 log k) but happens ONCE per
//      instance and is reused across every 2-opt call in the run.
//
//   2. Restrict the 2-opt search around a city `a` to candidates `c` drawn
//      from a's neighbour list only, and stop scanning the list as soon as
//      dist(a,c) >= dist(a,b) (b = a's current tour neighbour): the list is
//      sorted ascending, so no closer candidate remains, and any improving
//      move needs dist(a,c) < dist(a,b) (a necessary, well-known condition
//      for a 2-opt gain with this move structure). This turns an O(n) inner
//      scan into an O(k) one.
//
//   3. Don't-look bits + an active-city queue avoid re-examining cities whose
//      local neighbourhood hasn't changed since they were last found to have
//      no improving move. Only cities touched by an applied move (and their
//      old tour neighbours) are re-activated.
//
// Together these turn the O(passes * n^2) reference algorithm into something
// close to O(n) per pass in practice, at the cost of searching a strict
// subset of all possible 2-opt moves (only moves through a k-nearest-neighbour
// edge), so it can converge to a very slightly worse local optimum.
// -----------------------------------------------------------------------------

// ---- Neighbour lists ---------------------------------------------------------
//
// nbr[c*k + j] = the j-th nearest OTHER city to c (ascending by distance).
// Ties (equal distance) are broken by city index so the structure — and
// therefore every downstream search that consults it — is fully deterministic.
struct NeighbourLists {
    int n = 0, k = 0;
    std::vector<int> nbr;   // n*k, row-major

    void build(const TSPInstance& inst, int kk) {
        n = inst.n;
        k = std::min(kk, n > 0 ? n - 1 : 0);
        nbr.assign((size_t)n * (size_t)std::max(k, 0), 0);
        if (k <= 0) return;

        // Scratch: (distance, city) pairs for all other cities, then partial_sort
        // the k smallest. O(n) per city to build the candidate list, O(n log k)
        // to select+order the top k -> O(n^2 log k) total, done once.
        std::vector<std::pair<double, int>> cand;
        cand.reserve((size_t)n - 1);
        for (int c = 0; c < n; ++c) {
            cand.clear();
            for (int o = 0; o < n; ++o) {
                if (o == c) continue;
                cand.push_back({inst.dist(c, o), o});
            }
            int kk2 = std::min(k, (int)cand.size());
            std::partial_sort(cand.begin(), cand.begin() + kk2, cand.end(),
                [](const std::pair<double,int>& x, const std::pair<double,int>& y) {
                    if (x.first != y.first) return x.first < y.first;
                    return x.second < y.second;   // deterministic tie-break
                });
            for (int j = 0; j < kk2; ++j) nbr[(size_t)c * k + j] = cand[j].second;
            // If k > n-1 (tiny instances), pad remaining slots with the last
            // valid neighbour so `of(c)` is always safely readable k entries deep.
            for (int j = kk2; j < k; ++j) nbr[(size_t)c * k + j] = (kk2 > 0 ? cand[kk2 - 1].second : c);
        }
    }

    inline const int* of(int c) const { return nbr.data() + (size_t)c * k; }
};

// ---- Candidate-list 2-opt with don't-look bits --------------------------------
//
// t         : tour to optimise in place (permutation of 0..n-1).
// inst      : the instance (distances).
// nb        : precomputed neighbour lists for inst.
// max_moves : cap on the number of improving moves applied (-1 = run to
//             convergence, i.e. until the active queue empties).
//
// REVERSAL CAVEAT: to keep index/wrap bookkeeping simple and unambiguous, this
// implementation always reverses the INTERIOR (non-wrapping) segment between
// the two cut points, exactly as the reference two_opt() does — it does NOT
// pick the shorter of the two arcs. This is fully correct (either arc gives an
// equivalent tour) but foregoes the O(n/2) worst-case-reversal-cost bound that
// picking the shorter arc would give; the win here is purely from candidate
// pruning + don't-look bits, not from cheaper reversals.
inline void two_opt_fast(std::vector<int>& t, const TSPInstance& inst,
                         const NeighbourLists& nb, int max_moves = -1) {
    int n = (int)t.size();
    if (n < 4) return;

    std::vector<int> pos(n);
    for (int i = 0; i < n; ++i) pos[t[i]] = i;

    std::vector<char> in_queue(n, 1);
    std::vector<char> dont_look(n, 0);
    std::deque<int> queue;
    for (int c = 0; c < n; ++c) queue.push_back(c);

    auto succ_pos = [n](int p) { return p + 1 == n ? 0 : p + 1; };
    auto pred_pos = [n](int p) { return p == 0 ? n - 1 : p - 1; };

    auto activate = [&](int city) {
        if (in_queue[city]) return;
        dont_look[city] = 0;
        in_queue[city] = 1;
        queue.push_back(city);
    };

    // Reverse tour segment [i..j] (inclusive, interior, i<=j in array order),
    // keeping `pos` in sync.
    auto reverse_segment = [&](int i, int j) {
        while (i < j) {
            std::swap(t[i], t[j]);
            pos[t[i]] = i;
            pos[t[j]] = j;
            ++i; --j;
        }
    };

    int moves_applied = 0;

    // Try to find and apply a single improving move anchored at city `a`
    // (scanning both tour directions, candidates from nb.of(a)). Returns true
    // iff a move was applied. Factored out so it can be driven both by the
    // don't-look-bit queue (the fast path) and by the exhaustive verification
    // sweep below (the correctness backstop).
    auto try_improve = [&](int a) -> bool {
        bool improved_for_a = false;

        // Try both tour-neighbour directions of `a`: successor and predecessor.
        for (int dir = 0; dir < 2 && !improved_for_a; ++dir) {
            int pa = pos[a];
            int pb = (dir == 0) ? succ_pos(pa) : pred_pos(pa);
            int b = t[pb];
            double d_ab = inst.dist(a, b);

            const int* cand = nb.of(a);
            for (int ci = 0; ci < nb.k; ++ci) {
                int c = cand[ci];
                if (c == a) continue;
                double d_ac = inst.dist(a, c);
                if (d_ac >= d_ab) break;   // sorted ascending -> no closer candidate remains

                int pc = pos[c];
                int pd = (dir == 0) ? succ_pos(pc) : pred_pos(pc);
                int d = t[pd];
                if (d == a) continue;   // degenerate: c is adjacent to a on the wrong side

                double d_cd = inst.dist(c, d);
                double d_bd = inst.dist(b, d);
                double gain = d_ab + d_cd - d_ac - d_bd;

                if (gain > 1e-9) {
                    // Apply the move: new edges (a,c) and (b,d). This is realised by
                    // reversing the tour segment strictly between b and c (dir==0,
                    // successor case) or between c and b (dir==1, predecessor case),
                    // so that a becomes adjacent to c and b becomes adjacent to d.
                    int lo, hi;
                    if (dir == 0) {
                        // order along the array: ... a b ... c d ...  (or c d ... a b ...)
                        lo = pb; hi = pc;
                    } else {
                        // predecessor direction: ... d c ... b a ...
                        lo = pc; hi = pb;
                    }
                    if (lo <= hi) {
                        reverse_segment(lo, hi);
                    } else {
                        // The b..c (or c..b) span wraps past the array end. Reverse the
                        // complementary interior span instead (equivalent tour, same
                        // edge changes) to avoid wrap-around index arithmetic.
                        int tmp = lo; lo = hi + 1; hi = tmp - 1;
                        reverse_segment(lo, hi);
                    }

                    // Reactivating only {a,b,c,d} is the textbook rule, but it is
                    // provably insufficient here: reversing [lo,hi] preserves the
                    // *set* of tour-neighbours for every interior city but SWAPS
                    // which one is "successor" vs "predecessor" for each of them
                    // (array position i and i's neighbours i-1,i+1 both flip role
                    // under in-place reversal). Since this search treats succ/pred
                    // as distinct search directions (required for a valid 2-opt
                    // reconnection), a city whose direction-labels just flipped can
                    // have a newly-valid move that its stale don't-look bit hides,
                    // even though ITS incident edges never changed and it was never
                    // an endpoint of any move. Reactivating every city in [lo,hi]
                    // closes that gap; the extra work is the same order as the
                    // O(segment length) reversal/pos-update we already pay for.
                    for (int p = lo; p <= hi; ++p) activate(t[p]);
                    activate(a); activate(b); activate(c); activate(d);

                    ++moves_applied;
                    improved_for_a = true;
                    break;
                }
            }
        }
        return improved_for_a;
    };

    // Drain the active-city queue: the fast path. Cheap because most cities
    // quickly settle into "no improving move" and get skipped thereafter.
    auto drain_queue = [&]() {
        while (!queue.empty()) {
            if (max_moves >= 0 && moves_applied >= max_moves) return;

            int a = queue.front();
            queue.pop_front();
            in_queue[a] = 0;
            if (dont_look[a]) continue;   // stale entry (shouldn't happen, but safe)

            if (try_improve(a)) {
                activate(a);   // re-examine `a` itself; its local neighbourhood changed
            } else {
                dont_look[a] = 1;
            }
        }
    };

    drain_queue();

    // Exhaustive verification sweep: a correctness backstop for the theoretical
    // gap in plain "reactivate only the 4 move endpoints" don't-look-bit search
    // (see the comment above on direction-label flips for reversal-interior
    // cities). It costs O(n*k) — cheap relative to the reference O(n^2) scan —
    // and in practice finds nothing, since the interior-reactivation above
    // already closes the gap for the vast majority of cases; this just
    // guarantees a true fixed point rather than relying on that being complete.
    // Repeat until a full sweep applies zero moves, i.e. no improving move
    // remains anywhere among the candidate lists.
    while (!(max_moves >= 0 && moves_applied >= max_moves)) {
        bool any = false;
        for (int a = 0; a < n; ++a) {
            if (max_moves >= 0 && moves_applied >= max_moves) break;
            if (try_improve(a)) any = true;
        }
        if (!any) break;
        drain_queue();   // work off whatever the sweep reactivated, then re-verify
    }
}
