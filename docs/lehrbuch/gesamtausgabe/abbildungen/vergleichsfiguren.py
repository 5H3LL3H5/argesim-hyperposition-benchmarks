"""Satzgrafiken für die Kapitel 10, 14 und 17. Labor und Datenprüfung brauchen nur Python."""
import csv
from collections import Counter
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt

out = Path(__file__).resolve().parent
mpl.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"svg.fonttype":"none",
                     "pdf.fonttype":42,"axes.spines.top":False,"axes.spines.right":False})
def save(fig, name):
    for fmt in ("svg","pdf"):
        fig.savefig(out / (name+"."+fmt), bbox_inches="tight", pad_inches=.10)
    plt.close(fig)

fig,ax=plt.subplots(figsize=(6.1,2.0),layout="constrained")
ax.barh(["Stoß 1","Stoß 2","Stoß 3"],[0,0,1.2],height=.5,color="#006d77")
ax.axvline(1,ls="--",color="#9c4100",label="Fehlerbudget")
ax.set(xlim=(-.04,1.37),xlabel="Zeitfehler / erlaubter Zeitfehler")
ax.scatter([0,0],[0,1],s=24,color="#006d77")
ax.invert_yaxis();ax.legend(loc="upper right",frameon=False)
save(fig,"pruefung_score")

fig,ax=plt.subplots(figsize=(6.1,2.1),layout="constrained")
ax.step([0,4,7,9],[0,-800,0,0],where="post",lw=2.3,color="#006d77",label="vorgegebener Puls")
ax.step([0,3,6,9],[0,0,-800,0],where="post",ls="--",lw=1.6,color="#ab4c0d",label="linker Wert, 3-s-Schritte")
ax.set(xlim=(0,9.05),ylim=(-900,180),xticks=[0,3,4,6,7,9],yticks=[-800,-400,0],xlabel="Zeit in s",ylabel="Lastkraft in N")
ax.legend(frameon=False,fontsize=9,loc="center left")
save(fig,"pruefung_puls")

with (out.parent/"daten/qss-extension.csv").open() as f: counts=Counter((r["case"],r["status"]) for r in csv.DictReader(f))
fig,ax=plt.subplots(figsize=(6.35,3.3),layout="constrained")
cases=sorted({c for c, _ in counts});left=[0]*len(cases)
for status,tag,color,hatch in (("pass","Bestanden","#006d77",""),("accuracy_miss","Budget überschritten","#e4ac5e",""),
                               ("timeout","Zeitlimit","#728fab","/"),("event_mismatch","Zahl abweichend","#c37670","xx"),
                               ("solver_error","Solverfehler","#4f4b55","..")):
    vals=[counts[c,status] for c in cases]
    ax.barh(cases,vals,left=left,label=tag,color=color,edgecolor="white",lw=.55,hatch=hatch)
    left=[a+b for a,b in zip(left,vals)]
assert left==[57]*8
ax.invert_yaxis();ax.set(xlim=(0,57),xlabel="Archivierte Konfigurationen je Modellfenster",xticks=[0,10,20,30,40,50,57])
ax.legend(frameon=False,fontsize=8,ncol=3,loc="upper center",bbox_to_anchor=(.5,-.22),columnspacing=.8)
save(fig,"pruefung_matrix")
