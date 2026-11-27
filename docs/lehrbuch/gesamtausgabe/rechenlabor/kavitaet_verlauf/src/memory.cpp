// Read-only CP2 collision and boundary kernels from the verified source archive.
#include "cp2_kernels.hpp"

// All fields use the same contiguous (time, y, x, component) float64 contract.
extern "C" int cp2_fields(int n, double re, const int* steps, int count, double* out) noexcept {
    if (n < 5 || re <= 0 || count < 1 || !steps || !out || steps[0] != 0) return 1;
    try {
        const int stride = (n+15)/16*16;
        const int plane = n*stride;
        const double rate = 1./(.5+3*(n-1)*lid/re);
        std::array<std::vector<double>,2> populations{std::vector<double>(9*plane), std::vector<double>(9*plane)};
        for (int j=0; j<9; ++j) std::fill_n(populations[0].data()+j*plane,plane,weight[j]);
        int k = 0;
        for (int i=0; i<count; ++i) {
            if (i && steps[i] <= steps[i-1]) return 2;
            for (; k<steps[i]; ++k) {
                const double* a = populations[k%2].data();
                double* b = populations[(k+1)%2].data();
                for (int x=0; x<n; ++x) {
                    edge(a,b,n,stride,plane,0,x);
                    edge(a,b,n,stride,plane,n-1,x);
                }
                for (int y=1; y<n-1; ++y) row(a,b,n,stride,plane,y,rate);
            }
            const double* a = populations[k%2].data();
            double* field = out + static_cast<std::size_t>(i)*n*n*2;
            for (int y=0; y<n; ++y) {
                for (int x=0; x<n; ++x) {
                    const int p = y*stride+x;
                    const int q = 2*(y*n+x);
                    if (y==n-1) { field[q]=1.; field[q+1]=0.; continue; }
                    double f[9], rho=0;
                    for (int j=0;j<9;++j) {f[j]=a[j*plane+p]; rho+=f[j];}
                    if (!(rho>0.) || !std::isfinite(rho)) return 3;
                    field[q]=(f[1]+f[5]+f[8]-f[3]-f[6]-f[7])/(rho*lid);
                    field[q+1]=(f[2]+f[5]+f[6]-f[4]-f[7]-f[8])/(rho*lid);
                }
            }
        }
    } catch (...) { return 4; }
    return 0;
}
