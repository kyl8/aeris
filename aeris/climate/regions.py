from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Coordinate:
    name: str
    latitude: float
    longitude: float
    country: str = "BR"
    biome: str = "mata_atlantica"


@dataclass(frozen=True, slots=True)
class Region:
    slug: str
    name: str
    bbox: tuple[float, float, float, float]
    coordinates: tuple[Coordinate, ...]

    @classmethod
    def from_bbox(
        cls,
        *,
        slug: str,
        name: str,
        bbox: tuple[float, float, float, float],
        grid_spacing_degrees: float,
    ) -> "Region":
        min_lon, min_lat, max_lon, max_lat = bbox
        points: list[Coordinate] = []
        lat = min_lat
        row = 0
        while lat <= max_lat + 1e-9:
            lon = min_lon
            col = 0
            while lon <= max_lon + 1e-9:
                points.append(Coordinate(name=f"grid_{row:03d}_{col:03d}", latitude=round(lat, 6), longitude=round(lon, 6)))
                lon += grid_spacing_degrees
                col += 1
            lat += grid_spacing_degrees
            row += 1
        return cls(slug=slug, name=name, bbox=bbox, coordinates=tuple(points))

    @classmethod
    def from_coordinates(cls, *, slug: str, name: str, coordinates: Iterable[Coordinate]) -> "Region":
        coords = tuple(coordinates)
        if not coords:
            raise ValueError("region requires at least one coordinate")
        min_lat = min(point.latitude for point in coords)
        max_lat = max(point.latitude for point in coords)
        min_lon = min(point.longitude for point in coords)
        max_lon = max(point.longitude for point in coords)
        return cls(slug=slug, name=name, bbox=(min_lon, min_lat, max_lon, max_lat), coordinates=coords)

    def with_grid(self, spacing_degrees: float = 0.25) -> "Region":
        grid_region = Region.from_bbox(
            slug=f"{self.slug}_grid_{str(spacing_degrees).replace('.', '_')}",
            name=f"{self.name} grid {spacing_degrees}",
            bbox=self.bbox,
            grid_spacing_degrees=spacing_degrees,
        )
        return Region(slug=self.slug, name=self.name, bbox=self.bbox, coordinates=grid_region.coordinates)


BAIXADA_SANTISTA_CITIES = (
    Coordinate("santos", -23.9608, -46.3336),
    Coordinate("sao_vicente", -23.9631, -46.3919),
    Coordinate("praia_grande", -24.0058, -46.4028),
    Coordinate("guaruja", -23.9931, -46.2564),
    Coordinate("cubatao", -23.8950, -46.4253),
    Coordinate("mongagua", -24.0931, -46.6208),
    Coordinate("itanhaem", -24.1831, -46.7889),
    Coordinate("peruibe", -24.3201, -46.9983),
    Coordinate("bertioga", -23.8544, -46.1386),
)


BAIXADA_SANTISTA = Region(
    slug="baixada_santista",
    name="Baixada Santista, SP, Brasil",
    bbox=(-47.10, -24.40, -46.05, -23.78),
    coordinates=BAIXADA_SANTISTA_CITIES,
)
