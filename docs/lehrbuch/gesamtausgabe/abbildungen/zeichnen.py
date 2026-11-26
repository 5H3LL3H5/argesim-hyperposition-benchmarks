"""Bildsatz der sechs ergänzten Kapitel; Rechenlabor selbst benötigt nur Python."""
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter, NullLocator

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parent/'beispiele'))
from fourier_operator import string_run
from lbm_d2q9 import CX, CY, D2Q9, cavity
from linienmethode import heat, transport
from qss_devs import qss1
from rk_adaptiv import BS32, DP54, proposal, solve

blue,red,green,gray='#0072B2','#AA470E','#08735E','#50636C'
plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'teil1fa','font.size':9.5,
 'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#203342',
 'axes.titlesize':10.5,'axes.titleweight':'bold','legend.fontsize':8.0,'lines.linewidth':1.7})
comma=FuncFormatter(lambda x,pos:f'{x:g}'.replace('.',',').replace('-','−'))
def frame(a,b):
    fig,ax=plt.subplots(1,2,figsize=(8,3.6));fig.subplots_adjust(left=.095,right=.98,bottom=.19,top=.866,wspace=.39)
    for z,h in zip(ax,(a,b)):
        z.set_title(h,loc='left');z.grid(alpha=.17);z.xaxis.set_major_formatter(comma);z.yaxis.set_major_formatter(comma)
    return fig,*ax
def ready(fig,name):
    fig.savefig(root/(name+'.svg'),metadata={'Date':None});plt.close(fig)
def rk():
    fig,a,b=frame('A   Angenommene Schritte','B   Ein verschwindender Schätzwert')
    rhs=lambda t,y:(-y[0],)
    for pair,col,mark,name in ((BS32,blue,'o','BS3(2)'),(DP54,red,'s','DP5(4)')):
        rec,_=solve(rhs,(1.,),1.,.8,pair,(1e-9,),1e-6)
        a.plot([r[0] for r in rec],[r[1] for r in rec],mark+'-',ms=3,color=col,label=name)
    a.set(xlabel='Schrittbeginn t [s]',ylabel='Schrittweite h [s]');a.legend(frameon=False)
    hs=[j/100 for j in range(1,151)]
    val=[proposal(rhs,0.,(1.,),h,BS32) for h in hs]
    b.plot(hs,[abs(x[0][0]-x[1][0]) for x in val],color=blue,label='Paardifferenz')
    b.plot(hs,[abs(x[0][0]-math.exp(-h)) for h,x in zip(hs,val)],'--',color=red,label='wahrer lokaler Fehler')
    b.plot([1],[0],'o',mfc='white',mec=blue);b.set(xlabel='Schrittweite h [s]',ylabel='Betrag [1]');b.legend(frameon=False)
    ready(fig,'t1_rk')
def pendel():
    fig,a,b=frame('A   Tangente und nächster Ort','B   Phasenfehler nach einer Sekunde')
    th=[i*math.pi/180 for i in range(-12,76)]
    a.plot([math.cos(t) for t in th],[math.sin(t) for t in th],color=gray)
    a.plot([1,1],[0,.45],'--',color=red,label='freie Prognose')
    a.plot([1,math.sqrt(1-.45**2)],[.45,.45],'-',color=green,label='Ortskorrektur')
    for x,y,col,mark in [(1,0,blue,'o'),(1,.45,red,'s'),(math.sqrt(1-.45**2),.45,green,'D')]:a.plot(x,y,mark,color=col,ms=5)
    a.set(xlabel='Ort x [m]',ylabel='Ort y [m]',aspect='equal',xlim=(.2,1.18),ylim=(-.12,.95));a.legend(frameon=False,loc='lower left')
    hs=[1/n for n in (40,20,10,5)]
    b.loglog(hs,[(math.asin(h)-h)/h for h in hs],'o-',color=blue,label='RATTLE')
    b.loglog(hs,[h*h/6 for h in hs],'--',color=red,label='Leitterm bei ω = 1/s')
    b.set(xlabel='Schrittweite h [s]',ylabel='Phasenfehler [rad]');b.set_xticks(hs,['0,025','0,05','0,1','0,2']);b.legend(frameon=False)
    b.xaxis.set_minor_formatter(NullFormatter())
    ready(fig,'t1_dae')
def qss():
    fig,a,b=frame('A   Zustand und Meldung','B   Fehler und bewiesene Schranke')
    _,log,_=qss1(((-1.,),),(1.,),.125,2.)
    times=[0]+[r[0] for r in log]+[2.];qs=[1]+[r[2][0] for r in log];xs=[1]+[r[1][0] for r in log]
    xs.append(xs[-1]-(times[-1]-times[-2])*qs[-1]);a.plot(times,xs,color=blue,label='Zustand x')
    a.step(times,qs+[qs[-1]],where='post',ls='--',color=red,label='Meldung q')
    ts=[j/200 for j in range(401)];a.plot(ts,[math.exp(-t) for t in ts],':',color=gray,label='exakt')
    ii=0;err=[]
    for t in ts:
        while ii+1<len(times)-1 and times[ii+1]<=t:ii+=1
        err.append(abs(xs[ii]-(t-times[ii])*qs[ii]-math.exp(-t)))
    b.plot(ts,err,color=blue,label='Bahnfehler')
    b.plot(ts,[.125*(1-math.exp(-t)) for t in ts],'--',color=green,label='obere Schranke')
    a.set(xlabel='Zeit t [s]',ylabel='Speicherwert [1]');b.set(xlabel='Zeit t [s]',ylabel='Abweichung [1]')
    a.legend(frameon=False);b.legend(frameon=False);ready(fig,'t1_qss')
def raum():
    fig,a,b=frame('A   Fehler der Wärmeleitung','B   Eine Front nach einem Umlauf')
    ns=[8,16,32,64];res=[heat(n) for n in ns]
    a.loglog(ns,[abs(r[1]-r[2]) for r in res],'o-',color=blue,label='Raum allein')
    a.loglog(ns,[abs(r[0]-r[1]) for r in res],'s--',color=red,label='Zeit allein')
    a.set_xticks(ns,[str(n) for n in ns]);a.xaxis.set_minor_locator(NullLocator());a.set(xlabel='Anzahl Intervalle [1]',ylabel='Amplitudenfehler [1]');a.legend(frameon=False)
    init=[float(8<=j<20) for j in range(40)]
    b.step(range(40),init,where='mid',ls=':',color=gray,label='exakt')
    for flag,col,style,l in ((True,blue,'-','Minmod'),(False,red,'--','Upwind')):
        q=init.copy()
        for _ in range(80):q=transport(q,.5,flag)
        b.step(range(40),q,where='mid',ls=style,color=col,label=l)
    b.set(xlabel='Zellindex j [1]',ylabel='Zellmittel [1]',ylim=(-.1,1.25));b.legend(frameon=False,loc='upper right')
    ready(fig,'t1_mol')
def stern():
    fig,a,b=frame('A   D2Q9 im Geschwindigkeitsraum','B   Eingänge am Deckel')
    for i,(x,y) in enumerate(zip(CX,CY)):
        if i:
            a.annotate('',(x,y),(0,0),arrowprops={'arrowstyle':'-|>','color':blue if i<5 else green,'lw':1.8})
            a.text(1.13*x,1.13*y,str(i),ha='center',va='center')
    a.plot(0,0,'o',color=gray);a.text(.08,-.12,'0')
    a.set(xlabel='cᵢₓ / c [1]',ylabel='cᵢᵧ / c [1]',aspect='equal',xlim=(-1.4,1.4),ylim=(-1.4,1.4),xticks=[-1,0,1],yticks=[-1,0,1])
    b.set(xlabel='x / Δx [1]',ylabel='y / Δx [1]',xlim=(-1.55,1.55),ylim=(-1.15,1.45),aspect='equal',xticks=[-1,0,1],yticks=[-1,0,1])
    b.axhline(0,color=gray,lw=2);b.plot(0,0,'o',color=gray);b.text(-1.42,-.95,'Fluid')
    for i in (4,7,8):
        x,y=-CX[i],-CY[i]
        b.annotate('',(0,0),(x,y),arrowprops={'arrowstyle':'-|>','color':red,'lw':1.8})
        b.text(x,y+.13,str(i),ha='center')
    b.annotate('U',(.98,-.20),(.28,-.20),va='center',arrowprops={'arrowstyle':'->','color':blue},color=blue)
    ready(fig,'t1_stern')
def fluid():
    fig,a,b=frame('A   Kavität im Anlauf','B   Analytische Kontrolle im Kanal')
    box,hist=cavity();f=hist[500];n=box.nx
    ux=[[f[j*n+i][1]/.05 for i in range(n)] for j in range(box.ny)]
    uy=[[f[j*n+i][2]/.05 for i in range(n)] for j in range(box.ny)]
    a.grid(False);im=a.imshow(ux,extent=(0,1,-.5/n,1+.5/n),origin='lower',cmap='RdBu_r',vmin=-1,vmax=1,aspect='equal')
    xx=[(i+.5)/n for i in range(2,n,5)];yy=[j/n for j in range(2,box.ny,5)]
    a.quiver(xx,yy,[[ux[j][i] for i in range(2,n,5)] for j in range(2,box.ny,5)],[[uy[j][i] for i in range(2,n,5)] for j in range(2,box.ny,5)],color='#192F3C',scale=4,pivot='mid')
    c=fig.colorbar(im,ax=a,fraction=.048,pad=.045,format=comma,ticks=(-1,-.5,0,.5,1))
    c.ax.set_title('uₓ/U [1]',fontsize=8,fontweight='normal',pad=4)
    a.set(xlabel='x/L [1]',ylabel='y/L [1]',ylim=(0,1))
    N=8;ch=D2Q9(2,N+1,.8,.04,'zouhe',True)
    for _ in range(704): ch.step()
    b.plot([0,1],[0,1],'--',color=red,label='Couette-Profil')
    b.plot([j/N for j in range(N+1)],[ch.field()[2*j][1]/.04 for j in range(N+1)],'o',mfc='white',mec=blue,label='D2Q9')
    b.set(xlabel='relative Höhe y/H [1]',ylabel='uₓ/U [1]');b.legend(frameon=False)
    ready(fig,'t1_lbm')
def fno():
    fig,a,b=frame('A   Saite mit Knick bei t = 0,19 s','B   Auswertung mit festen Gewichten')
    _,_,res=string_run();n,_,_,y,z=res[-1];x=[j/n for j in range(n+1)]
    a.plot(x,z,color=gray,label='d’Alembert');a.plot(x,y,'--',color=blue,label='8 gelernte Moden')
    a.set(xlabel='Ort x [m]',ylabel='normierte Auslenkung [1]');a.legend(frameon=False)
    ns=[r[0]+1 for r in res];b.semilogy(ns,[r[1] for r in res],'o-',color=green,label='glattes Testfeld')
    b.semilogy(ns,[r[2] for r in res],'s--',color=red,label='Dreieck')
    b.set(xlabel='Anzahl Gitterpunkte [1]',ylabel='relativer Feldfehler [1]',ylim=(1e-17,1));b.set_xticks(ns);b.legend(frameon=False,loc='center right')
    ready(fig,'t1_fno')
if __name__=='__main__':
    rk();pendel();qss();raum();stern();fluid();fno()
