// Uniform initial density. Each buffer holds postcollision populations in D2Q9 order.
// The incoming populations for both collision and output follow the CP2 out-of-range
// rule: a missing source leaves the postcollision value at the destination in place.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Planes = std::array<std::vector<double>, 9>;
constexpr std::array<int,9> cx{0,1,0,-1,0,1,-1,-1,1};
constexpr std::array<int,9> cy{0,0,1,0,-1,1,1,-1,-1};
constexpr std::array<int,9> opposite{0,3,4,1,2,7,8,5,6};
constexpr std::array<double,9> w{4./9,1./9,1./9,1./9,1./9,1./36,1./36,1./36,1./36};

std::array<double,9> incoming(const Planes& a, int n, int x, int y) {
    std::array<double,9> f;
    for (int k=0; k<9; ++k) {
        const int sx=x-cx[k], sy=y-cy[k];
        const int source=(sx<0 || sx>=n || sy<0 || sy>=n) ? y*n+x : sy*n+sx;
        f[k]=a[k][source];
    }
    return f;
}

inline void collide(const std::array<double,9>& f, Planes& b, int p, double omega,
                    bool lid, double speed) {
    const double rho=f[0]+f[1]+f[2]+f[3]+f[4]+f[5]+f[6]+f[7]+f[8];
    const double u=lid ? speed : (f[1]+f[5]+f[8]-f[3]-f[6]-f[7])/rho;
    const double v=lid ? 0.0 : (f[2]+f[5]+f[6]-f[4]-f[7]-f[8])/rho;
    const double base=1-1.5*(u*u+v*v);
    for (int k=0; k<9; ++k) {
        const double d=cx[k]*u+cy[k]*v;
        const double eq=w[k]*rho*(base+d*(3.+4.5*d));
        b[k][p]=lid ? eq : f[k]+omega*(eq-f[k]);
    }
}

void step(const Planes& a, Planes& b, int n, double omega, double speed) {
    for (int y=1; y<n-1; ++y) {
        // Direction planes make consecutive x values contiguous for the compiler.
        #pragma omp simd
        for (int x=1; x<n-1; ++x) {
            const int p=y*n+x;
            std::array<double,9> f;
            for (int k=0; k<9; ++k) f[k]=a[k][p-cx[k]-n*cy[k]];
            collide(f,b,p,omega,false,speed);
        }
    }
    for (int y=0; y<n; ++y) {
        const int stride=(y==0 || y==n-1) ? 1 : n-1;
        for (int x=0; x<n; x+=stride) {
            const auto f=incoming(a,n,x,y);
            const int p=y*n+x;
            if (y==n-1) collide(f,b,p,omega,true,speed);
            else for (int k=0; k<9; ++k) b[k][p]=f[opposite[k]];
        }
    }
}

