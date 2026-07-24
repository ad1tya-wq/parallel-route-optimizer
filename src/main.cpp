#include <iostream>
#include <iomanip>
#include <string>
#include <cstdlib>
#include <fstream>
#include "tsp.hpp"
#include "ga.hpp"
#include "island.hpp"
#include "svg.hpp"

// -----------------------------------------------------------------------------
// ParallelRoute CLI.
//   ./ParallelRoute --mode island-dtam --gen uniform --n 500 --threads 6 \
//                   --pop 240 --generations 2000 --twoopt --svg route.svg
// Prints a human summary; optionally appends a machine-readable row to --out
// (for the benchmark harness) and writes a convergence log + SVG route.
// -----------------------------------------------------------------------------

static const char* USAGE =
"ParallelRoute - parallel island-model GA route optimizer\n"
"Usage:\n"
"  --mode <serial|island-fixed|island-dtam>   optimisation engine (default serial)\n"
"  --in <file.tsp>                            load a TSPLIB EUC_2D instance\n"
"  --gen <uniform|circle> --n <N>             OR generate an instance of size N\n"
"  --seed <s>                                 RNG seed (default 1)\n"
"  --threads <T>                              islands / OpenMP threads (default 1)\n"
"  --pop <P>                                  total population (default 240)\n"
"  --generations <G>                          total generations (default 1000)\n"
"  --time <sec>                               wall-clock budget (overrides -G stop)\n"
"  --epoch-len <E>                            generations per epoch (default 10)\n"
"  --migrate-interval <epochs>                P1 migration period (default 1)\n"
"  --migrants <K>                             migrants exchanged (default 4)\n"
"  --tau <t>                                  DTAM stagnation threshold (default 0.15)\n"
"  --twoopt [--twoopt-rate r] [--twoopt-passes p]   enable 2-opt local search\n"
"  --mutation <r> --tournament <k> --elites <e>     GA knobs\n"
"  --target-gap <Y>                           record time-to-reach Y% gap\n"
"  --log-interval <n>                         convergence-log cadence (default 10)\n"
"  --csv-log <file>                           write per-row convergence log\n"
"  --out <file>                               append a summary row (benchmark aggregation)\n"
"  --svg <file>                               render best route to SVG\n"
"  --quiet                                    suppress the human summary\n";

int main(int argc, char** argv) {
    EngineParams P;
    std::string in_file, gen_kind, out_file, csv_log, svg_file;
    int n = 200;
    bool quiet = false;

    auto need = [&](int& i) -> std::string {
        if (i + 1 >= argc) { std::cerr << "missing value for " << argv[i] << "\n"; std::exit(2); }
        return argv[++i];
    };
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if      (a == "--mode") {
            std::string m = need(i);
            if (m == "serial") P.mode = Mode::Serial;
            else if (m == "island-fixed") P.mode = Mode::IslandFixed;
            else if (m == "island-dtam")  P.mode = Mode::IslandDTAM;
            else { std::cerr << "unknown mode: " << m << "\n"; return 2; }
        }
        else if (a == "--in")               in_file = need(i);
        else if (a == "--gen")              gen_kind = need(i);
        else if (a == "--n")                n = std::stoi(need(i));
        else if (a == "--seed")             P.seed = std::stoull(need(i));
        else if (a == "--threads")          P.threads = std::stoi(need(i));
        else if (a == "--pop")              P.ga.pop_size = std::stoi(need(i));
        else if (a == "--generations")      P.generations = std::stoi(need(i));
        else if (a == "--time")             P.time_budget = std::stod(need(i));
        else if (a == "--epoch-len")        P.epoch_len = std::stoi(need(i));
        else if (a == "--migrate-interval") P.migrate_interval = std::stoi(need(i));
        else if (a == "--migrants")         P.migrants = std::stoi(need(i));
        else if (a == "--tau")              P.tau = std::stod(need(i));
        else if (a == "--twoopt")           P.ga.use_2opt = true;
        else if (a == "--twoopt-rate")      P.ga.two_opt_rate = std::stod(need(i));
        else if (a == "--twoopt-passes")    P.ga.two_opt_passes = std::stoi(need(i));
        else if (a == "--mutation")         P.ga.mutation_rate = std::stod(need(i));
        else if (a == "--tournament")       P.ga.tournament_k = std::stoi(need(i));
        else if (a == "--elites")           P.ga.elites = std::stoi(need(i));
        else if (a == "--target-gap")       P.target_gap = std::stod(need(i));
        else if (a == "--log-interval")     P.log_interval = std::stoi(need(i));
        else if (a == "--csv-log")          csv_log = need(i);
        else if (a == "--out")              out_file = need(i);
        else if (a == "--svg")              svg_file = need(i);
        else if (a == "--quiet")            quiet = true;
        else if (a == "-h" || a == "--help"){ std::cout << USAGE; return 0; }
        else { std::cerr << "unknown arg: " << a << "\n" << USAGE; return 2; }
    }

    // Build the instance.
    TSPInstance inst;
    try {
        if (!in_file.empty())            inst = load_tsplib(in_file);
        else if (gen_kind == "uniform")  inst = gen_uniform(n, P.seed);
        else if (gen_kind == "circle")   inst = gen_circle(n);
        else { std::cerr << "specify --in <file> or --gen <uniform|circle> --n <N>\n"; return 2; }
    } catch (const std::exception& e) { std::cerr << "error: " << e.what() << "\n"; return 1; }

    Result R = run_engine(inst, P);

    double best = R.best.len;
    double gap  = inst.gap_percent(best);

    if (!quiet) {
        std::cout << std::fixed << std::setprecision(2);
        std::cout << "instance      : " << inst.name << "  (n=" << inst.n << ", "
                  << (inst.rounded ? "EUC_2D/rounded" : "euclidean") << ")\n";
        std::cout << "mode          : " << mode_name(R.mode) << "\n";
        std::cout << "threads       : " << R.threads << "   island_pop=" << R.island_pop
                  << "   total_pop=" << (R.threads * R.island_pop) << "\n";
        std::cout << "generations   : " << R.effective_generations << "\n";
        std::cout << "best length   : " << best << "\n";
        if (inst.known_opt > 0)
            std::cout << (inst.opt_is_exact ? "opt (exact)   : " : "opt (estimate): ")
                      << inst.known_opt << "   gap=" << gap << "%\n";
        std::cout << "wall time     : " << R.total_time << " s\n";
        if (R.mode != Mode::Serial) std::cout << "migrations    : " << R.total_migrations << "\n";
        if (P.target_gap > 0)
            std::cout << "time-to-" << P.target_gap << "%   : "
                      << (R.time_to_target < 0 ? -1.0 : R.time_to_target) << " s\n";
    }

    if (!csv_log.empty()) {
        std::ofstream o(csv_log);
        o << "generation,elapsed,best_len,gap,diversity,migrations\n";
        for (auto& r : R.log)
            o << r.generation << "," << r.elapsed << "," << r.best_len << ","
              << r.gap << "," << r.diversity << "," << r.migrations << "\n";
    }

    if (!out_file.empty()) {
        bool exists = std::ifstream(out_file).good();
        std::ofstream o(out_file, std::ios::app);
        if (!exists)
            o << "mode,instance,n,threads,island_pop,total_pop,generations,seed,twoopt,"
                 "best_len,gap,total_time,time_to_target,migrations\n";
        o << mode_name(R.mode) << "," << inst.name << "," << inst.n << "," << R.threads << ","
          << R.island_pop << "," << (R.threads * R.island_pop) << "," << R.effective_generations << ","
          << P.seed << "," << (P.ga.use_2opt ? 1 : 0) << ","
          << best << "," << gap << "," << R.total_time << "," << R.time_to_target << ","
          << R.total_migrations << "\n";
    }

    if (!svg_file.empty()) { write_svg(svg_file, inst, R.best.tour, best); }
    return 0;
}
