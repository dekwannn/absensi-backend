import math

class GeoService:
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Menghitung jarak antara dua titik koordinat (Latitude, Longitude)
        Menggunakan rumus Haversine.
        Output: Jarak dalam meter (float).
        """
        R = 6371000  # Radius bumi dalam meter

        # Konversi derajat ke radian
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        # Rumus Haversine
        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2.0) ** 2
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        meters = R * c
        return meters

    @staticmethod
    def is_within_radius(lat_user, lon_user, lat_office, lon_office, radius_meters=100):
        distance = GeoService.calculate_distance(lat_user, lon_user, lat_office, lon_office)
        return distance <= radius_meters, distance