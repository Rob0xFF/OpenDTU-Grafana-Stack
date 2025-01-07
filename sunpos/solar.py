import math
from datetime import datetime, timedelta
import pytz

# Inputs
start_time = datetime(2024, 1, 1, 0, 0, 0)  # Start of the timespan
end_time = datetime(2030, 12, 31, 23, 50, 0)  # End of the timespan
timezone = pytz.timezone("Europe/Berlin")  # Example timezone with DST
measurement_name = "solar_data"  # Define the measurement name
K = 1  # Offset in decimal hours
L = 0  # Longitude in degrees
M = 0  # Latitude in degrees
P1, alpha1, beta1 = 60, 29, -14  # Parameters for yield1 (peak power, normal altitude (horizon = 0°), normal azimut (south = 0°))
P2, alpha2, beta2 = 40, 49, -14  # Parameters for yield2 (peak power, normal altitude (horizon = 0°), normal azimut (south = 0°))
P3, alpha3, beta3 = 60, 26, 67  # Parameters for yield3 (peak power, normal altitude (horizon = 0°), normal azimut (south = 0°))
eps = -0.05 # empiric athmospheric extinction coefficient

# Helper function for solar declination
def calculate_delta(n):
    return 23.45 * math.sin(2 * math.pi * (284 + n) / 365)

# Helper function for equation of time
def calculate_equation_of_time(n):
    P_angle = n / 365 * 2 * math.pi
    return 229.18312 * (
        0.000075
        + 0.001868 * math.cos(P_angle)
        - 0.032077 * math.sin(P_angle)
        - 0.014615 * math.cos(2 * P_angle)
        - 0.04089 * math.sin(2 * P_angle)
    )

# Helper function for Phi calculations
def calculate_phi(P, alpha, beta, X, V):
    alpha_radians = alpha * math.pi / 180
    beta_radians = beta * math.pi / 180
    X_radians = X * math.pi / 180
    V_radians = V * math.pi / 180
    return P * (
        math.cos(alpha_radians) * math.sin(beta_radians) * math.cos(X_radians) * math.sin(V_radians)
        + math.cos(alpha_radians) * math.cos(beta_radians) * math.cos(X_radians) * math.cos(V_radians)
        + math.sin(alpha_radians) * math.sin(X_radians)
    )

# Helper function for yields
def calculate_yield(phi, X):
    # alternative extiction model start
    # AM = 1 / (math.cos((90 - X) * math.pi / 180) + 0.50572 * (96.07995 - (90 - X) * math.pi / 180) ** -1.6364) # Air Mass, model: Kasten&Young
    # I = 1.1 * max(phi, 0) * 0.7 ** (AM ** 0.678)
    # return I if X > 0 else 0
    # alternative model stop
    return max(phi, 0) * math.exp(eps / math.sin(X * math.pi / 180)) if X > 0 else 0

# Prepare the output file
output_file = "solar_calculations_cli_alt_extinction.csv"
with open(output_file, "w") as file:
    # Write InfluxDB annotations
    file.write("#group,false,false,false,false,false,false,false,false,false\n")
    file.write("#datatype,string,dateTime:RFC3339,double,double,double,double,double,double,string\n")
    file.write("#default,_result,,,,,,,\n")
    file.write(",result,time,azimuth,height,yield1,yield2,yield3,total_yield,_measurement\n")
    
    # Iterate over the timespan with 15-minute intervals
    current_time = start_time
    while current_time <= end_time:
        # Localize time and calculate UTC offset
        localized_time = timezone.localize(current_time)

        # Calculate the day of the year
        n = (current_time - datetime(current_time.year, 1, 1)).days + 1

        # Calculate delta (solar declination)
        delta = calculate_delta(n)

        # Calculate equation of time (Q3)
        Q = calculate_equation_of_time(n)

        # Calculate local solar time (H3)
        J_decimal = current_time.hour + current_time.minute / 60 + current_time.second / 3600
        R = (J_decimal - K) + L / 15 + Q / 60

        # Calculate azimuth-related time angle (S3)
        S = (R - 12) / 12 * math.pi

        # Latitude (T3) and declination (U3) in radians
        T = M * math.pi / 180
        U = delta * math.pi / 180

        # Azimuth (V3)
        V = 180 / math.pi * S

        # Solar height (sinSonnenhöhe, W3) and X3
        W = math.sin(T) * math.sin(U) + math.cos(T) * math.cos(U) * math.cos(S)
        X = math.asin(W) * 180 / math.pi if W >= -1 and W <= 1 else 0  # Handle edge cases

        # Calculate Y3, Z3, and AA3
        Y = calculate_phi(P1, alpha1, beta1, X, V)
        Z = calculate_phi(P2, alpha2, beta2, X, V)
        AA = calculate_phi(P3, alpha3, beta3, X, V)

        # Calculate yields
        AC = calculate_yield(Y, X)  # yield1
        AD = calculate_yield(Z, X)  # yield2
        AE = calculate_yield(AA, X)  # yield3
        AF = AC + AD + AE  # Total yield

        # Write to the file
        file.write(f",,{localized_time.isoformat()},{V},{X},{AC},{AD},{AE},{AF},solpos\n")

        # Increment by 10 minutes
        current_time += timedelta(minutes=10)

print(f"Calculations complete. Results saved to {output_file}.")