"""Export and interchange.

Serialises core state — objects, regions, routes, missions and navigation
state — into portable interchange formats for files and for DCC **adapters**.
This is the boundary across which adapters (Cinema 4D, Blender, Houdini, Unreal)
receive data: they consume exported/interchange payloads and never reach into
core astronomy logic directly.
"""
