"""Derivadas del terreno sobre rejillas regulares (numpy puro).

Convenciones: `dem` en metros, fila 0 al norte, `res` = tamaño de celda en metros.
NaN marca datos ausentes y se propaga.
"""
import numpy as np


def gradient(dem, res):
    """Devuelve (dz/dx hacia el este, dz/dy hacia el norte)."""
    dzdy_rows, dzdx = np.gradient(dem, res)
    return dzdx, -dzdy_rows


def slope_deg(dem, res):
    dzdx, dzdy = gradient(dem, res)
    return np.degrees(np.arctan(np.hypot(dzdx, dzdy)))


def aspect_deg(dem, res):
    """Dirección hacia la que cae la ladera, 0 = norte, 90 = este."""
    dzdx, dzdy = gradient(dem, res)
    return (np.degrees(np.arctan2(-dzdx, -dzdy)) + 360.0) % 360.0


def hillshade(dem, res, azimuth=315.0, altitude=45.0):
    """Sombreado 0..1 con sol en `azimuth` (desde el norte) y `altitude` grados."""
    dzdx, dzdy = gradient(dem, res)
    nx, ny, nz = -dzdx, -dzdy, np.ones_like(dem)
    norm = np.sqrt(nx**2 + ny**2 + nz**2)
    az, alt = np.radians(azimuth), np.radians(altitude)
    sx, sy, sz = np.sin(az) * np.cos(alt), np.cos(az) * np.cos(alt), np.sin(alt)
    return np.clip((nx * sx + ny * sy + nz * sz) / norm, 0.0, 1.0)


def _box_mean(a, r):
    """Media en ventana cuadrada de lado 2r+1 ignorando NaN (imagen integral)."""
    valid = np.isfinite(a)
    filled = np.where(valid, a, 0.0)

    def boxsum(x):
        c = np.pad(np.pad(x, r, mode="constant"), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        k = 2 * r + 1
        return c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]

    s, n = boxsum(filled), boxsum(valid.astype(float))
    with np.errstate(invalid="ignore", divide="ignore"):
        out = s / n
    out[~valid] = np.nan
    return out


def tri(dem):
    """Terrain Ruggedness Index: media del |desnivel| con los 8 vecinos (m)."""
    p = np.pad(dem, 1, mode="edge")
    acc = np.zeros_like(dem)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                acc += np.abs(p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx] - dem)
    return acc / 8.0


def tpi(dem, radius_cells):
    """Topographic Position Index: cota menos la media del entorno (m). >0 lomas, <0 vaguadas."""
    return dem - _box_mean(dem, radius_cells)


def block_reduce(a, factor, how):
    """Agrega bloques factor×factor con 'mean', 'max' o 'std' ignorando NaN."""
    h, w = (a.shape[0] // factor) * factor, (a.shape[1] // factor) * factor
    b = a[:h, :w].reshape(h // factor, factor, w // factor, factor)
    fn = {"mean": np.nanmean, "max": np.nanmax, "std": np.nanstd}[how]
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return fn(b, axis=(1, 3))


def mean_direct_insolation(slope, aspect, lat_deg, n_decl=12, n_hours=24):
    """Insolación directa media anual relativa a una superficie horizontal (sin sombras proyectadas).

    Promedia cos(ángulo de incidencia) sobre declinaciones solares de Marte (±25.2°) y horas del día.
    1.0 = recibe lo mismo que el llano; >1 laderas orientadas al sol.
    """
    s, a = np.radians(slope), np.radians(aspect)
    lat = np.radians(lat_deg)
    nx, ny, nz = np.sin(s) * np.sin(a), np.sin(s) * np.cos(a), np.cos(s)
    acc, flat = np.zeros_like(slope), 0.0
    for decl in np.radians(25.19) * np.sin(np.linspace(0, 2 * np.pi, n_decl, endpoint=False)):
        for h in np.linspace(-np.pi, np.pi, n_hours, endpoint=False):
            # vector solar en coordenadas locales (este, norte, arriba)
            sz = np.sin(lat) * np.sin(decl) + np.cos(lat) * np.cos(decl) * np.cos(h)
            if sz <= 0:
                continue
            sx = -np.cos(decl) * np.sin(h)
            sy = np.cos(lat) * np.sin(decl) - np.sin(lat) * np.cos(decl) * np.cos(h)
            acc += np.clip(nx * sx + ny * sy + nz * sz, 0, None)
            flat += sz
    return acc / flat
