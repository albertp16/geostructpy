import math
from typing import Tuple

class Geostruct:
    def __init__(self, soil_weight: float, h_wall: float, angle_friction: float,
                 angle_embankment: float, angle_inclination: float, angle_friction_wall_soil: float):
        self.soil_weight = soil_weight
        self.h_wall = h_wall
        self.angle_friction = angle_friction
        self.angle_embankment = angle_embankment
        self.angle_inclination = angle_inclination
        self.angle_friction_wall_soil = angle_friction_wall_soil

    def calculate_coefficients(self, PGA: float) -> Tuple[float, float]:
        """Calculates seismic coefficients for horizontal and vertical accelerations."""
        kh = 0.5 * PGA
        kv = 0  # Assuming no vertical acceleration
        return kh, kv

    def inclination_angle(self, kh: float, kv: float) -> float:
        """Calculates the inclination angle of horizontal acceleration in degrees."""
        theta = math.atan(kh / (1 - kv))
        return math.degrees(theta)

    def calculate_ko(self) -> float:
        """Calculates the coefficient of lateral earth pressure at rest."""
        return 1 - math.sin(math.radians(self.angle_friction))

    def static_active_pressure_coefficient(self) -> float:
        """Computes the static active pressure coefficient (Ka)."""
        beta, phi, delta, alpha = self.angle_embankment, self.angle_friction, self.angle_friction_wall_soil, self.angle_inclination
        
        varia_a = math.sin(math.radians(beta + phi)) ** 2
        varia_b = math.sin(math.radians(phi + delta)) * math.sin(math.radians(phi - alpha))
        varia_c = math.sin(math.radians(beta - delta)) * math.sin(math.radians(beta + alpha))
        varia_d = (1 + math.sqrt(varia_b / varia_c)) ** 2
        varia_e = math.sin(math.radians(beta)) ** 2 * math.sin(math.radians(beta - delta)) * varia_d

        return varia_a / varia_e

    def static_passive_pressure_coefficient(self) -> float:
        """Computes the static passive pressure coefficient (Kp)."""
        beta, phi, delta, alpha = self.angle_embankment, self.angle_friction, self.angle_friction_wall_soil, self.angle_inclination

        varia_a = math.sin(math.radians(beta - phi)) ** 2
        varia_b = math.sin(math.radians(phi + delta)) * math.sin(math.radians(phi + alpha))
        varia_c = math.sin(math.radians(beta + delta)) * math.sin(math.radians(beta + alpha))
        varia_d = (1 - math.sqrt(varia_b / varia_c)) ** 2
        varia_e = math.sin(math.radians(beta)) ** 2 * math.sin(math.radians(beta - delta)) * varia_d

        return varia_a / varia_e

    def static_active_seismic_pressure_coefficient(self, theta: float) -> float:
        """Computes the active seismic pressure coefficient (Kae)."""
        beta, phi, delta, alpha = self.angle_embankment, self.angle_friction, self.angle_friction_wall_soil, self.angle_inclination

        varia_a = math.sin(math.radians(beta + phi - theta)) ** 2
        varia_b = math.sin(math.radians(phi + delta)) * math.sin(math.radians(phi - alpha - theta))
        varia_c = math.sin(math.radians(beta - delta - theta)) * math.sin(math.radians(beta + alpha))
        varia_d = (1 + math.sqrt(varia_b / varia_c)) ** 2
        varia_e = math.cos(math.radians(theta)) * math.sin(math.radians(beta)) ** 2 * math.sin(math.radians(beta - delta - theta)) * varia_d

        return varia_a / varia_e

    def calculate_deltaKa(self, kae: float, kv: float, ka: float) -> float:
        """Calculates the change in active earth pressure due to seismic forces."""
        return kae * (1 - kv) - ka

    def compute_lateral_earth_pressures(self, PGA: float) -> None:
        """Calculates and prints the lateral earth pressures for different cases."""
        kh, kv = self.calculate_coefficients(PGA)
        theta = self.inclination_angle(kh, kv)
        ko = self.calculate_ko()
        ka = self.static_active_pressure_coefficient()
        kp = self.static_passive_pressure_coefficient()
        kae = self.static_active_seismic_pressure_coefficient(theta)
        deltaKa = self.calculate_deltaKa(kae, kv, ka)

        atrest_bot = self.h_wall * self.soil_weight * ko
        active_bot = self.h_wall * self.soil_weight * ka
        passive_bot = self.h_wall * self.soil_weight * kp
        active_seismic = self.h_wall * self.soil_weight * deltaKa

        print(f"Seismic Coefficients: kh = {kh:.3f}, kv = {kv:.3f}")
        print(f"Inclination Angle of Horizontal Acceleration: {theta:.3f}°")
        print(f"At‐Rest Earth Pressure = {atrest_bot:.3f} kN/m²")
        print(f"Active Earth Pressure = {active_bot:.3f} kN/m²")
        print(f"Passive Earth Pressure = {passive_bot:.3f} kN/m²")
        print(f"Active Earth Pressure due to Seismic = {active_seismic:.3f} kN/m²")


# Example Usage:
if __name__ == "__main__":
    parameters = {
        "soil_weight": 18,
        "h_wall": 1.60,
        "angle_friction": 30,
        "angle_embankment": 0,
        "angle_inclination": 90,
        "angle_friction_wall_soil": 20
    }

    # Initialize the class
    geo = Geostruct(**parameters)

    # Compute pressures for a given PGA
    PGA = 0.40
    geo.compute_lateral_earth_pressures(PGA)
