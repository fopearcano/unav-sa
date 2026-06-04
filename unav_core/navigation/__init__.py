"""Navigation state and the real-time navigator.

Owns the **navigation state**: the observer/camera pose, reference frame, field
of view, target selection, and the real-time update loop that the App and
adapters drive. Navigation is expressed in core astronomical terms (frames,
coordinates and distances from :mod:`unav_core.astro`) and is fully decoupled
from any renderer or DCC.
"""
