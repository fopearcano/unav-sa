# UNAV-SA — Navigation State

The navigation pose and parameters: `NavigatorState` (serialisable), `Camera`
(live controller) and `Vec3` (the vector type). All distances are in **parsecs**.

## `Vec3`

A small immutable (frozen) 3D vector with the ops the camera/navigation need:
`+ - *` (scalar), `dot`, `cross`, `length`, `normalized`, `distance_to`,
`as_tuple`, and `Vec3.of(x, y, z)`. Components must be finite. Because it is a
frozen pydantic model it serialises cleanly inside `NavigatorState` and events,
and it is hashable.

## `NavigatorState`

The canonical, validated, serialisable navigation state.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `position` | `Vec3` | `(0,0,0)` | Camera position (pc). |
| `direction` | `Vec3` | `(0,0,-1)` | View direction (non-zero). |
| `up` | `Vec3` | `(0,1,0)` | Up vector (non-zero). |
| `fov_degrees` | float | `60` | Field of view, `0 < fov < 180`. |
| `near_distance` | float | `0` | Near clip, `≥ 0`. |
| `far_distance` | float | `1000` | Far clip, `> 0` and `> near_distance`. |
| `cone_angle_degrees` | float | `45` | Visible-sector cone **half-angle**, `0 < a ≤ 180`. |
| `epoch` | str? | `None` | Reference epoch, e.g. `"J2016.0"`. |
| `max_visible_objects` | int | `1000` | Visible-object cap, `≥ 1`. |
| `active_dataset_ids` | list[str] | `[]` | Active datasets (advisory — see [engine doc](NAVIGATION_ENGINE.md)). |

Validation rejects a zero `direction`/`up`, `far_distance ≤ near_distance`,
out-of-range angles, `max_visible_objects < 1`, and unknown fields
(`extra="forbid"`).

Helpers: `forward()` (normalised direction), `to_camera()`, and
`NavigatorState.from_camera(camera, **viewing_params)`.

```python
from unav_core.navigation import NavigatorState, Vec3
state = NavigatorState(position=Vec3.of(0, 0, 0), far_distance=200, cone_angle_degrees=40)
state2 = NavigatorState.model_validate(state.model_dump())   # round-trips
```

## `Camera`

A live, mutable pose with an orthonormal `forward`/`right`/`up` basis.

| Method | Effect |
| --- | --- |
| `look_at(target, up_hint=None)` | Aim `forward` at a `Vec3` or object with `x/y/z`. |
| `move_forward(d)` / `move_right(d)` / `move_up(d)` | Translate along the basis. |
| `orbit_target(target, yaw, pitch)` | Orbit around a point (about up, then right), preserving distance. |
| `focus_object(target, distance=None)` | Aim at the target; if `distance` given, sit that far away along the view. |

`look_at` / `focus_object` / `orbit_target` accept either a `Vec3` or anything
with `x/y/z` (e.g. a `CatalogObject`), so you can focus an object directly
without importing the data layer into the camera.

```python
from unav_core.navigation import Camera, Vec3
cam = Camera(position=Vec3.of(0, 0, 10), forward=Vec3.of(0, 0, -1))
cam.orbit_target(Vec3.of(0, 0, 0), yaw_degrees=90, pitch_degrees=0)  # -> at (10, 0, 0)
cam.focus_object(Vec3.of(0, 0, 0), distance=5)                       # -> at (0, 0, 5)
```

The camera is pure geometry (no DB, no Astropy); `NavigatorState` bridges to it.
