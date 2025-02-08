import math

## INPUTS
parameters = {
    "soil_weight": 18,
    "h_wall": 1.60,
    "angle_friction": 30,
    "angle_embankment": 0,
    "angle_inclination": 90,
    "angle_friction_wall_soil": 20
}

print('soil_weight = ' + str(parameters["soil_weight"]))
print('angle_friction = ' + str(parameters["angle_friction"]))
print('angle_embankment = ' + str(parameters["angle_embankment"]))
print('angle_inclination = ' + str(parameters["angle_inclination"]))
print('angle_friction_wall_soil = ' + str(parameters["angle_friction_wall_soil"]))

def calculate_coefficients(PGA):
    kh = 0.5 * PGA
    kv = 0
    return kh, kv

PGA = 0.40
kh, kv = calculate_coefficients(PGA)


print(kh)
print(kv)

import math

def incHorAcc(kh, kv):
    """
    Calculate the inclination angle of horizontal acceleration.

    Parameters:
    kh (float): The horizontal acceleration in the x-direction.
    kv (float): The vertical acceleration in the z-direction.

    Returns:
    float: The inclination angle in degrees.
    """
    theta_solve_init = kh / (1 - kv)
    theta = math.atan(theta_solve_init)
    toDegree = theta * 180 / math.pi
    return toDegree

coefficient_seis = incHorAcc(kh,kv)
coefficient_seis
#At-rest Eart Pressure
def calculate_ko(angle_friction):
    """
    Calculate the coefficient of lateral earth pressure at-rest.

    Parameters:
    angle_friction (float): The angle of friction in degrees.

    Returns:
    float: The coefficient of lateral earth pressure at-rest.
    """
    return 1 - math.sin(math.radians(angle_friction))

ko = calculate_ko(parameters["angle_friction"])
# ko
def staticActivePressureCoefficient(alpha, beta, delta, phi):
    """
    Calculate the coefficient of static active pressure.

    Parameters:
    alpha (float): The angle of inclination of the wall in degrees.
    beta (float): The angle of inclination of the backfill in degrees.
    delta (float): The angle of friction between the wall and the backfill in degrees.
    phi (float): The angle of friction between the backfill and the ground in degrees.

    Returns:
    float: The coefficient of static active pressure.
    """
    varia_a = math.pow(math.sin(math.radians(beta + phi)), 2)
    varia_b = math.sin(math.radians(phi + delta)) * math.sin(math.radians(phi - alpha))
    varia_c = math.sin(math.radians(beta - delta)) * math.sin(math.radians(beta + alpha))
    varia_d = math.pow(1 + math.sqrt(varia_b / varia_c), 2)
    varia_e = math.pow(math.sin(math.radians(beta)), 2) * math.sin(math.radians(beta - delta)) * varia_d
    results = varia_a / varia_e
    return results
    
ka = staticActivePressureCoefficient(parameters["angle_embankment"], parameters["angle_inclination"], parameters["angle_friction_wall_soil"], parameters["angle_friction"])
# ka
def staticPassivePressureCoefficient(alpha, beta, delta, phi):
    """
    Calculate the static passive pressure coefficient.

    Parameters:
    alpha (float): The alpha angle in degrees.
    beta (float): The beta angle in degrees.
    delta (float): The delta angle in degrees.
    phi (float): The phi angle in degrees.

    Returns:
    float: The static passive pressure coefficient.

    """
    varia_a = math.pow(math.sin(math.radians(beta - phi)), 2)

    varia_b = math.sin(math.radians(phi + delta)) * math.sin(math.radians(phi + alpha))
    varia_c = math.sin(math.radians(beta + delta)) * math.sin(math.radians(beta + alpha))

    varia_d = math.pow(1 - math.sqrt(varia_b / varia_c), 2)

    varia_e = math.pow(math.sin(math.radians(beta)), 2) * math.sin(math.radians(beta - delta)) * varia_d

    results = varia_a / varia_e
    return results


def staticPassivePressureCoefficient(alpha, beta, delta, phi):
    """
    Calculates the static passive pressure coefficient.

    Parameters:
    alpha (float): The angle alpha in degrees.
    beta (float): The angle beta in degrees.
    delta (float): The angle delta in degrees.
    phi (float): The angle phi in degrees.

    Returns:
    float: The calculated static passive pressure coefficient.

    """
    varia_a = math.pow(math.sin(math.radians(beta - phi)), 2)
    varia_b = math.sin(math.radians(phi + delta)) * math.sin(math.radians(phi + alpha))
    varia_c = math.sin(math.radians(beta + delta)) * math.sin(math.radians(beta + alpha))
    varia_d = math.pow(1 - math.sqrt(varia_b / varia_c), 2)
    varia_e = math.pow(math.sin(math.radians(beta)), 2) * math.sin(math.radians(beta - delta)) * varia_d
    results = varia_a / varia_e
    return results
# def staticPassivePressureCoefficient(alpha,beta,delta,phi):
    
#     varia_a = math.pow( math.sin(math.radians(beta - phi)),2) #okay
    
#     varia_b = math.sin(math.radians(phi + delta))*math.sin(math.radians(phi + alpha))     
#     varia_c = math.sin(math.radians(beta + delta))*math.sin(math.radians(beta + alpha)) 
    
#     varia_d = math.pow(1 - math.sqrt(varia_b/varia_c),2)
    
    
#     varia_e = math.pow(math.sin(math.radians(beta)),2)*math.sin(math.radians(beta - delta))*varia_d 
    
#     results = varia_a/varia_e
#     return results

kp = staticPassivePressureCoefficient(parameters["angle_embankment"], parameters["angle_inclination"], parameters["angle_friction_wall_soil"], parameters["angle_friction"])
# kp
def staticActiveSeismicPressureCoefficient(alpha,beta,delta,phi,theta):
    
    varia_a = math.pow( math.sin(math.radians(beta + phi - theta)),2) 
    
    varia_b = math.sin(math.radians(phi + delta))*math.sin(math.radians(phi - alpha - theta))     
    varia_c = math.sin(math.radians(beta - delta - theta))*math.sin(math.radians(beta + alpha)) 
    
    varia_d = math.pow(1 + math.sqrt(varia_b/varia_c),2)
    
    
    varia_e = math.cos(math.radians(theta))*math.pow(math.sin(math.radians(beta)),2)*math.sin(math.radians(beta - delta - theta))*varia_d 
    
    results = varia_a/varia_e
    return results

kae = staticActiveSeismicPressureCoefficient(parameters["angle_embankment"], parameters["angle_inclination"], parameters["angle_friction_wall_soil"], parameters["angle_friction"], coefficient_seis)
# kae
def calculate_deltaKa(kae, kv, ka):
    """
    Calculate the change in active earth pressure due to seismic forces.

    Parameters:
    kae (float): The coefficient of static active seismic pressure.
    kv (float): The vertical acceleration in the z-direction.
    ka (float): The coefficient of static active pressure.

    Returns:
    float: The change in active earth pressure due to seismic forces.
    """
    deltaKa = kae * (1 - kv) - ka
    return deltaKa

deltaKa = calculate_deltaKa(kae, kv, ka)
# print(deltaKa)
## Lateral Earth Pressures
atrestbot = parameters["h_wall"] * parameters["soil_weight"] * ko
atactivebot = parameters["h_wall"] * parameters["soil_weight"] * ka
atpassivebot = parameters["h_wall"] * parameters["soil_weight"] * kp
attopseis = parameters["h_wall"] * parameters["soil_weight"] * deltaKa

print("At‐Rest Earth Pressure = " + str(atrestbot))
print("Active Earth Pressure = " + str(atactivebot))
print("Passive Earth Pressure = " + str(atpassivebot))
print("Active Earth Pressure due to Seismic = " + str(attopseis))


# import math

# def compute_theta(k_h, k_v):
#     return math.atan(abs(k_h) / (1 + k_v))

# def compute_KAE(alpha, phi, theta, delta, beta):
#     numerator = math.sin(alpha + phi - theta)**2
#     term1 = math.sin(alpha)**2 * math.sin(alpha - delta - theta)
#     term2 = 1 + math.sqrt((math.sin(phi + delta) * math.sin(phi - beta - theta)) / 
#                           (math.sin(alpha - delta - theta) * math.sin(alpha + beta)))
#     denominator = math.cos(theta) * term1 * term2**2
#     return numerator / denominator

# def compute_KPE(alpha, phi, theta, delta, beta):
#     numerator = math.sin(alpha - phi + theta)**2
#     term1 = math.sin(alpha)**2 * math.sin(alpha + delta + theta)
#     term2 = 1 - math.sqrt((math.sin(phi + delta) * math.sin(phi + beta - theta)) / 
#                           (math.sin(alpha - delta + theta) * math.sin(alpha + beta)))
#     denominator = math.cos(theta) * term1 * term2**2
#     return numerator / denominator