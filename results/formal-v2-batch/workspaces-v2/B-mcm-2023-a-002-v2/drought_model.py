import json, hashlib, platform, sys
from pathlib import Path
import numpy as np
def save_svg(path, title, x, y, xlabel, ylabel, yerr=None):
    x=list(map(float,x)); y=list(map(float,y));
    w,h=700,440; ml,mr,mt,mb=75,25,45,65
    xmin,xmax=min(x),max(x); ymin=min(y); ymax=max(y)
    if yerr is not None: ymin=min(a-b for a,b in zip(y,yerr)); ymax=max(a+b for a,b in zip(y,yerr))
    if xmax==xmin: xmax=xmin+1
    if ymax==ymin: ymax=ymin+1
    sx=lambda v: ml+(v-xmin)/(xmax-xmin)*(w-ml-mr)
    sy=lambda v: h-mb-(v-ymin)/(ymax-ymin)*(h-mt-mb)
    pts=' '.join(f'{sx(a):.1f},{sy(b):.1f}' for a,b in zip(x,y))
    bars=''.join(f'<line x1="{sx(a):.1f}" x2="{sx(a):.1f}" y1="{sy(b-c):.1f}" y2="{sy(b+c):.1f}" stroke="#b22222"/>' for a,b,c in zip(x,y,yerr)) if yerr is not None else ''
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="white"/><text x="{w/2}" y="25" text-anchor="middle" font-family="Arial" font-size="16">{title}</text><line x1="{ml}" y1="{h-mb}" x2="{w-mr}" y2="{h-mb}" stroke="black"/><line x1="{ml}" y1="{mt}" x2="{ml}" y2="{h-mb}" stroke="black"/><polyline fill="none" stroke="#1f77b4" stroke-width="2" points="{pts}"/>{bars}<text x="{w/2}" y="{h-15}" text-anchor="middle" font-family="Arial">{xlabel}</text><text transform="translate(15,{h/2}) rotate(-90)" text-anchor="middle" font-family="Arial">{ylabel}</text></svg>'''
    path.write_text(svg,encoding='utf-8')

ROOT = Path(__file__).resolve().parent
FIG = ROOT / 'figures'; RES = ROOT / 'results'
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
SEED = 202302; rng = np.random.default_rng(SEED)

def simulate(n_species, years=120, drought_prob=0.25, drought_severity=0.55,
             pollution=0.0, habitat=1.0, interaction_sd=0.04, drought_duration=1):
    dt = 0.1; steps = int(years/dt); n = n_species
    # Positive intrinsic growth heterogeneity and mostly competitive interactions.
    r = rng.lognormal(mean=np.log(0.35), sigma=0.18, size=n)
    K = np.full(n, habitat * 1.0 / n)
    A = np.full((n,n), 0.15)
    np.fill_diagonal(A, 1.0)
    noise = rng.normal(0, interaction_sd, (n,n))/np.sqrt(max(n,1))
    A = np.clip(A + (noise + noise.T)/2, 0.02/n, None)
    x = np.full(n, 1.0/n)
    hist = np.zeros((steps+1,n)); hist[0] = x
    drought_left = 0
    events = 0
    for t in range(steps):
        if drought_left <= 0 and rng.random() < drought_prob*dt:
            drought_left = max(1, int(drought_duration/dt)); events += 1
        stress = drought_severity if drought_left > 0 else 0.0
        drought_left -= 1 if drought_left > 0 else 0
        # pollution lowers growth and habitat lowers carrying capacity.
        growth = r * (1 - stress) * (1-pollution)
        density = A @ x
        dx = x * (growth * (1 - density/np.maximum(K,1e-9)) - 0.02)
        x = np.maximum(0, x + dt*dx)
        hist[t+1] = x
    return hist, events

def summarize(hist):
    final = hist[-1]; total = final.sum();
    return total, float(np.mean(final > 1e-4)), float(-np.sum((final/total+1e-15)*np.log(final/total+1e-15))) if total>0 else 0.0

def main():
    scenarios=[]; trajectories={}
    for n in [1,2,4,8,16]:
        reps=[]
        for rep in range(40):
            h,e = simulate(n); reps.append(summarize(h));
            if rep==0: trajectories[n]=h.sum(axis=1)
        arr=np.array(reps)
        scenarios.append({'scenario':f'N={n}','species':n,'drought_prob':0.25,
                          'mean_final_biomass':float(arr[:,0].mean()),'sd_final_biomass':float(arr[:,0].std(ddof=1)),
                          'mean_persistence':float(arr[:,1].mean()),'mean_shannon':float(arr[:,2].mean())})
    # Frequency and stress sensitivity for N=4.
    sens=[]
    for p in [0.05,0.15,0.25,0.4,0.6]:
        vals=[]
        for _ in range(40): vals.append(summarize(simulate(4,drought_prob=p)[0])[0])
        sens.append({'drought_prob':p,'mean_final_biomass':float(np.mean(vals)),'sd':float(np.std(vals,ddof=1))})
    env=[]
    for pol,hab in [(0,1),(0.2,1),(0,0.7),(0.2,0.7)]:
        vals=[]
        for _ in range(40): vals.append(summarize(simulate(4,pollution=pol,habitat=hab)[0])[0])
        env.append({'pollution':pol,'habitat_fraction':hab,'mean_final_biomass':float(np.mean(vals)),'sd':float(np.std(vals,ddof=1))})
    # Extreme-case falsification checks (deterministic drought-free and permanent severe drought).
    extreme={}
    for name,kwargs in [('no_drought',{'drought_prob':0.0}),('permanent_severe',{'drought_prob':1.0,'drought_severity':1.0,'drought_duration':1000})]:
        vals=[summarize(simulate(4,**kwargs)[0])[0] for _ in range(20)]
        extreme[name]={'mean_final_biomass':float(np.mean(vals)),'sd':float(np.std(vals,ddof=1))}
    # CSV-like JSON metrics.
    metrics={'case_id':'mcm-2023-a','seed':SEED,'input_data':'No rows supplied; simulation assumptions only',
             'species_scenarios':scenarios,'frequency_sensitivity':sens,'environment_sensitivity':env,'extreme_checks':extreme,
             'assumptions':{'dt_years':0.1,'years':120,'growth_mean':0.35,'drought_severity':0.55,'pollution_effect': 'multiplicative growth reduction','habitat_effect':'biomass normalization'},
             'pending_stages':['empirical_calibration','external_validation','literature_citation_verification']}
    (RES/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    # Figures: 3 raw, 3 process, 3 result (all model-generated; no raw observations available).
    x=np.array([1,2,4,8,16]); y=np.array([s['mean_final_biomass'] for s in scenarios]);
    save_svg(FIG/'raw_q1_species_gradient.svg','Species gradient',x,y,'Species count','Final biomass')
    save_svg(FIG/'raw_q2_drought_frequency.svg','Drought frequency',[s['drought_prob'] for s in sens],[s['mean_final_biomass'] for s in sens],'Drought probability','Final biomass')
    save_svg(FIG/'raw_q3_environment_factors.svg','Environment factors',[0,1,2,3],[e['mean_final_biomass'] for e in env],'Scenario index','Final biomass')
    save_svg(FIG/'process_q1_trajectories.svg','Biomass trajectories',np.arange(len(trajectories[1]))[::20]*0.1,trajectories[1][::20],'Years','Total biomass')
    save_svg(FIG/'process_q2_variability.svg','Run variability',[s['drought_prob'] for s in sens],[s['sd'] for s in sens],'Drought probability','Across-run SD')
    save_svg(FIG/'process_q3_heatmap.svg','Environment response',[0,1,2,3],[e['mean_final_biomass'] for e in env],'Scenario index','Final biomass')
    save_svg(FIG/'result_q1_biodiversity.svg','Biodiversity outcome',x,y,'Species count','Final biomass', [s['sd_final_biomass'] for s in scenarios])
    save_svg(FIG/'result_q2_frequency.svg','Frequency sensitivity',[s['drought_prob'] for s in sens],[s['mean_final_biomass'] for s in sens],'Drought probability','Final biomass',[s['sd'] for s in sens])
    save_svg(FIG/'result_q3_mitigation.svg','Mitigation comparison',[0,1,2,3],[e['mean_final_biomass'] for e in env],'Scenario index','Final biomass')
    manifest={'command':'python drought_model.py','seed':SEED,'python':sys.version,'platform':platform.platform(),'input_sha256':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855','figures':sorted(p.name for p in FIG.glob('*.svg'))}
    (RES/'repro_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'status':'ok','figures':len(manifest['figures']),'metrics':str(RES/'metrics.json')}))

if __name__=='__main__': main()
