"""Reuse the archived D2Q9 collision and physical boundary equations in an MPI halo experiment."""
import sys
from pathlib import Path
from buchquellen import CAVITY_SOURCE, read_book_source

source = read_book_source(Path(sys.argv[1]), CAVITY_SOURCE / 'd2q9.cpp').decode('utf-8')
Path('d2q9_book.cpp').write_text(source)
kernel=source[source.index('constexpr double lid='):source.index('int main(')]
for old,new in [
    ('double *__restrict b,int n,int st','double *__restrict b,int,int st'),
    ('int y,double rate){','int y,double rate,int first_x,int end_x){'),
    ('for(int x=1;x<n-1;++x){','for(int x=first_x;x<end_x;++x){'),
    ('    edge(a,b,n,st,pl,y,0);edge(a,b,n,st,pl,y,n-1);','')]:
    if kernel.count(old) != 1:
        raise ValueError(f'D2Q9 source differs at kernel marker: {old!r}')
    kernel=kernel.replace(old,new)
Path('kernel_local.hpp').write_text(kernel)
