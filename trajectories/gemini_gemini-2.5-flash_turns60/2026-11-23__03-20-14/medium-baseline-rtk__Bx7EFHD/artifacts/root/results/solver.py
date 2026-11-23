import argparse
import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Constants for GPS
GPS_PI = 3.1415926535898  # pi
GPS_OMEGA_E = 7.2921151467e-5 # Earth's rotation rate in rad/s
GPS_MU = 3.986005e14     # Earth's gravitational constant for GPS in m^3/s^2
GPS_F = -4.442807633e-10 # Relativistic correction constant in s/sqrt(m)
GPS_C = 299792458.0      # Speed of light in m/s

def rinex_time_to_gps_week_tow(year, month, day, hour, minute, second):
    # Convert given UTC time to GPS Week and Time-Of-Week (TOW)
    # GPS epoch: Jan 6, 1980, 00:00:00 UTC
    gps_epoch = datetime(1980, 1, 6, 0, 0, 0)
    
    try:
        target_datetime = datetime(year, month, day, hour, minute, int(second))
    except ValueError as e:
        print(f"Error converting time to datetime: year={year}, month={month}, day={day}, hour={hour}, minute={minute}, second={second}")
        raise e

    # For RINEX navigation files, broadcast ephemeris times (TOE) are GPS time.
    # No leap second adjustment is needed for TOE if it's already GPST.
    time_diff = target_datetime - gps_epoch
    days = time_diff.days
    seconds_of_day = time_diff.seconds + time_diff.microseconds / 1e6

    gps_week = days // 7
    tow = (days % 7) * 86400 + seconds_of_day

    return gps_week, tow

def parse_nav_file(nav_filepath):
    ephemeris_data = {}
    with open(nav_filepath, 'r') as f:
        lines = f.readlines()

    # Skip header
    header_end = 0
    for i, line in enumerate(lines):
        if 'END OF HEADER' in line:
            header_end = i + 1
            break

    current_prn = None
    current_ephemeris = {}
    i = header_end # Initialize i for the main loop
    while i < len(lines):
        line = lines[i]
        if len(line) >= 3 and line[0] == 'G' and line[1:3].strip().isdigit(): 
            # New satellite ephemeris block starts
            if current_prn is not None and current_ephemeris:
                if current_prn not in ephemeris_data:
                    ephemeris_data[current_prn] = []
                ephemeris_data[current_prn].append(current_ephemeris)

            current_prn = line[1:3].strip() # PRN (e.g., G01, G02)

            # Parse epoch time - CORRECTED SLICES based on RINEX 3.04 N-file format
            year = int(line[4:8].strip())       # Col 6-9
            month = int(line[9:11].strip())    # Col 10-11
            day = int(line[12:14].strip())      # Col 13-14
            hour = int(line[15:17].strip())     # Col 16-17
            minute = int(line[18:20].strip())   # Col 19-20
            second = float(line[21:23].strip()) # Col 22-23

            gps_week, tow = rinex_time_to_gps_week_tow(year, month, day, hour, minute, second)

            # Corrected clock correction slices (19 chars each for Field2/3, 18 for Field1 without explicit plus sign for positive numbers)
            sv_clk_bias_str = line[24:42].replace('D', 'e').strip() # Slices 25-42 (18 chars)
            sv_clk_drift_str = line[42:61].replace('D', 'e').strip() # Slices 43-61 (19 chars)
            sv_clk_drift_rate_str = line[61:80].replace('D', 'e').strip() # Slices 62-80 (19 chars)

            current_ephemeris = {
                'prn': current_prn,
                'week': gps_week,
                'tow': tow,
                'SV_CLK_BIAS': float(sv_clk_bias_str), 
                'SV_CLK_DRIFT': float(sv_clk_drift_str), 
                'SV_CLK_DRIFT_RATE': float(sv_clk_drift_rate_str), 
            }
            # Next 7 lines contain orbital parameters (each field is 19 chars, starting from Col 5)
            # So the slices will be [4:23], [23:42], [42:61], [61:80]
            line_idx_offset = 1
            current_ephemeris['IODE'] = float(lines[i + line_idx_offset][4:23].replace('D', 'e').strip())
            current_ephemeris['Crs'] = float(lines[i + line_idx_offset][23:42].replace('D', 'e').strip())
            current_ephemeris['Delta_n'] = float(lines[i + line_idx_offset][42:61].replace('D', 'e').strip())
            current_ephemeris['M0'] = float(lines[i + line_idx_offset][61:80].replace('D', 'e').strip())
            
            line_idx_offset += 1
            current_ephemeris['Cuc'] = float(lines[i + line_idx_offset][4:23].replace('D', 'e').strip())
            current_ephemeris['Eccentricity'] = float(lines[i + line_idx_offset][23:42].replace('D', 'e').strip())
            current_ephemeris['Cus'] = float(lines[i + line_idx_offset][42:61].replace('D', 'e').strip())
            current_ephemeris['sqrtA'] = float(lines[i + line_idx_offset][61:80].replace('D', 'e').strip())

            line_idx_offset += 1
            current_ephemeris['TOE'] = float(lines[i + line_idx_offset][4:23].replace('D', 'e').strip()) # Time of Ephemeris
            current_ephemeris['Cic'] = float(lines[i + line_idx_offset][23:42].replace('D', 'e').strip())
            current_ephemeris['Omega0'] = float(lines[i + line_idx_offset][42:61].replace('D', 'e').strip())
            current_ephemeris['Cis'] = float(lines[i + line_idx_offset][61:80].replace('D', 'e').strip())

            line_idx_offset += 1
            current_ephemeris['i0'] = float(lines[i + line_idx_offset][4:23].replace('D', 'e').strip())
            current_ephemeris['Crc'] = float(lines[i + line_idx_offset][23:42].replace('D', 'e').strip())
            current_ephemeris['omega'] = float(lines[i + line_idx_offset][42:61].replace('D', 'e').strip())
            current_ephemeris['Omega_DOT'] = float(lines[i + line_idx_offset][61:80].replace('D', 'e').strip())

            line_idx_offset += 1
            current_ephemeris['IDOT'] = float(lines[i + line_idx_offset][4:23].replace('D', 'e').strip())
            current_ephemeris['GPS_Week'] = float(lines[i + line_idx_offset][23:42].replace('D', 'e').strip()) # Actual GPS week for ephemeris
            current_ephemeris['accuracy'] = float(lines[i + line_idx_offset][42:61].replace('D', 'e').strip())
            current_ephemeris['health'] = float(lines[i + line_idx_offset][61:80].replace('D', 'e').strip())

            line_idx_offset += 1
            current_ephemeris['TGD'] = float(lines[i + line_idx_offset][4:23].replace('D', 'e').strip())
            current_ephemeris['IODC'] = float(lines[i + line_idx_offset][23:42].replace('D', 'e').strip())
            current_ephemeris['Trans_Time'] = float(lines[i + line_idx_offset][42:61].replace('D', 'e').strip()) # Transmission Time of Message
            current_ephemeris['fit_interval'] = float(lines[i + line_idx_offset][61:80].replace('D', 'e').strip())

            # Advance i by 8 lines (1 header + 7 data lines) for the next block
            i += 8
        else:
            # If it's not a GXX line, just move to the next line
            i += 1

    # Add the last parsed ephemeris block if exists
    if current_prn is not None and current_ephemeris:
        if current_prn not in ephemeris_data:
            ephemeris_data[current_prn] = []
        ephemeris_data[current_prn].append(current_ephemeris)

    # Sort ephemeris data for each PRN by TOE
    for prn in ephemeris_data:
        ephemeris_data[prn].sort(key=lambda x: x['TOE'])

    return ephemeris_data

def parse_obs_file(obs_filepath):
    # observations = {} # This dict is not used, epoch_data is used below.
    with open(obs_filepath, 'r') as f:
        lines = f.readlines()

    header_end = 0
    obs_types = []
    num_obs_types = 0
    for i, line in enumerate(lines):
        if 'SYS / # / OBS TYPES' in line: 
            if line.startswith('G'): # Only parse GPS observations as per task description
                num_obs_types = int(line[4:6].strip()) # CORRECTED SLICE for '8'
                current_obs_types_str = line[6:60].strip() # CORRECTED SLICE: start from col 7 (index 6)
                obs_types.extend(current_obs_types_str.split())

        if 'END OF HEADER' in line:
            header_end = i + 1
            break
    
    epoch_data = [] # List to store parsed epochs
    i = header_end
    while i < len(lines):
        line = lines[i]
        # Epoch header line: > 2026 03 10 16 00  0.0000000  0  32G
        if line.startswith('>'):
            # print(f"DEBUG: Found epoch header at line {i}: {line.strip()}")
            year = int(line[2:6].strip())
            month = int(line[7:9].strip())
            day = int(line[10:12].strip())
            hour = int(line[13:15].strip())
            minute = int(line[16:18].strip())
            second = float(line[19:29].strip()) # Fractional seconds
            # epoch_flag = int(line[30:31].strip()) # Epoch flag
            num_satellites_in_epoch = int(line[32:35].strip()) # Number of satellites

            epoch_observations = {
                'year': year, 'month': month, 'day': day, 
                'hour': hour, 'minute': minute, 'second': second,
                'satellites': {}
            }
            
            lines_read_for_epoch = 0 # Accumulate lines of observations for this epoch
            sat_processed_in_epoch = 0

            # print(f"DEBUG Epoch {year}/{month}/{day} {hour}:{minute}:{second}, expecting {num_satellites_in_epoch} satellites.")

            while sat_processed_in_epoch < num_satellites_in_epoch and (i + 1 + lines_read_for_epoch) < len(lines):
                obs_line_first = lines[i + 1 + lines_read_for_epoch]
                
                prn_system = obs_line_first[0] # G for GPS
                prn = obs_line_first[1:3] # Satellite PRN
                sat_id = prn_system + prn
                sat_obs = {}

                lines_consumed_by_current_sat = 1 # Each satellite consumes at least one line

                # Read first line of observations for this satellite (obs_type_idx 0-4)
                for obs_type_idx in range(min(len(obs_types), 5)): 
                    obs_type = obs_types[obs_type_idx]
                    field_start = 3 + obs_type_idx * 16 # Col 4, 20, 36, 52, 68 for value part (14 chars)
                    if len(obs_line_first) >= (field_start + 14):
                        val_str = obs_line_first[field_start:field_start+14].strip()
                        try:
                            sat_obs[obs_type] = float(val_str) if val_str else np.nan
                        except ValueError:
                            sat_obs[obs_type] = np.nan

                # print(f"DEBUG   Satellite {sat_id}: Processed first obs line '{obs_line_first.strip()}'")

                # Check for second line of observations for this satellite (obs_type_idx 5-7)
                if len(obs_types) > 5 and (i + 1 + lines_read_for_epoch + 1) < len(lines):
                    obs_line_cont = lines[i + 1 + lines_read_for_epoch + 1]
                    # Continuation lines for the same satellite start with spaces up to column 3
                    if obs_line_cont[0:3].strip() == '': # Confirms it's a continuation line for the *same* satellite
                        # print(f"DEBUG     Satellite {sat_id}: Processing continuation line '{obs_line_cont.strip()}'")
                        for obs_type_idx in range(5, len(obs_types)): 
                            obs_type = obs_types[obs_type_idx]
                            field_start_cont = 3 + (obs_type_idx - 5) * 16 # Col 4, 20, 36 for value part (14 chars)
                            if len(obs_line_cont) >= (field_start_cont + 14):
                                val_str = obs_line_cont[field_start_cont:field_start_cont+14].strip()
                                try:
                                    sat_obs[obs_type] = float(val_str) if val_str else np.nan
                                except ValueError:
                                    sat_obs[obs_type] = np.nan
                        lines_consumed_by_current_sat += 1 # Consume this continuation line

                epoch_observations['satellites'][sat_id] = sat_obs
                sat_processed_in_epoch += 1
                lines_read_for_epoch += lines_consumed_by_current_sat
            
            epoch_data.append(epoch_observations)
            # print(f"DEBUG   Epoch complete. Lines read for epoch: {lines_read_for_epoch}. Advancing i from {i} to {i + 1 + lines_read_for_epoch}")
            i += (1 + lines_read_for_epoch) # Advance i to next epoch header (1 for epoch header itself + lines_read_for_epoch)
        else:
            i += 1 # Move to next line if not an epoch header
    
    return {}, obs_types, epoch_data # Returning parsed header info and epoch data

# Function to calculate satellite position from ephemeris
def calculate_satellite_position(ephemeris, target_gps_week, target_tow):
    # Implements the algorithm from IS-GPS-200K (or similar, simplified)
    # This is a placeholder and needs full implementation

    # Select the correct ephemeris record based on target_tow
    # For simplicity, finding the closest TOE for now. A proper implementation would consider fit interval etc.
    best_eph = None
    min_dt = float('inf')
    for eph in ephemeris:
        dt = abs(eph['TOE'] - target_tow)
        if dt < min_dt:
            min_dt = dt
            best_eph = eph
    
    if best_eph is None:
        return None, None # No suitable ephemeris found

    eph = best_eph

    # Time from ephemeris reference epoch
    # Correct definition of tk: Time from ephemeris reference epoch (t_k = t - t_oe)
    # The time in ephemeris is GPS week and TOW, the target_tow is also GPS week and TOW.
    # So, tk = target_tow - eph['TOE']
    tk = target_tow - eph['TOE']

    # Account for beginning/end of GPS week if needed (e.g., if tk < -302400 or tk > 302400)
    # For this task, assuming the TOW values are within a single week relevant to TOE.

    # Satellite clock correction
    dt_sv = eph['SV_CLK_BIAS'] + eph['SV_CLK_DRIFT'] * tk + eph['SV_CLK_DRIFT_RATE'] * (tk**2)
    # Relativistic correction (simplified, more detailed model may include TGD and other terms)
    # Simplified relativistic correction according to RTKLIB (or IS-GPS-200) for clock error:
    dt_rel = GPS_F * eph['Eccentricity'] * eph['sqrtA'] * np.sin(eph['M0'] + eph['Delta_n'] * tk)
    dt_sv += dt_rel

    # Mean anomaly (Mk)
    A = eph['sqrtA']**2
    n0 = np.sqrt(GPS_MU / (A**3)) # Corrected mean motion
    n = n0 + eph['Delta_n'] # Corrected mean motion
    Mk = eph['M0'] + n * tk

    # Iteratively solve for eccentric anomaly (Ek)
    Ek_old = Mk
    for _ in range(10): # Max 10 iterations
        Ek_new = Mk + eph['Eccentricity'] * np.sin(Ek_old)
        if abs(Ek_new - Ek_old) < 1e-12: # Check for convergence
            break
        Ek_old = Ek_new
    Ek = Ek_new

    # True anomaly (vk)
    vk = np.arctan2(np.sqrt(1 - eph['Eccentricity']**2) * np.sin(Ek), np.cos(Ek) - eph['Eccentricity'])

    # Argument of latitude (uk)
    uk = vk + eph['omega']

    # Second harmonic perturbations
    delta_uk = eph['Cus'] * np.sin(2 * uk) + eph['Cuc'] * np.cos(2 * uk)
    delta_rk = eph['Crs'] * np.sin(2 * uk) + eph['Crc'] * np.cos(2 * uk)
    delta_ik = eph['Cis'] * np.sin(2 * uk) + eph['Cic'] * np.cos(2 * uk)

    # Corrected argument of latitude, radius, and inclination
    uk_prime = uk + delta_uk
    rk_prime = A * (1 - eph['Eccentricity'] * np.cos(Ek)) + delta_rk
    ik_prime = eph['i0'] + eph['IDOT'] * tk + delta_ik

    # Positions in orbital plane
    xk_prime = rk_prime * np.cos(uk_prime)
    yk_prime = rk_prime * np.sin(uk_prime)

    # Corrected longitude of ascending node (Omega_k)
    Omega_k = eph['Omega0'] + (eph['Omega_DOT'] - GPS_OMEGA_E) * tk - GPS_OMEGA_E * eph['TOE'] # Simplified
    # More accurate: Omega_k = eph['Omega0'] + (eph['Omega_DOT'] - GPS_OMEGA_E) * (tk)
    # This definition of Omega_k can be tricky. Let's stick with the IS-GPS-200K one.
    # Omega_k = eph['Omega0'] + (eph['Omega_DOT'] - GPS_OMEGA_E) * tk
    # However, the task uses RTKLIB for reference (implied by file names and RINEX 3.04), which uses:
    # Omega_k = eph['Omega0'] + (eph['Omega_DOT'] - GPS_OMEGA_E) * tk - GPS_OMEGA_E * eph['TOE'] 
    # Let's use simpler form first: Omega_k = eph['Omega0'] + (eph['Omega_DOT'] - GPS_OMEGA_E) * tk
    Omega_k = eph['Omega0'] + (eph['Omega_DOT'] - GPS_OMEGA_E) * (tk)

    # Earth-fixed coordinates
    Xk = xk_prime * np.cos(Omega_k) - yk_prime * np.cos(ik_prime) * np.sin(Omega_k)
    Yk = xk_prime * np.sin(Omega_k) + yk_prime * np.cos(ik_prime) * np.cos(Omega_k)
    Zk = yk_prime * np.sin(ik_prime)
    
    sat_pos_ecef = np.array([Xk, Yk, Zk])

    return sat_pos_ecef, dt_sv

def main():
    print("Solver script started.")
    parser = argparse.ArgumentParser(description='GPS Kinematic Trajectory Solver')
    parser.add_argument('--input-dir', required=True, help='Directory containing input RINEX and session files')
    parser.add_argument('--output-dir', required=True, help='Directory to write the solution.csv file')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    session_json_path = os.path.join(args.input_dir, 'session.json')
    with open(session_json_path, 'r') as f:
        session_data = json.load(f)
    base_position_ecef_m = np.array(session_data['base_position_ecef_m'])
    print(f"Loaded base position: {base_position_ecef_m}")

    # Parse navigation file
    nav_filepath = os.path.join(args.input_dir, 'nav.rnx')
    ephemeris_data = parse_nav_file(nav_filepath)
    print(f"Parsed navigation file. Found ephemeris for {len(ephemeris_data)} satellites.")
    if '01' in ephemeris_data:
        print(f"First ephemeris for G01: TOE={ephemeris_data['01'][0]['TOE']}, M0={ephemeris_data['01'][0]['M0']}")

    # Parse base observation file
    base_obs_filepath = os.path.join(args.input_dir, 'base.rnx')
    _, obs_types, base_obs_data = parse_obs_file(base_obs_filepath)
    print(f"Parsed base observation file. Found {len(base_obs_data)} epochs.")
    print(f"Observed types: {obs_types}")
    if base_obs_data:
        first_epoch_sats = base_obs_data[0]['satellites']
        print(f"First epoch ({base_obs_data[0]['year']}/{base_obs_data[0]['month']}/{base_obs_data[0]['day']} {base_obs_data[0]['hour']}:{base_obs_data[0]['minute']}:{base_obs_data[0]['second']}) has {len(first_epoch_sats)} satellites.")
        if 'G01' in first_epoch_sats:
            print(f"G01 observations in first epoch: {first_epoch_sats['G01']}")

    # Parse rover observation file
    rover_obs_filepath = os.path.join(args.input_dir, 'rover.rnx')
    _, _, rover_obs_data = parse_obs_file(rover_obs_filepath)
    print(f"Parsed rover observation file. Found {len(rover_obs_data)} epochs.")

    # Test satellite position calculation for a sample
    if '01' in ephemeris_data and base_obs_data:
        sample_eph = ephemeris_data['01'][0] # Use the first ephemeris for G01
        sample_epoch = base_obs_data[0] # Use the first epoch from base observations
        sample_gps_week, sample_tow = rinex_time_to_gps_week_tow(sample_epoch['year'], sample_epoch['month'], sample_epoch['day'], sample_epoch['hour'], sample_epoch['minute'], sample_epoch['second'])
        print(f"Calculating G01 position for GPS Week {sample_gps_week}, TOW {sample_tow}")
        sat_pos, sat_clk = calculate_satellite_position([sample_eph], sample_gps_week, sample_tow) # Pass a list for ephemeris_data to the function
        if sat_pos is not None:
            print(f"Calculated G01 ECEF position: {sat_pos}")
            print(f"Calculated G01 clock bias: {sat_clk}")
        else:
            print(f"Failed to calculate G01 ECEF position.")

    dummy_data = {
        'gps_week': [],
        'tow': [],
        'x': [],
        'y': [],
        'z': [],
        'status': []
    }
    df = pd.DataFrame(dummy_data)
    output_csv_path = os.path.join(args.output_dir, 'solution.csv')
    df.to_csv(output_csv_path, index=False)
    print(f"Empty solution.csv created at {output_csv_path}")

if __name__ == '__main__':
    main()
