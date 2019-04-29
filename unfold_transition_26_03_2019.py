bl_info = {
    "name": "Unfold Transition",
    "version": (0, 1, 2),
    "blender": (2, 80, 0),
    "location": "Properties Editor > Objects Panel > Unfold Transition",
    "description": "Simple unfold transition / animation, will separate faces and set up an armature",
    "category": "Animation"}

import bpy, random as R, mathutils
from mathutils import geometry as G

bpy.types.WindowManager.modo=bpy.props.EnumProperty(
    name="", items=[("cursor","3D Cursor", "Use the Distance to 3D Cursor"), ("weight","Weight Map",
    "Use a Painted Weight map"),("index","Mesh Indices","Use Faces and Vertices index")], 
    description="How to Sort Bones for animation", default="cursor")
bpy.types.WindowManager.flip = bpy.props.BoolProperty(
    name="Flipping Faces", default=False,
    description="Rotate faces around the Center & skip Scaling - keep checked for both operators")
bpy.types.WindowManager.fold_duration = bpy.props.IntProperty(
    name="Total Time", min=5, soft_min=25, max=10000, soft_max=2500, default=200, 
    description="Total animation length")
bpy.types.WindowManager.sca_time = bpy.props.IntProperty(
    name="Scale Time", min=1, max=5000, soft_max=500, default=10, 
    description="Faces scaling time")
bpy.types.WindowManager.rot_time = bpy.props.IntProperty(
    name="Rotation Time", min=1, soft_min=5, max=5000, soft_max=500, default=15, 
    description="Faces rotation time")
bpy.types.WindowManager.rot_max = bpy.props.IntProperty(
    name="Angle", min=-180, max=180, default=135, 
    description="Faces rotation angle")
bpy.types.WindowManager.fold_noise = bpy.props.IntProperty(
    name="Noise", min=0, max=500, soft_max=50, default=0, 
    description="Offset some faces animation")
bpy.types.WindowManager.bounce = bpy.props.FloatProperty(
    name="Bounce", min=0, max=10, soft_max=2.5, default=0, 
    description="Add some bounce to rotation")
bpy.types.WindowManager.from_point = bpy.props.BoolProperty(
    name="Point", default=False,
    description="Scale faces from a Point instead of from an Edge")
bpy.types.WindowManager.wiggle_rot = bpy.props.BoolProperty(
    name="Wiggle", default=False, 
    description="Use all Axis + Random Rotation instead of X Aligned")


class Set_Up_Fold(bpy.types.Operator):
    bl_idname = "object.set_up_fold"
    bl_label = "Set Up Unfold"
    bl_description = "Set up Faces and Bones for animation"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (bpy.context.object.type == "MESH")

    def execute(self, context):
        bpy.ops.object.mode_set()
        wm = context.window_manager
        scn = bpy.context.scene
        colcn = bpy.context.collection
        vulyr = bpy.context.view_layer
        obj = bpy.context.object
        dat = obj.data
        fac = dat.polygons
        ver = dat.vertices

    # tratar de limpiar rastros de procesados anteriores
    # try to clean traces of previous processed
    
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=True)
        bpy.ops.object.mode_set()
        old_vg = [vg for vg in obj.vertex_groups if vg.name.startswith("bone.")]
        for vg in old_vg: obj.vertex_groups.remove(vg)
        if "UnFold" in obj.modifiers:
            arm = obj.modifiers["UnFold"].object
            rig = arm.data
            try:
                scn.objects.unlink(arm)
                bpy.data.objects.remove(arm)
                bpy.data.armatures.remove(rig)
            except:
                pass
            obj.modifiers.remove(obj.modifiers["UnFold"])

    # obtener secuencia de caras desde el peso de los vertices
    # get sequence of faces from the weight of the vertices
    
        if wm.modo == "weight":
            if len(obj.vertex_groups):
                i = obj.vertex_groups.active.index
                W = []
                for f in fac:
                    v_data = []
                    for v in f.vertices:
                        try:
                            w = ver[v].groups[i].weight
                            v_data.append((w,v))
                        except:
                            v_data.append((0,v))
                    v_data.sort(reverse=True)
                    v1 = ver[v_data[0][1]].co
                    v2 = ver[v_data[1][1]].co
                    cen = mathutils.Vector(f.center)
                    its = G.intersect_point_line(cen, v2, v1)
                    head = v2.lerp(v1, its[1])
                    peso = sum([x[0] for x in v_data])
                    W.append((peso, f.index, cen, head))
                W.sort(reverse=True)
                S = [x[1:] for x in W]
            else:
                self.report({"INFO"}, "First paint a Weight Map for this object")
                return {"FINISHED"}

    # separar caras y ordenar
    # separate faces and order
    
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.edge_split()
        bpy.ops.mesh.select_all(action="SELECT")
        if wm.modo == "cursor":
            bpy.context.tool_settings.mesh_select_mode = [True, True, True]
            bpy.ops.mesh.sort_elements(type="CURSOR_DISTANCE", elements={"VERT","EDGE","FACE"})
        bpy.context.tool_settings.mesh_select_mode = [False, False, True]
        bpy.ops.object.mode_set()

    # obtener secuencia de caras y bordes desde indices de cara / vertice
    # get sequence of faces and edges from face indexes / vertice
    
        if wm.modo != "weight":
            S = []
            for f in fac:
                E = list(f.edge_keys)
                E.sort()
                v1 = ver[E[0][0]].co
                v2 = ver[E[0][1]].co
                cen = mathutils.Vector(f.center)
                its = G.intersect_point_line(cen, v2, v1)
                head = v2.lerp(v1, its[1])
                S.append((f.index, f.center, head))

    # crear esqueleto y modificador
    # create skeleton and modifier
    
        arm = bpy.data.armatures.new("arm")
        rig = bpy.data.objects.new("rig_" + obj.name, arm)
        rig.matrix_world = obj.matrix_world
        #scn.objects.link(rig)
        colcn.objects.link(rig)
        #scn.objects.active = rig
        vulyr.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        #arm.draw_type = "WIRE"
        arm.display_type = "WIRE"
        #rig.show_x_ray = True
        mod = obj.modifiers.new("UnFold", "ARMATURE")
        mod.show_in_editmode = True
        mod.object = rig

    # crear los huesos y vertex groups
    # create the bones and vertex groups
    
        root = arm.edit_bones.new("bone.000")
        root.tail = (0,0,0)
        root.head = (0,0,1)
        root.select = True
        vis = [False, True] + [False] * 30

        for fb in S:
            f = fac[fb[0]]
            b = arm.edit_bones.new("bone.000")
            if wm.flip:
                b.tail, b.head = fb[2], fb[1]
            else:
                b.tail, b.head = fb[1], fb[2]
            b.align_roll(f.normal)
            b.select = False
            b.layers = vis
            b.parent = root
            vg = obj.vertex_groups.new(name = b.name)
            vg.add(f.vertices, 1, "ADD")

        bpy.ops.object.mode_set()
        if wm.modo == "weight":
            obj.vertex_groups.active_index = 0
        #scn.objects.active = rig
        vulyr.objects.active = rig
        #obj.select = False
        rig.select_set(state = False)
        return {"FINISHED"}


class Animate_Fold(bpy.types.Operator):
    bl_idname = "object.animate_fold"
    bl_label = "Animate Unfold"
    bl_description = "Animate bones to simulate unfold... Starts on current frame"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = bpy.context.object
        #return (obj.type == "ARMATURE" and obj.is_visible(bpy.context.scene))
        return (obj.type == "ARMATURE" and obj.visible_get(view_layer = bpy.context.view_layer))

    def execute(self, context):
        obj = bpy.context.object
        scn = bpy.context.scene
        fra = scn.frame_current
        wm = context.window_manager

    # limpiar animacion y obtener lista de huesos
    # Clean animation and get list of bones.
    
        if obj.animation_data: obj.animation_data_clear()
        bpy.ops.object.mode_set(mode="POSE")
        bones = obj.pose.bones[0].children_recursive
        if wm.flip:
            rot = -3.141592
        else:
            rot = wm.rot_max / 57.3
        extra = wm.rot_time * wm.bounce
        ruido = max(wm.rot_time + extra, wm.sca_time) + wm.fold_noise
        vel = (wm.fold_duration - ruido) / len(bones)

    # introducir fotogramas clave de escala y rotacion
    # enter keyframes of scale and rotation
    
        for a, b in enumerate(bones):
            t = fra + a * vel + R.randint(0, wm.fold_noise)
            if wm.flip:
                b.scale = (1, 1, 1)
            elif wm.from_point:
                b.scale = (0, 0, 0)
            else:
                b.scale = (1, 0, 0)
            if not wm.flip:
                b.keyframe_insert("scale", frame = t )
                b.scale = (1, 1, 1)
                b.keyframe_insert("scale", frame = t + wm.sca_time)
            if wm.rot_max:
                b.rotation_mode = "XYZ"
                if wm.wiggle_rot:
                    euler = (R.uniform(-rot,rot), R.uniform(-rot,rot), R.uniform(-rot,rot))
                else:
                    euler = (rot, 0, 0)
                b.rotation_euler = euler
                b.keyframe_insert("rotation_euler", frame = t )
            if wm.bounce:
                val = wm.bounce * -.10
                b.rotation_euler = (val * euler[0], val * euler[1], val * euler[2])
                b.keyframe_insert("rotation_euler", frame = t + wm.rot_time + .25 * extra)
                val = wm.bounce * .05
                b.rotation_euler = (val * euler[0], val * euler[1], val * euler[2])
                b.keyframe_insert("rotation_euler", frame = t + wm.rot_time + .50 * extra )
                val = wm.bounce * -.025
                b.rotation_euler = (val * euler[0], val * euler[1], val * euler[2])
                b.keyframe_insert("rotation_euler", frame = t + wm.rot_time + .75 * extra )
            b.rotation_euler = (0, 0, 0)
            b.keyframe_insert("rotation_euler", frame = t + wm.rot_time + extra )
        return {"FINISHED"}

class PanelFOLD(bpy.types.Panel):
    bl_label = "Unfold Transition"
    bl_idname = "OBJECT_PT_unfold"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout
        column = layout.column()
        column.operator("object.set_up_fold", text="1. Set Up Unfold")
        column.prop(wm, "modo")
        column.prop(wm, "flip")
        layout.separator()
        column = layout.column()
        column.operator("object.animate_fold", text="2. Animate Unfold")
        column.prop(wm, "fold_duration")
        column.prop(wm, "sca_time")
        column.prop(wm, "rot_time")
        column.prop(wm, "rot_max")
        row = column.row(align=True)
        row.prop(wm, "fold_noise")
        row.prop(wm, "bounce")
        row = column.row(align=True)
        row.prop(wm, "wiggle_rot")
        if not wm.flip:
            row.prop(wm, "from_point")
            
def register():
    bpy.utils.register_class(Set_Up_Fold)
    bpy.utils.register_class(Animate_Fold)
    bpy.utils.register_class(PanelFOLD)

def unregister():
    bpy.utils.unregister_class(Set_Up_Fold)
    bpy.utils.unregister_class(Animate_Fold)
    bpy.utils.unregister_class(PanelFOLD)

if __name__ == "__main__":
    register()