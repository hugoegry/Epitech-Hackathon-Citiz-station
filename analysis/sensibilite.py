import json, itertools, numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import shape
T="data/lakehouse/Tables/"
rd=lambda n: pd.read_parquet(T+n+".parquet")
gold=rd("gold_iris"); couts=rd("gold_couts"); villes_vls=set(rd("bronze_velo").ville)
off=rd("gold_suggestions")
def select(g,wc=.5,we=.5,budget=500000):
    base=g[g.pop_2021>=200]; cand=[]
    for t in couts.itertuples():
        c=base[base[f"gain_ind_{t.type}"]>0].copy()
        if t.type=="velo": c=c[c.ville.isin(villes_vls)&(c.densite_2021>=7000)]
        c["type"],c["cout_eur"]=t.type,t.cout_horizon_eur
        c["gain_pop_2030"]=(c[f"gain_ind_{t.type}"]/c.ind_carreaux*c.pop_2030_proj).round()
        cand.append(c)
    cand=pd.concat(cand)
    cand["score"]=cand.gain_pop_2030*(1+wc*cand.rang_motorisation.fillna(0)+we*cand.equite)
    cand["spk"]=cand.score/cand.cout_eur*1000
    cand=cand.sort_values("spk",ascending=False)
    best=cand[~cand.duplicated("code_iris")].copy()
    best["cum"]=best.groupby("ville").cout_eur.cumsum()
    best["rang"]=best.groupby("ville").cumcount()+1
    return best[best.cum<=budget]
def summ(s):
    return dict(sites=len(s),citiz=int((s.type=="citiz").sum()),bus=int((s.type=="arret_bus").sum()),velo=int((s.type=="velo").sum()),cout=round(s.cout_eur.sum(),2),hab=int(s.gain_pop_2030.sum()),eur_hab=round(s.cout_eur.sum()/s.gain_pop_2030.sum(),2))
B=select(gold)
o=off[off.recommande]
print("CHECK baseline vs official:",summ(B),"| official",len(o),round(o.cout_eur.sum(),2),o.gain_pop_2030.sum(), "same set:",set(zip(B.code_iris,B.type))==set(zip(o.code_iris,o.type)))
key=lambda s:set(s.code_iris)
def comp(V,label,rows):
    r={"variante":label,"n_sites":len(V),"global":len(key(B)&key(V))/len(B)}
    for v,g in B.groupby("ville"):
        r[v]=len(key(g)&key(V[V.ville==v]))/len(g)
    t5=B[B.rang<=5]; r["top5_kept"]=len(key(t5)&key(V))/len(t5)
    rows.append(r)
rows=[]
for wc,we in itertools.product([0,.25,.5,.75,1],repeat=2):
    if (wc,we)!=(.5,.5): comp(select(gold,wc,we),f"wc={wc} we={we}",rows)
W=pd.DataFrame(rows); pd.set_option("display.width",250)
print(W.round(3).to_string()); print("weights: global min",W["global"].min(),"median",W["global"].median(),"top5 min",W.top5_kept.min(),"median",W.top5_kept.median())
W.to_csv("analysis/sensibilite_poids.csv",index=False)
iris=rd("bronze_iris_geo"); iris=gpd.GeoDataFrame(iris,geometry=iris.geometry_json.apply(lambda g:shape(json.loads(g))),crs=4326).to_crs(2154)
car0=rd("bronze_carreaux"); car0=gpd.GeoDataFrame(car0,geometry=gpd.points_from_xy(car0.x,car0.y),crs=3035).to_crs(2154)
car0=gpd.sjoin(car0,iris[["code_iris","geometry"]],predicate="within").drop(columns="index_right")
def gains(R):
    out={}
    for table,lat,lon,nom in [("bronze_stops","stop_lat","stop_lon","arret_bus"),("bronze_citiz","lat","lon","citiz"),("bronze_velo","lat","lon","velo")]:
        car=car0.copy(); pts=rd(table); pts=gpd.GeoDataFrame(pts,geometry=gpd.points_from_xy(pts[lon],pts[lat]),crs=4326).to_crs(2154)[["geometry"]]
        d="d"; car[d]=gpd.sjoin_nearest(car[["geometry"]],pts,distance_col=d).groupby(level=0)[d].min()
        nc=car[car[d]>R]
        p=gpd.sjoin(nc[["code_iris","geometry"]].set_geometry(nc.buffer(R)),nc[["code_iris","ind","geometry"]],predicate="contains")
        gain=p[p.code_iris_left==p.code_iris_right].groupby(level=0).ind.sum()
        b=nc.assign(gain=gain).sort_values("gain").groupby("code_iris").tail(1)
        out[f"gain_ind_{nom}"]=b.set_index("code_iris").gain
    return pd.DataFrame(out)
rows2=[]
for R in [300,350,500]:
    g=gold.drop(columns=[c for c in gold if c.startswith("gain_ind_")]).merge(gains(R),left_on="code_iris",right_index=True,how="left").fillna({"gain_ind_arret_bus":0,"gain_ind_citiz":0,"gain_ind_velo":0})
    V=select(g); comp(V,f"R={R}",rows2); print(R,summ(V))
D=pd.DataFrame(rows2); print(D.round(3).to_string()); D.to_csv("analysis/sensibilite_distance.csv",index=False)
for bud in [250000,500000,1000000]:
    s=select(gold,budget=bud); print("BUDGET",bud,"ALL",summ(s))
    for v,g in s.groupby("ville"): print("   ",v,summ(g))
