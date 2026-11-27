"""Drei Vektorabbildungen für Kapitel 3; nur der Bildsatz nutzt Matplotlib."""
import sys
from math import cos, exp, pi, sin
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "beispiele"))
from c05 import MODEN, phase, schaltfolge
from c05 import A as RATE
from folgeregler import integriert
from radau_iia import C, RadauLinear
from stabilitaet import rueckwaerts, trapez

NAVY, TEAL, RED, GRAY = "#19394D", "#006D67", "#A94322", "#607681"
GRID = "#D8E1E3"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9.5,
                     "axes.labelcolor":NAVY,"text.color":NAVY,
                     "xtick.color":NAVY,"ytick.color":NAVY,"axes.edgecolor":GRAY,
                     "axes.spines.top":False,"axes.spines.right":False,
                     "xtick.labelsize":8.6,"ytick.labelsize":8.6,
                     "svg.fonttype":"none","svg.hashsalt":"nst-kapitel-3"})

def layout(titel):
    fig, axes = plt.subplots(1,2,figsize=(7.1,3.25))
    fig.subplots_adjust(left=.085,right=.978,bottom=.30,top=.85,wspace=.35)
    for ax, title in zip(axes,titel):
        ax.set_title(title,loc="left",fontsize=11.5,fontweight="bold",pad=8)
        ax.grid(color=GRID,linewidth=.65); ax.set_axisbelow(True)
        ax.tick_params(length=3)
    return fig, axes

def legende(ax):
    ax.legend(loc="upper left",bbox_to_anchor=(-.02,-.29),borderaxespad=0,
              ncol=2,fontsize=8.25,handlelength=1.6,columnspacing=.85,
              frameon=False,labelspacing=.28)

def ausgabe(fig, name, desc):
    fig.savefig(HERE/(name+".svg"),facecolor="white",
                metadata={"Date":"2026-11-22","Title":name,
                          "Description":desc,"Creator":"Christian Stenzel"})
    if name == "k3_stabilitaet":
        fig.savefig(HERE/(name+".pdf"), facecolor="white",
                    metadata={"Title": name, "Author":"Christian Stenzel",
                              "CreationDate":None, "ModDate":None})
    plt.close(fig)

def stabilitaet():
    fig,(a,b)=layout(["A   Grenzen im z-Raum","B   Nach dem Schalten"])
    phi=[2*pi*j/360 for j in range(361)]
    a.axvspan(-2.6,0,color="#EBF2F1",zorder=0)
    a.plot([-1+cos(t) for t in phi],[sin(t) for t in phi],
           color=RED,ls="--",lw=1.8,label="Vorwärts-Euler")
    a.plot([1+cos(t) for t in phi],[sin(t) for t in phi],
           color=TEAL,lw=1.9,label="Rückwärts-Euler")
    a.axvline(0,color=NAVY,lw=1,ls=":")
    # The closed real segment is stable; only its interior is strictly damped.
    a.plot([-2,0],[0,0],color=RED,lw=2.8,solid_capstyle="butt",zorder=5)
    a.scatter([-2,0],[0,0],color=RED,s=14,zorder=6)
    a.scatter([-1],[0],facecolor="white",edgecolor=RED,s=23,zorder=7)
    a.annotate("R(−1) = 0",xy=(-1,0),xytext=(0,11),
               textcoords="offset points",ha="center",color=RED,fontsize=8.0)

    a.set(xlim=(-2.35,2.35),ylim=(-1.35,1.35),aspect="equal",
          xlabel="Re(z) [1]",ylabel="Im(z) [1]",xticks=[-2,-1,0,1,2],
          yticks=[-1,0,1])
    legende(a)
    n=list(range(6))
    b.plot(n,[exp(-100*j) for j in n],color=NAVY,lw=1.6,label="Exakt")
    b.plot(n,[rueckwaerts(-100)**j for j in n],":s",color=TEAL,
           markerfacecolor="white",ms=4.0,label="Rückwärts-Euler")
    b.plot(n,[trapez(-100)**j for j in n],"--o",color=RED,ms=4,label="Trapez")
    b.set(xlabel="Schritt n [1]",ylabel="dₙ/d₀ [1]",xlim=(-.1,5.14),
          xticks=n,ylim=(-1.1,1.17),yticks=[-1,0,1])
    legende(b)
    ausgabe(fig,"k3_stabilitaet","Links zwei Euler-Grenzkreise, das reelle Vorwärts-Euler-Intervall [−2,0] und die Verstärkungsnullstelle −1. Rechts Gitterwerte für z=-100.")

def kollokation():
    fig,(a,b)=layout(["A   Temperaturüberschuss","B   Defekt der Kurve"])
    y=RadauLinear().stufen(0.,1.,.01,-1000.,lambda t:0.)
    theta=[j/480 for j in range(481)]
    kurve=[1-10*sum(w*v for w,v in zip(integriert(s),y)) for s in theta]
    def lagrange(s,j):
        v=[c for k,c in enumerate(C) if k!=j]; p,q=v
        return (s-p)*(s-q)/((C[j]-p)*(C[j]-q))
    defekt=[10*(p-sum(lagrange(s,j)*y[j] for j in range(3)))
            for s,p in zip(theta,kurve)]
    t=[10*s for s in theta]; tk=[10*c for c in C]
    a.plot(t,[exp(-10*s) for s in theta],color=NAVY,lw=1.8,label="Exakt")
    a.plot(t,kurve,color=TEAL,lw=1.9,ls="--",label="Kollokation")
    a.scatter(tk,y,facecolor="white",edgecolor=RED,zorder=4,s=27,label="Stufen")
    a.axhline(0,color=GRAY,lw=.7)
    a.set(ylabel="d/d₀ [1]",ylim=(-.24,1.12),yticks=[-.2,0,.5,1])
    b.axhline(0,lw=.8,color=GRAY)
    b.plot(t,defekt,color=RED,lw=1.8,label="Defekt")
    b.scatter(tk,[0]*3,facecolor="white",edgecolor=RED,zorder=5,s=27,
              label="Stufen")
    b.set(ylabel="dp/dθ + 10 p [1]")
    for ax in (a,b):
        ax.set(xlabel="Zeit seit Schrittbeginn [ms]",xlim=(-.2,10.35),
               xticks=[0,2,4,6,8,10]);legende(ax)
    ausgabe(fig,"k3_kollokation","Die Temperaturkurve am groben Radau-Schritt hat eine negative zweite Stufe. Ihr Defekt verschwindet an allen drei Radau-Knoten.")

def c05_plot():
    fig,(a,b)=layout(["A   Drei Schaltungen","B   Erste Mikrosekunden"])
    folge,_=schaltfolge()
    start=(4.2,.3); beginn=0.; m=0
    for j,ende in enumerate([t for t,_ in folge]+[3.5]):
        c2,c4,_,_=MODEN[m]; d=ende-beginn
        ts=[d*i/450 for i in range(451)]
        werte=[phase(dt,start,c2,c4) for dt in ts]; start=werte[-1]
        a.plot([beginn+t for t in ts],[y[0] for y in werte],color=TEAL,lw=1.55,
               label="Zustand y₁" if j==0 else None)
        a.plot([beginn+t for t in ts],[y[1] for y in werte],color=NAVY,lw=1.4,
               ls="--",label="Zustand y₂" if j==0 else None)
        if j<len(folge):
            a.plot(ende,start[0],marker="^" if folge[j][1]>0 else "v",
                   color=RED,ms=6,markerfacecolor="white",zorder=5)
        beginn=ende; m=1-m
    for y0 in (2.5,5.8):a.axhline(y0,ls=":",lw=.8,color=GRAY)
    a.set(xlabel="Zeit t [s]",ylabel="Projektzustand [1]",xlim=(-.04,3.54),
          ylim=(0,6.25),xticks=[0,1,2,3],yticks=[0,2.5,5.8])
    us=[2.5*j/300 for j in range(301)]
    werte=[phase(t*1e-6,(4.2,.3),.4,5.5) for t in us]
    b.plot(us,[y[0] for y in werte],color=TEAL,lw=1.9,label="Zustand y₁")
    b.plot(us,[y[1] for y in werte],color=NAVY,lw=1.5,ls="--",label="Zustand y₂")
    b.axvline(1e6/RATE,ls=":",color=GRAY,lw=1)
    b.annotate("1/a",xy=(1e6/RATE,3.8),xytext=(7,0),
               textcoords="offset points",fontsize=8.4)
    b.set(xlabel="Zeit t [µs]",ylabel="Projektzustand [1]",xlim=(-.04,2.55),
          ylim=(0,4.5),xticks=[0,.5,1,1.5,2,2.5],yticks=[0,1,2,3,4])
    for ax in (a,b):legende(ax)
    ausgabe(fig,"k3_c05","C05 im kurzen Projektfenster und die schnelle erste Relaxation. Dreiecke markieren gerichtete Schwellenübertritte.")

if __name__=="__main__":
    stabilitaet()
    kollokation()
    c05_plot()
