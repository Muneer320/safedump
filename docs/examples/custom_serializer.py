"""Example: Registering custom type serializers."""

from dataclasses import dataclass

import safedump


@dataclass
class GeoPoint:
    lat: float
    lon: float


# Register a custom serializer
safedump.register_serializer(GeoPoint, lambda p: {"lat": p.lat, "lon": p.lon})

safedump.install()

# Now GeoPoint objects in crash reports will be serialized nicely
point = GeoPoint(lat=51.5074, lon=-0.1278)
raise ValueError(f"Invalid location: {point}")
