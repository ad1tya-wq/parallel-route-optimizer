#!/usr/bin/env python3
"""Figures for the Review-2 extensions (E7 sync cost, E8 epoch/quality, E9 2-opt, E10 DTAM)."""
import csv
from collections import defaultdict
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
R, F = ROOT/"results", ROOT/"results"/"figures"
F.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi":130,"savefig.dpi":130,"font.size":9,"axes.grid":True,
                     "grid.alpha":.25,"axes.spines.top":False,"axes.spines.right":False,
                     "figure.autolayout":True})
FIX,DTAM,GREY,ACC = "#2563eb","#dc2626","#6b7280","#f2a541"
def load(p):
    return list(csv.DictReader(open(R/p))) if (R/p).exists() else []
def med(x):
    x=sorted(x); n=len(x); return x[n//2] if n%2 else .5*(x[n//2-1]+x[n//2])

# ---- Fig: the epoch-length trade-off (E7 speed vs E8 quality) ----------------
e7,e8=load("study_E7.csv"),load("study_E8.csv")
if e7 and e8:
    fig,ax=plt.subplots(1,2,figsize=(9.4,3.5))
    d=defaultdict(list)
    for r in e7: d[(int(r["threads"]),int(r["epoch_len"]))].append(float(r["t_min"]))
    m={k:min(v) for k,v in d.items()}; Es=sorted({k[1] for k in m})
    for T,c in ((1,GREY),(4,FIX),(8,DTAM)):
        ys=[m[(T,E)] for E in Es if (T,E) in m]
        if ys: ax[0].plot(Es[:len(ys)],ys,"-o",color=c,ms=4,label=f"{T} thread{'s' if T>1 else ''}")
    ax[0].set_xscale("log"); ax[0].set_xlabel("epoch length (generations between syncs)")
    ax[0].set_ylabel("wall-clock (s), identical total work")
    ax[0].set_title("E7: longer epochs are much faster", fontsize=9.5); ax[0].legend(fontsize=7)
    Es8=sorted({int(r["epoch_len"]) for r in e8})
    for land,t,c,ls in (("uniform500","0",FIX,"-"),("clustered600","0",DTAM,"-"),
                        ("uniform500","1",FIX,"--"),("clustered600","1",DTAM,"--")):
        ys=[med([float(r["best_len"]) for r in e8 if r["landscape"]==land and r["twoopt"]==t
                 and r["mode"]=="island-fixed" and int(r["epoch_len"])==E]) for E in Es8]
        if ys and ys[0]>0:
            ax[1].plot(Es8,[100*(y/ys[0]-1) for y in ys],ls,color=c,marker="o",ms=3.5,
                       label=f"{land}, 2-opt {'on' if t=='1' else 'off'}")
    ax[1].axhline(0,color="k",lw=.8,alpha=.4)
    ax[1].set_xscale("log"); ax[1].set_xlabel("epoch length")
    ax[1].set_ylabel("tour length vs epoch=5 (%)\nlower is better")
    ax[1].set_title("E8: ...but quality gets worse", fontsize=9.5); ax[1].legend(fontsize=6.6)
    fig.savefig(F/"i5_epoch_tradeoff.png"); plt.close(fig); print("-> i5_epoch_tradeoff.png")

# ---- Fig: E9 fast 2-opt + E10 DTAM factorial --------------------------------
ext=load("study_E9_E10.csv")
if ext:
    e9=[r for r in ext if r.get("exp")=="E9"]
    lands=["uniform500","clustered600","kroA200","a280"]
    fig,ax=plt.subplots(1,2,figsize=(9.6,3.6))
    x=np.arange(len(lands)); w=.35
    for i,(v,c) in enumerate((("naive",GREY),("fast",FIX))):
        vals=[]
        for land in lands:
            base=med([float(r["best_len"]) for r in e9 if r["landscape"]==land
                      and r["variant"]=="naive" and r["mode"]=="island-fixed"])
            cur=med([float(r["best_len"]) for r in e9 if r["landscape"]==land
                     and r["variant"]==v and r["mode"]=="island-fixed"])
            vals.append(100*(cur-base)/base if base else 0)
        ax[0].bar(x+(i-.5)*w,vals,w,color=c,label=f"{v} 2-opt")
    ax[0].axhline(0,color="k",lw=.8); ax[0].set_xticks(x); ax[0].set_xticklabels(lands,fontsize=7.5)
    ax[0].set_ylabel("tour length vs naive (%)\nlower is better")
    ax[0].set_title("E9: candidate-list 2-opt, equal 3s budget",fontsize=9.5); ax[0].legend(fontsize=7)
    gg=[]
    for land in lands:
        n_=med([float(r["generations"]) for r in e9 if r["landscape"]==land and r["variant"]=="naive"])
        f_=med([float(r["generations"]) for r in e9 if r["landscape"]==land and r["variant"]=="fast"])
        gg.append(f_/n_ if n_ else 0)
    ax[1].bar(x,gg,.5,color=ACC)
    ax[1].set_xticks(x); ax[1].set_xticklabels(lands,fontsize=7.5)
    ax[1].set_ylabel("generations completed, fast / naive")
    ax[1].set_title("E9: throughput gain",fontsize=9.5)
    for i,v in enumerate(gg): ax[1].text(i,v,f"{v:.0f}x",ha="center",va="bottom",fontsize=8)
    fig.savefig(F/"i5_fast_twoopt.png"); plt.close(fig); print("-> i5_fast_twoopt.png")

    e10=[r for r in ext if r.get("exp")=="E10"]
    cfgs=["stock","heterogeneous","immigrants","het+immigrants","rel-trigger","het+rel"]
    fig,ax=plt.subplots(1,2,figsize=(9.8,3.7))
    for a,(land,t) in zip(ax,(("uniform500","0"),("clustered600","0"))):
        ref=med([float(r["best_len"]) for r in e10 if r["landscape"]==land
                 and r["twoopt"]==t and r["config"]=="FIXED-ref"])
        vals,dons=[],[]
        for c in cfgs:
            rs=[r for r in e10 if r["landscape"]==land and r["twoopt"]==t and r["config"]==c]
            vals.append(100*(med([float(r["best_len"]) for r in rs])-ref)/ref if rs else 0)
            df=sum(int(r["donor_found"]) for r in rs); fb=sum(int(r["donor_fallback"]) for r in rs)
            dons.append(100*df/(df+fb) if df+fb else 0)
        bars=a.bar(range(len(cfgs)),vals,.6,
                   color=[DTAM if v>0 else "#1e7a5a" for v in vals])
        a.axhline(0,color="k",lw=1)
        a.set_xticks(range(len(cfgs)))
        a.set_xticklabels(cfgs,rotation=32,ha="right",fontsize=7)
        a.set_ylabel("tour length vs fixed migration (%)")
        a.set_title(f"E10: {land}, no local search",fontsize=9.5)
        for i,(v,d) in enumerate(zip(vals,dons)):
            a.text(i,v,f" donor {d:.0f}%",ha="center",
                   va="bottom" if v>=0 else "top",fontsize=6.2,color=GREY)
    fig.text(.5,.005,"Bars above zero = worse than the fixed-migration baseline. "
             "'donor %' = share of DTAM migrations that found a genuinely non-stagnating source.",
             ha="center",fontsize=6.8,color=GREY)
    fig.savefig(F/"i5_dtam_factorial.png"); plt.close(fig); print("-> i5_dtam_factorial.png")
