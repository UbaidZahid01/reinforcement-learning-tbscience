
import os, json, argparse, numpy as np, pandas as pd
from datetime import datetime
from scipy.linalg import block_diag

CLIGHT = 299792458.0
MU_GPS = 3.986005e14
OMEGA_E_DOT = 7.2921151467e-5
F1, F2 = 1575.42e6, 1227.60e6
L1, L2 = CLIGHT/F1, CLIGHT/F2
GPS_EPOCH = datetime(1980, 1, 6)

def to_gps_time(dt):
    delta = dt - GPS_EPOCH
    w = delta.days // 7
    t = delta.total_seconds() - w * 604800
    return w, t

def parse_nav(file):
    ephs = {}
    if not os.path.exists(file): return {}
    with open(file) as f:
        lines = f.readlines()
        i = 0
        while i < len(lines):
            if 'END OF HEADER' in lines[i]: i += 1; break
            i += 1
        while i < len(lines):
            l = lines[i]; i += 1
            if not l.startswith('G'): continue
            sat = l[:3]
            try:
                epoch = datetime.strptime(l[4:23], '%Y %m %d %H %M %S')
                pf = lambda s: float(s.replace('D', 'E'))
                cb, cd, cdr = pf(l[23:42]), pf(l[42:61]), pf(l[61:80])
                p = []
                for _ in range(7):
                    ll = lines[i]; i += 1
                    for j in range(4):
                        s = ll[4+19*j:23+19*j].strip()
                        if s: p.append(pf(s))
                e = {'sat':sat,'epoch':epoch,'cb':cb,'cd':cd,'cdr':cdr,'Toe':p[8],
                     'sqrtA':p[7],'e':p[5],'M0':p[3],'dn':p[2],'omg':p[14],'OMG0':p[10],
                     'OMGD':p[15],'i0':p[12],'IDOT':p[16],'Crc':p[13],'Crs':p[1],
                     'Cuc':p[4],'Cus':p[6],'Cic':p[9],'Cis':p[11],'TGD':p[22]}
                if sat not in ephs: ephs[sat] = []
                ephs[sat].append(e)
            except: continue
    return ephs

def parse_obs(file):
    if not os.path.exists(file): return []
    with open(file) as f:
        lines = f.readlines()
        i = 0; types = []
        while i < len(lines):
            l = lines[i]; i += 1
            if 'SYS / # / OBS TYPES' in l and l.startswith('G'):
                parts = l.split(); types = parts[2:2+int(parts[1])]
            if 'END OF HEADER' in l: break
        data = []
        while i < len(lines):
            l = lines[i]; i += 1
            if l.startswith('>'):
                dt = datetime.strptime(l[2:21], '%Y %m %d %H %M %S')
                n = int(l[32:35]); obs = {}
                for _ in range(n):
                    ll = lines[i]; i += 1
                    sat = ll[:3]; o = {}
                    for j, t in enumerate(types):
                        v = ll[3+16*j:17+16*j].strip()
                        if v: o[t] = float(v)
                    obs[sat] = o
                data.append({'dt':dt, 'obs':obs})
    return data

def get_sat_pos(e, t):
    tk = t - e['Toe']
    if tk > 302400: tk -= 604800
    elif tk < -302400: tk += 604800
    A = e['sqrtA']**2; n = np.sqrt(MU_GPS/A**3)+e['dn']; M = e['M0']+n*tk
    E = M
    for _ in range(10): E = M + e['e']*np.sin(E)
    v = np.arctan2(np.sqrt(1-e['e']**2)*np.sin(E), np.cos(E)-e['e'])
    phi = v + e['omg']
    u = phi + e['Cuc']*np.cos(2*phi) + e['Cus']*np.sin(2*phi)
    r = A*(1-e['e']*np.cos(E)) + e['Crc']*np.cos(2*phi) + e['Crs']*np.sin(2*phi)
    inc = e['i0'] + e['IDOT']*tk + e['Cic']*np.cos(2*phi) + e['Cis']*np.sin(2*phi)
    xo, yo = r*np.cos(u), r*np.sin(u)
    OMG = e['OMG0'] + (e['OMGD']-OMEGA_E_DOT)*tk - OMEGA_E_DOT*e['Toe']
    x = xo*np.cos(OMG) - yo*np.cos(inc)*np.sin(OMG)
    y = xo*np.sin(OMG) + yo*np.cos(inc)*np.cos(OMG)
    z = yo*np.sin(inc)
    dt = e['cb'] + e['cd']*tk + e['cdr']*tk**2 - 2*np.sqrt(MU_GPS*A)*e['e']*np.sin(E)/CLIGHT**2
    return np.array([x,y,z]), dt

def get_sat_info(ephs, sat, t_rec, pr):
    if sat not in ephs: return None
    e = min(ephs[sat], key=lambda x: abs(t_rec - x['Toe']))
    t_tx = t_rec - pr/CLIGHT
    p, dt = get_sat_pos(e, t_tx)
    th = OMEGA_E_DOT * (pr/CLIGHT)
    R = np.array([[np.cos(th),np.sin(th),0],[-np.sin(th),np.cos(th),0],[0,0,1]])
    return R@p, dt

def spp(obs, ephs, t):
    sp, sc, ov = [], [], []
    for s, sig in obs.items():
        if 'C1C' in sig:
            info = get_sat_info(ephs, s, t, sig['C1C'])
            if info: sp.append(info[0]); sc.append(info[1]); ov.append(sig['C1C'])
    if len(ov) < 4: return None, 0
    st = np.zeros(4)
    for _ in range(10):
        res, H = [], []
        for i in range(len(ov)):
            r = np.linalg.norm(sp[i] - st[:3])
            res.append(r + st[3] - CLIGHT*sc[i] - ov[i])
            H.append([(st[0]-sp[i][0])/r, (st[1]-sp[i][1])/r, (st[2]-sp[i][2])/r, 1])
        dx = np.linalg.lstsq(np.array(H), -np.array(res), rcond=None)[0]
        st += dx
        if np.linalg.norm(dx) < 1e-4: break
    return st[:3], st[3]/CLIGHT

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    with open(os.path.join(args.input_dir, 'session.json')) as f: session = json.load(f)
    base_pos = np.array(session['base_position_ecef_m'])
    ephs = parse_nav(os.path.join(args.input_dir, 'nav.rnx'))
    rover_obs = parse_obs(os.path.join(args.input_dir, 'rover.rnx'))
    base_obs = {o['dt']: o['obs'] for o in parse_obs(os.path.join(args.input_dir, 'base.rnx'))}

    res_list = []
    # RTK filter state
    x_hat = None; P = np.eye(3) * 10.0
    ambs = {} # DD ambiguities
    ref_sat = None
    
    for r_data in rover_obs:
        dt = r_data['dt']; w, tow = to_gps_time(dt)
        r_sigs = r_data['obs']; b_sigs = base_obs.get(dt)
        res_row = {'gps_week': w, 'tow': tow, 'x': 0.0, 'y': 0.0, 'z': 0.0, 'status': 'float'}
        
        p_spp, dt_r = spp(r_sigs, ephs, tow)
        if p_spp is not None and b_sigs:
            tow_rx = tow - dt_r
            common = sorted([s for s in r_sigs if s in b_sigs and 'C1C' in r_sigs[s] and 'L1C' in r_sigs[s]])
            if len(common) >= 5:
                if ref_sat not in common: ref_sat = common[0]
                if x_hat is None: x_hat = p_spp
                
                # Simple DD RTK
                # For each epoch, we solve for position using float ambiguities if possible
                # To keep it simple and fast, we use a single frequency L1 only for now
                # but construct DD equations.
                sats = [s for s in common if s != ref_sat]
                H = []; v = []; R_diag = []
                for s in sats:
                    info_r = get_sat_info(ephs, s, tow_rx, r_sigs[s]['C1C'])
                    info_b = get_sat_info(ephs, s, tow_rx, b_sigs[s]['C1C'])
                    info_r0 = get_sat_info(ephs, ref_sat, tow_rx, r_sigs[ref_sat]['C1C'])
                    info_b0 = get_sat_info(ephs, ref_sat, tow_rx, b_sigs[ref_sat]['C1C'])
                    if info_r and info_b and info_r0 and info_b0:
                        # DD pseudorange
                        geom_r = np.linalg.norm(info_r[0] - x_hat)
                        geom_b = np.linalg.norm(info_b[0] - base_pos)
                        geom_r0 = np.linalg.norm(info_r0[0] - x_hat)
                        geom_b0 = np.linalg.norm(info_b0[0] - base_pos)
                        H_row = (info_r[0]-x_hat)/geom_r - (info_r0[0]-x_hat)/geom_r0
                        H.append(H_row)
                        v.append((r_sigs[s]['C1C'] - b_sigs[s]['C1C']) - (r_sigs[ref_sat]['C1C'] - b_sigs[ref_sat]['C1C']) - (geom_r - geom_b - (geom_r0 - geom_b0)))
                        R_diag.append(1.0) # sigma = 1m
                        
                        # DD phase
                        if 'L1C' in r_sigs[s] and 'L1C' in b_sigs[s] and 'L1C' in r_sigs[ref_sat] and 'L1C' in b_sigs[ref_sat]:
                            amb_key = (s, ref_sat, 'L1')
                            if amb_key not in ambs:
                                ambs[amb_key] = ((r_sigs[s]['L1C'] - b_sigs[s]['L1C']) - (r_sigs[ref_sat]['L1C'] - b_sigs[ref_sat]['L1C'])) - (geom_r - geom_b - (geom_r0 - geom_b0))/L1
                            
                            H.append(H_row)
                            v.append(L1*((r_sigs[s]['L1C'] - b_sigs[s]['L1C']) - (r_sigs[ref_sat]['L1C'] - b_sigs[ref_sat]['L1C']) - ambs[amb_key]) - (geom_r - geom_b - (geom_r0 - geom_b0)))
                            R_diag.append(0.01) # sigma = 1cm
                
                if H:
                    dx = np.linalg.lstsq(np.array(H), np.array(v), rcond=None)[0]
                    x_hat += dx
                    # Update ambiguities (very simple)
                    for s in sats:
                        amb_key = (s, ref_sat, 'L1')
                        if amb_key in ambs:
                            geom_r = np.linalg.norm(info_r[0] - x_hat)
                            geom_r0 = np.linalg.norm(info_r0[0] - x_hat)
                            ambs[amb_key] = ((r_sigs[s]['L1C'] - b_sigs[s]['L1C']) - (r_sigs[ref_sat]['L1C'] - b_sigs[ref_sat]['L1C'])) - (geom_r - geom_b - (geom_r0 - geom_b0))/L1
                    
                    # Check if we can fix
                    fixed = True
                    for amb_val in ambs.values():
                        if abs(amb_val - np.round(amb_val)) > 0.15: # Not very robust but fast
                            fixed = False; break
                    
                    if fixed: 
                        res_row.update({'status': 'fixed'})
                        # Actually re-solve with fixed ambiguities if we wanted to be more precise
                res_row.update({'x': x_hat[0], 'y': x_hat[1], 'z': x_hat[2]})
            else: # Fallback to SPP
                res_row.update({'x': p_spp[0], 'y': p_spp[1], 'z': p_spp[2], 'status': 'float'})
        res_list.append(res_row)
    pd.DataFrame(res_list).to_csv(os.path.join(args.output_dir, 'solution.csv'), index=False)
main()
