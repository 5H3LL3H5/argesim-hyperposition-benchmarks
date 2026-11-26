"""Bildsatz für Kapitel 5. Nur die Neuzeichnung benötigt Matplotlib."""
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base.parent/"beispiele"))
from ball import G, reference, simulate
from detektion import growth

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.2,
                     "axes.labelsize": 9.4, "axes.titlesize": 10.6,
                     "axes.titleweight": "bold", "legend.fontsize": 8.5,
                     "svg.fonttype": "none", "svg.hashsalt": "lehrbuch-kap5",
                     "lines.linewidth": 1.65, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#536670",
                     "text.color": "#1D3240", "axes.labelcolor": "#1D3240"})
blue, orange, gray, green = "#0072B2", "#A84012", "#536670", "#007567"
comma = FuncFormatter(lambda x, pos: f"{x:g}".replace(".", ",").replace("-", "−"))


def canvas(a_title, b_title):
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.85))
    fig.subplots_adjust(left=.095, right=.972, top=.87, bottom=.22, wspace=.40)
    for ax, title in zip(axes, (a_title, b_title)):
        ax.set_title(title, loc="left", pad=8)
        ax.grid(True, alpha=.18, linewidth=.65)
        ax.tick_params(labelsize=8.6)
        ax.xaxis.set_major_formatter(comma)
        ax.yaxis.set_major_formatter(comma)
    return fig, axes


def finish(fig, name):
    fig.savefig(base/(name+".svg"), metadata={"Date": None})
    plt.close(fig)


def detector():
    fig, (a,b) = canvas("A   Zwei Durchgänge und eine Berührung",
                        "B   Fehler des Schwellenzeitpunkts")
    ts = [i/200 for i in range(201)]
    a.axhline(0, color=gray, lw=.9)
    a.plot(ts, [(t-.25)*(t-.75) for t in ts], color=blue, label="zwei Durchgänge")
    a.plot(ts, [(t-.5)**2 for t in ts], "--", color=orange, label="Berührung")
    a.plot([0,1],[.1875,.1875],"o",color=blue,ms=4)
    a.plot([.25,.75],[0,0],"o",mfc="white",mec=blue,ms=6)
    a.plot(.5,0,"D",mfc="white",mec=orange,ms=5)
    a.set(xlabel="Zeit t [s]", ylabel="Wächterwert [1]",xticks=[0,.25,.5,.75,1],
          ylim=(-.09,.32),yticks=[-.05,0,.1,.2,.3])
    a.legend(loc="upper center",frameon=False,handlelength=1.8,ncol=1)
    hs = [.0625,.125,.25,.5]
    err = [abs(growth(h)-math.log(2)) for h in hs]
    bd = [math.e*h**4*((1+h/4)/120+1/384) for h in hs]
    b.loglog(hs,err,"o-",color=blue,label="gemessener Fehler")
    b.loglog(hs,bd,"s--",color=green,mfc="white",label="hergeleitete Schranke")
    b.set(xlabel="Schrittweite h [s]",ylabel="Zeitfehler [s]",ylim=(3e-8,8e-3))
    b.set_xticks(hs, ["0,0625","0,125","0,25","0,5"])
    b.minorticks_off()
    b.legend(loc="upper left",frameon=False,handlelength=1.6)
    finish(fig,"k5_detektion")


def common_clock():
    fig,(a,b) = canvas("A   Die Höhe bleibt stetig","B   Die Geschwindigkeit springt")
    for H, color, style, label in [(2,blue,"-","2,00 m"),(2.25,orange,"--","2,25 m")]:
        tau=math.sqrt(2*H/G)
        u=.85*G*tau
        before=[.55+(tau-.55)*k/70 for k in range(71)]
        after=[tau+(.88-tau)*k/70 for k in range(71)]
        a.plot(before,[H-G*t*t/2 for t in before],style,color=color,label=label)
        a.plot(after,[u*(t-tau)-G*(t-tau)**2/2 for t in after],style,color=color)
        a.plot(tau,0,"o",color=color,ms=4)
        b.plot(before,[-G*t for t in before],style,color=color)
        b.plot(after,[u-G*(t-tau) for t in after],style,color=color)
        b.plot([tau,tau],[-G*tau,u],":",color=color,lw=.95)
        b.plot(tau,-G*tau,"o",mfc="white",mec=color,ms=4)
        b.plot(tau,u,"o",mfc=color,mec=color,ms=4)
        for ax,y in [(a,u*(.8-tau)-G*(.8-tau)**2/2),(b,u-G*(.8-tau))]:
            ax.plot(.8,y,"D",color=color,ms=4)
    for ax in (a,b):
        ax.axvline(.8, color=gray,ls="-.",lw=.9,zorder=0)
        ax.set(xlabel="Laborzeit t [s]",xlim=(.55,.88),xticks=[.55,.6,.65,.7,.75,.8,.85])
    a.set(ylabel="Höhe q [m]",ylim=(-.06,1.18))
    b.set(ylabel="Geschwindigkeit v [m/s]",ylim=(-8,7.5))
    a.legend(loc="upper left",title="Starthöhe H",title_fontsize=8.2,frameon=False)
    finish(fig,"k5_saltation")


def zeno():
    fig,(a,b) = canvas("A   Fall und Rückflüge","B   Dauer der einzelnen Rückflüge")
    _, hits, rest=simulate(10,10)
    ts=[i/1000 for i in range(8011)]
    heights=[]
    k=0
    for t in ts:
        while k<len(hits) and hits[k][0]<=t:
            k+=1
        if t>=rest[0]:
            q=0
        elif k==0:
            q=2-G*t*t/2
        else:
            ti,_,u=hits[k-1]
            q=u*(t-ti)-G*(t-ti)**2/2
        heights.append(q)
    a.plot(ts,heights,color=blue)
    a.plot([row[0] for row in hits[:3]],[0]*3,"o",mec=orange,mfc="white",ms=5)
    limit=math.sqrt(4/G)*1.85/.15
    a.axvline(limit,ls="--",color=gray,lw=1.2)
    a.text(limit-.1,1.7,"Grenzzeit",ha="right",color=gray,fontsize=8.8)
    a.set(xlabel="Zeit t [s]",ylabel="Höhe q [m]",xlim=(-.1,8.1),ylim=(-.08,2.1))
    ks=list(range(1,len(hits)+1))
    b.semilogy(ks,[2*(-.85*reference(k)[1])/G for k in ks],"--",
               color=gray,label="geometrische Folge")
    sampled=range(1,len(hits),5)
    b.plot(list(sampled),[hits[k][0]-hits[k-1][0] for k in sampled],
           "o",mfc="white",mec=blue,label="protokollierte Flüge",ms=5)
    k=len(hits)
    b.plot(k,2*hits[-1][2]/G,"D",color=orange,label="erster ausgelassener Flug",ms=4)
    b.set(xlabel="Stoßnummer k [1]",ylabel="Flugzeit nach Stoß k [s]",ylim=(7e-5,5))
    b.legend(loc="upper right",frameon=False,fontsize=7.8,handlelength=1.6)
    finish(fig,"k5_zeno")


if __name__ == "__main__":
    detector()
    common_clock()
    zeno()
