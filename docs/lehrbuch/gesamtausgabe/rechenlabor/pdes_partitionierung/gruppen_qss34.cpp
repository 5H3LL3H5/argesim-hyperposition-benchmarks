// Full-field vector quantization for the incompressible CP2 cavity.
// Grid is extracted without changes from the book's gruppen_qss.cpp.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
#include "wirbel_gitter.hpp"

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

struct TaylorField {
    Grid grid;
    int order;
    std::vector<V> z, psi, zx, zy, u, v;

    TaylorField(int n, int p) : grid(n, 1000.), order(p),
        z(p + 1, V(n*n)), psi(p, V(n*n)), zx(p, V(n*n)), zy(zx), u(zx), v(zx) {}

    // In F(q) the advection term is quadratic. Collect each coefficient
    // in powers of elapsed time before integrating it once.
    double expand() {
        const int n = grid.n;
        double highest = 0.;
        for (int k = 0; k < order; ++k) {
            grid.geometry(z[k], psi[k], k == 0 ? 1. : 0.);
            for (int y = 1; y < n - 1; ++y) {
                for (int x = 1; x < n - 1; ++x) {
                    const int i = y*n+x;
                    u[k][i] = grid.dy(psi[k], i);
                    v[k][i] = -grid.dx(psi[k], i);
                    zx[k][i] = grid.dx(z[k], i);
                    zy[k][i] = grid.dy(z[k], i);
                    double rhs = grid.diffus(z[k], i);
                    for (int j = 0; j <= k; ++j)
                        rhs -= u[j][i]*zx[k-j][i] + v[j][i]*zy[k-j][i];
                    z[k+1][i] = rhs / (k+1);
                    if (!std::isfinite(z[k+1][i])) throw std::runtime_error("Non-finite coefficient");
                    if (k+1 == order) highest = std::max(highest, std::abs(z[k+1][i]));
                }
            }
        }
        return highest;
    }

    double at(int i, double h) const {
        double value = z[order][i];
        for (int k = order-1; k >= 0; --k) value = value*h + z[k][i];
        return value;
    }

    void advance(double h) {
        for (int y = 1; y < grid.n-1; ++y)
            for (int x = 1; x < grid.n-1; ++x) {
                const int i = y*grid.n+x;
                z[0][i] = at(i,h);
            }
    }

    void observe(const fs::path &target, double h) const {
        V row(grid.m);
        std::ofstream output(target, std::ios::binary);
        for (int y = 1; y < grid.n-1; ++y) {
            for (int x = 1; x < grid.n-1; ++x) row[x-1] = at(y*grid.n+x,h);
            output.write(reinterpret_cast<const char*>(row.data()),
                         static_cast<std::streamsize>(row.size()*sizeof(double)));
        }
        output.close();
        if (!output) throw std::runtime_error("Field write failed");
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 6) throw std::runtime_error("N order quantum observation_ticks_file output_dir");
        const int n = std::stoi(argv[1]), order = std::stoi(argv[2]);
        const double quantum = std::stod(argv[3]);
        if (n < 5 || (order != 3 && order != 4) || !(quantum > 0.) || !std::isfinite(quantum))
            throw std::runtime_error("Invalid grid, order or quantum");
        std::ifstream input(argv[4]);
        std::vector<int> ticks;
        for (int k; input >> k;) {
            if (k <= 0 || (!ticks.empty() && k <= ticks.back())) throw std::runtime_error("Unsorted ticks");
            ticks.push_back(k);
        }
        if (ticks.empty() || !input.eof()) throw std::runtime_error("Invalid observations");
        const fs::path target(argv[5]);
        fs::create_directories(target);
        std::ofstream history(target/"history.csv");
        history.exceptions(std::ios::badbit | std::ios::failbit);
        history << "tick,t_star,segments,kernel_s,max_band_defect\n" << std::setprecision(17);
        TaylorField flow(n, order);
        const double dt = 0.1/(n-1), end = ticks.back()*dt;
        std::size_t next = 0, segments = 0;
        double now = 0., io = 0., peak_defect = 0.;
        const auto start = Clock::now();
        while (now < end) {
            const double peak = flow.expand();
            const double remaining = end-now;
            const double step = peak > 0. ? std::min(remaining,std::pow(quantum/peak,1./order)) : remaining;
            if (!(now+step > now)) throw std::runtime_error("Lost time resolution");
            const double stop = step == remaining ? end : now+step;
            peak_defect = std::max(peak_defect, peak*std::pow(step,order));
            if (peak_defect > quantum*(1.+1.e-12)) throw std::runtime_error("Quantization band exceeded");
            ++segments;
            // Commit the step before stopping the core timer for its observations.
            // Only z[0] changes on commit. Save interior samples before overwriting it.
            const auto before = Clock::now();
            std::size_t first = next;
            while (next < ticks.size() && ticks[next]*dt <= stop) {
                flow.observe(target/("z_"+std::to_string(ticks[next])+".bin"),ticks[next]*dt-now);
                ++next;
            }
            if (first != next) io += std::chrono::duration<double>(Clock::now()-before).count();
            flow.advance(step);
            now = stop;
            if (first != next) {
                const auto stamp = Clock::now();
                const double elapsed = std::chrono::duration<double>(stamp-start).count()-io;
                for (auto index = first; index < next; ++index)
                    history << ticks[index] << ',' << ticks[index]*dt << ',' << segments << ','
                            << elapsed << ',' << peak_defect << '\n';
                history.flush();
                io += std::chrono::duration<double>(Clock::now()-stamp).count();
            }
        }
        if (next != ticks.size()) throw std::runtime_error("Missing field");
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
