// Single-thread float64 kernels. Caller owns inputs and outputs in contiguous arrays.
#include "cavity_planes.hpp"
#include <cstddef>
#include <limits>

namespace diffusion {
using Five = std::array<std::vector<double>, 5>;
using State = std::array<Five, 2>;
constexpr std::array<double, 5> weights{1./3, 1./6, 1./6, 1./6, 1./6};

void stream(const Five& post, Five& f, int n) {
    // Reflect both the sign and the normal discrete velocity at a boundary node.
    // This is the restriction of a doubly odd periodic extension to one quadrant.
    std::copy(post[0].begin(), post[0].end(), f[0].begin());
    for (int y = 0; y < n; ++y) {
        const int a = y*n;
        std::copy_n(post[1].data()+a, n-1, f[1].data()+a+1);
        std::copy_n(post[3].data()+a+1, n-1, f[3].data()+a);
        f[1][a] = -post[3][a+1];
        f[3][a+n-1] = -post[1][a+n-2];
    }
    std::copy_n(post[2].data(), n*(n-1), f[2].data()+n);
    std::copy_n(post[4].data()+n, n*(n-1), f[4].data());
    for (int x = 0; x < n; ++x) {
        f[2][x] = -post[4][n+x];
        f[4][n*(n-1)+x] = -post[2][n*(n-2)+x];
    }
}

void solve(const double* input, double* output, int n, int steps, double du,
           double dv, double rate, double horizon) {
    const int count = n*n;
    if (horizon == 0.) {
        std::copy_n(input, 2*count, output);
        return;
    }
    const double dt = horizon/steps;
    const double ratio = dt*(n-1)*(n-1);
    const double wu = 1./(.5+3*du*ratio), wv = 1./(.5+3*dv*ratio);
    const double half = -.5*std::expm1(-rate*dt);
    const double full = -.5*std::expm1(-2*rate*dt);
    State f, post;
    for (int c=0; c<2; ++c) for (int k=0; k<5; ++k) {
        f[c][k].resize(count);
        post[c][k].resize(count);
    }
    for (int k=0; k<5; ++k) for (int i=0; i<count; ++i) {
        const double u=input[i], v=input[count+i], mix=half*(v-u);
        f[0][k][i]=weights[k]*(u+mix);
        f[1][k][i]=weights[k]*(v-mix);
    }
    for (int t=0; t<steps; ++t) {
        const double transfer = (t+1==steps) ? half : full;
        #pragma omp simd
        for (int i=0; i<count; ++i) {
            const double u=f[0][0][i]+f[0][1][i]+f[0][2][i]+f[0][3][i]+f[0][4][i];
            const double v=f[1][0][i]+f[1][1][i]+f[1][2][i]+f[1][3][i]+f[1][4][i];
            for (int k=0; k<5; ++k) {
                const double a=f[0][k][i]+wu*(weights[k]*u-f[0][k][i]);
                const double b=f[1][k][i]+wv*(weights[k]*v-f[1][k][i]);
                const double q=transfer*(b-a);
                post[0][k][i]=a+q;
                post[1][k][i]=b-q;
            }
        }
        stream(post[0],f[0],n);
        stream(post[1],f[1],n);
    }
    for (int c=0; c<2; ++c) for (int i=0; i<count; ++i) {
        output[c*count+i]=f[c][0][i]+f[c][1][i]+f[c][2][i]+f[c][3][i]+f[c][4][i];
    }
}
}

extern "C" int d2q5(const double* input, double* output, int n, int steps,
                    double du, double dv, double rate, double horizon) noexcept {
    if (!input || !output || n<3 || n>4096 || steps<1 || !(du>0. && dv>0. &&
        rate>=0. && horizon>=0.) || !std::isfinite(du+dv+rate+horizon)) return 1;
    try { diffusion::solve(input,output,n,steps,du,dv,rate,horizon); }
    catch (...) { return 2; }
    return 0;
}

extern "C" int d2q9(const double* density, double* output, int n, int steps,
                    double speed) noexcept {
    if (!density || !output || n<3 || n>4096 || steps<1 || !(speed>0. && speed<1.)) return 1;
    try {
        const int count=n*n;
        const double omega=1./(.5+3.*(n-1)*speed/1000.);
        Planes a,b;
        for (int k=0; k<9; ++k) { a[k].resize(count); b[k].resize(count); }
        // At t=0 the supplied field is pre-streaming and at rest.
        // Do the first collision locally before using the published fused pull kernel.
        for (int i=0; i<count; ++i) {
            if (!(density[i]>0.) || !std::isfinite(density[i])) return 1;
            std::array<double,9> f;
            for (int k=0;k<9;++k) f[k]=w[k]*density[i];
            collide(f,a,i,omega,i/n==n-1,speed);
        }
        for (int t=1;t<steps;++t) { step(a,b,n,omega,speed); a.swap(b); }
        for (int y=0;y<n;++y) for (int x=0;x<n;++x) {
            const int i=y*n+x;
            const auto f=incoming(a,n,x,y);
            double rho=0.;
            for (double value:f) rho+=value;
            if (!(rho>0.) || !std::isfinite(rho)) return 3;
            output[i]= y==n-1 ? 1. : (f[1]+f[5]+f[8]-f[3]-f[6]-f[7])/(rho*speed);
            output[count+i]= y==n-1 ? 0. : (f[2]+f[5]+f[6]-f[4]-f[7]-f[8])/(rho*speed);
        }
    }
    catch (...) { return 2; }
    return 0;
}
