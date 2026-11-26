"""Abb. 9.2 aus den gleichen Fits und Blindversuchen wie im Rechenlabor erzeugen."""
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

here = Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"beispiele"))
from fno_physik import (
    ACC_NOISE,
    SEEDS,
    SPEED,
    K,
    calibration,
    fit_acceleration,
    mean_step_error,
    train_variants,
)


def main():
    plt.rcParams.update({"font.size":9.2,"svg.fonttype":"none","svg.hashsalt":"cp2-physik-lernen",
                         "axes.spines.top":False,"axes.spines.right":False,
                         "axes.labelcolor":"#203342","axes.titleweight":"bold","axes.titlesize":10.1})
    blue,green,red,ink = "#0072B2","#08735E","#AA470E","#283F4D"
    fig,(ax,bx) = plt.subplots(1,2,figsize=(8,3.6))
    fig.subplots_adjust(left=.098,right=.985,top=.85,bottom=.20,wspace=.37)
    fit0 = fit_acceleration(calibration(SEEDS[0],SPEED,ACC_NOISE),ACC_NOISE)
    convert = lambda v:100*(math.sqrt(v)/SPEED-1)
    ax.axhline(0,lw=1,color=ink,ls=":",label="Sollwert")
    ax.plot(range(1,K+1),[convert(v) for v in fit0.independent],color=blue,marker="o",
            ms=3.8,lw=1.3,label="ein Wert je Mode")
    ax.axhline(convert(fit0.shared),ls="--",lw=1.8,color=green,label="gemeinsamer Wert")
    ax.set(xlabel="Modenindex k",ylabel="Abweichung von c [%]",xticks=[1,4,8,12,16],
           xlim=(.5,16.5))
    ax.set_title("A   Welche Geschwindigkeit lernt die Mode?",loc="left")
    ax.legend(frameon=False,fontsize=7.8,loc="best")
    ax.grid(axis="y",alpha=.22)
    med=[]
    for seed in SEEDS:
        fit = fit_acceleration(calibration(seed,SPEED,ACC_NOISE),ACC_NOISE)
        values=[100*mean_step_error(p,128) for p in train_variants(fit,seed)]
        med.append(values)
        bx.plot([0,1,2],values,color="#788A91",alpha=.59,lw=.85,zorder=1)
        for x,(v,c,m) in enumerate(zip(values,(blue,green,red),("o","D","s"))):
            bx.plot(x,v,marker=m,ms=4.7,markeredgecolor="white",markeredgewidth=.45,color=c,zorder=2)
    import statistics
    for j in range(3):
        v=statistics.median(row[j] for row in med)
        bx.plot([j-.13,j+.13],[v,v],lw=2.3,color=ink,zorder=3)
    bx.set_yscale("log")
    bx.set_xticks([0,1,2],["Daten","PDE mit ĉ","PDE mit 2ĉ"])
    bx.set_yticks([.1,.3,1,3,10])
    fmt=FuncFormatter(lambda x,pos:f"{x:g}".replace(".",",").replace("-","−"))
    ax.yaxis.set_major_formatter(fmt);bx.yaxis.set_major_formatter(fmt)
    bx.set(ylim=(.078,16),xlim=(-.24,2.24),ylabel="relativer Feldfehler [%]")
    bx.set_title("B   Feldfehler auf sechs Testprofilen",loc="left")
    bx.grid(axis="y",which="major",alpha=.22);bx.tick_params(axis="x",labelsize=8)
    fig.savefig(here/"t1_fno_physik.svg",metadata={"Date":None})
    plt.close(fig)

if __name__=="__main__":
    main()
