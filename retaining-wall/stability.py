import math

# Input data
wall_data = {
    "stem": {
        "height": 1.650,
        "width": 0.250,
        "offset": 0
    },
    "base": {
        "width": 1,
        "thickness": 0.350
    },
    "active_and_passive_soil": {
        "gamma": 14,  # kN/m³
        "friction_angle": 20   # degrees
    },
    "substructure_soil": {
        "gamma": 14,  # kN/m³
        "soil_concrete_friction_coefficient": 0.30,
        "allowable_bearing_pressure": 75 # kPa
    },
    "surcharge_load_value": -4.8,  # kN/m
    "unit_weight_concrete": 23.58  # kN/m³
}


def calculate_sliding_safety(wall_data):
    # Extract input values
    gamma_soil = wall_data["active_and_passive_soil"]["gamma"]
    gamma_conc = wall_data["unit_weight_concrete"]
    mu = wall_data["substructure_soil"]["soil_concrete_friction_coefficient"]
    theta = wall_data["active_and_passive_soil"]["friction_angle"]
    stem_h = wall_data["stem"]["height"]
    stem_w = wall_data["stem"]["width"]
    stem_o = wall_data["stem"]["offset"]
    base_w = wall_data["base"]["width"]
    base_t = wall_data["base"]["thickness"]
    q_surcharge = wall_data["surcharge_load_value"]

    # Earth pressure coefficient (Rankine)
    ka = (1 - math.sin(math.radians(theta))) / (1 + math.sin(math.radians(theta)))
    print(f"Active Earth Pressure Coefficient (ka): {ka}")

    # Sliding forces
    h_active = 0.5 * gamma_soil * (stem_h + base_t) ** 2 * ka
    h_eq = q_surcharge / gamma_soil
    h_surcharge = gamma_soil * h_eq * (stem_h + base_t) * ka
    total_sliding_force = h_active + h_surcharge

    # Vertical loads
    w_stem = gamma_conc * stem_h * stem_w
    w_base = gamma_conc * base_t * base_w
    w_active = gamma_soil * stem_h * (base_w - stem_o - stem_w)
    w_surcharge = -q_surcharge * (base_w - stem_o - stem_w)
    sum_w = w_stem + w_base + w_active + w_surcharge

    # Friction resisting force
    friction_force = mu * sum_w

    # Factor of Safety
    fs_sliding = friction_force / total_sliding_force
    fs_status = "PASS" if fs_sliding >= 1.5 else "FAIL"

    wall_data["factor_of_sliding_safety"] = {
        "fs": round(fs_sliding, 3),
        "status": fs_status
    }

    return wall_data



print("Calculating sliding safety...")
print("Input data: ", calculate_sliding_safety(wall_data)["factor_of_sliding_safety"]["fs"])