"""Abbildung 9.3. Modenphase im Rollout und Gitterkontrolle an der gezupften Saite."""
import math
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

here = Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"beispiele"))
from fno_physiklayer import (
    DT,
    SEEDS,
    SPEED,
    blind_run,
    kappa,
    oscillator_step,
    train_models,
)


def main():
    plt.rcParams.update({"font.size":9.1,"svg.fonttype":"none","svg.hashsalt":"physiklayer9",
                         "axes.spines.top":False,"axes.spines.right":False,"axes.labelcolor":"#203342",
                         "axes.titleweight":"bold","axes.titlesize":10.1})
    blue,green,orange,ink="#0072B2","#08735E","#AA470E","#253F4B"
    fig,(left,right)=plt.subplots(1,2,figsize=(8,3.6))
    fig.subplots_adjust(left=.092,right=.983,bottom=.215,top=.87,wspace=.36)
    omega=kappa(3)*SPEED
    t=[j*DT for j in range(33)]
    q,v=1.,0.
    saved=[q]
    for _ in t[1:]:
        q,v=oscillator_step(q,v,omega,DT)
        saved.append(q)
    left.axhline(0,color=ink,lw=.65,alpha=.4)
    left.plot(t,saved,color=blue,lw=1.7,label="Ort und Geschwindigkeit")
    left.plot(t,[math.cos(omega*DT)**j for j in range(33)],'--',color=orange,lw=1.7,
              label="Geschwindigkeit auf null")
    left.plot(t[-1],saved[-1],'o',color=blue,ms=4.3)
    left.plot(t[-1],math.cos(omega*DT)**32,'s',color=orange,ms=4.0)
    left.set(xlabel="Zeit t [s]",ylabel="Modenamplitude q₃/q₃(0) [1]",xlim=(0,.825),
             ylim=(-1.32,1.2),xticks=(0,.2,.4,.6,.8),yticks=(-1,-.5,0,.5,1))
    left.legend(frameon=False,fontsize=7.6,loc="center",bbox_to_anchor=(.50,-.27),ncol=1)
    left.set_title("A   Die dritte Saitenmode",loc="left")
    fmt=FuncFormatter(lambda x,pos:f"{x:g}".replace(".",",").replace("-","−"))
    left.xaxis.set_major_formatter(fmt);left.yaxis.set_major_formatter(fmt)
    trained=[train_models(seed) for seed in SEEDS]
    med=[]
    for n in (112,128,240):
        trials=[blind_run(model,n).triangle for model in trained]
        med.append([100*statistics.median(col) for col in zip(*trials)])
    for j,color,marker,style,label in ((1,blue,"o","-","FNO mit Physikterm"),
             (3,green,"D","--","Physik-Layer"),(4,orange,"s",":","Layer und FNO-Korrektur")):
        right.plot(range(3),[v[j] for v in med],marker=marker,ls=style,color=color,
                   lw=1.6,ms=4.5,label=label)
    right.set_yscale("log");right.set_yticks((.001,.01,.1,1));right.yaxis.set_major_formatter(fmt)
    right.set_xticks(range(3),["113 (3,5)","129 (4)","241 (7,5)"])
    right.set(xlabel="Gitterpunkte (Weg in Zellen)",ylabel="relativer Feldfehler [%]",
              xlim=(-.12,2.12),ylim=(.0009,1.8))
    right.legend(frameon=False,fontsize=7.2,loc="center",bbox_to_anchor=(.50,-.31),ncol=1)
    right.set_title("B   Dreieck nach 25 ms",loc="left")
    for ax in (left,right): ax.grid(axis="y",alpha=.2)
    fig.savefig(here/"t1_physiklayer.svg",bbox_inches="tight",pad_inches=.10,metadata={"Date":None})
    plt.close(fig)

if __name__=="__main__":
    main()
