bl_info = {
    "name": "Dust Speck",
    "blender": (3, 4, 1),
    "category": "3D View",
    "location": "View3D > Menu > View > Sidebar",
    "description": "Procedural planet generation tool",
    "author": "Jean-Louis Voiseux",
    "version": (1, 0, 0),
}

import bpy
import math
import numpy as np
import random
from enum import Enum, auto

try:
    import opensimplex
    print("OpenSimplex is available - using Simplex noise")
except ImportError:
    raise RuntimeError("Opensimplex is required to use Dust Speck")


# Core generation logic
def purge_all():
    ob = [o for o in bpy.data.objects]
    while ob:
        bpy.data.objects.remove(ob.pop())
        
    mesh = [m for m in bpy.data.meshes]
    while mesh:
        bpy.data.meshes.remove(mesh.pop())
        
    mat = [m for m in bpy.data.materials]
    while mat:
        bpy.data.materials.remove(mat.pop())

    def purge_node_groups():   
        node_group = [g for g in bpy.data.node_groups]
        while node_group:
            bpy.data.node_groups.remove(node_group.pop())
        if [g for g in bpy.data.node_groups]: purge_node_groups()
    purge_node_groups()
        
    tex = [t for t in bpy.data.textures]
    while tex:
        bpy.data.textures.remove(tex.pop())

    img = [i for i in bpy.data.images]
    while img:
        bpy.data.images.remove(img.pop())

    cam = [c for c in bpy.data.cameras]
    while cam :
        bpy.data.cameras.remove(cam.pop())
        

# Vectorization using opensimplex.noise2array seems to worsen performance
# Turns out that sometimes a triple for loop is preferable to multiple operations on
# very large matrices
def generate_fractal_map(name, texture_size, num_octaves, basds_e_frequency, basds_e_amplitude, lacunarity, persistence):
    opensimplex.seed(random.randint(1, 1000))
    
    noise_texture = []
    phi_range = np.arange(-math.pi/2, math.pi/2, math.pi/texture_size)
    theta_range = np.arange(0, 2*math.pi, 2*math.pi/texture_size)
    for i, phi in enumerate(phi_range):
        row = []
        print("Generating fractal map ({}): {:.2%}".format(name, float(i)/texture_size), end='\r')
        for theta in theta_range:
            noise_val = 0
            frequency = basds_e_frequency
            amplitude = basds_e_amplitude
            x = math.cos(phi)*math.cos(theta)
            y = math.cos(phi)*math.sin(theta)
            z = math.sin(phi)
            for octave in range(0, num_octaves):
                noise_val += amplitude * opensimplex.noise3(frequency * x, frequency * y, frequency * z)
                frequency *= lacunarity
                amplitude *= persistence
            row.append(noise_val)
        noise_texture.append(row)

    print("\n")
    return noise_to_image(noise_texture, texture_size)


def noise_to_image(noise_texture, texture_size):
    image = bpy.data.images.new(name="ProceduralTexture", width=texture_size, height=texture_size)
    pixels = [channel for row in noise_texture for pixel in row for channel in [pixel, pixel, pixel, 1.0]]  # Grayscale image
    image.pixels = pixels
    image.update()  
    return image


def generate_normal_material(): 
    mat = bpy.data.materials.new(name="NormalMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    links.clear()
    
    texture_node = nodes.new(type="ShaderNodeTexImage")
    texture_node.name = "ImageNode"
    bump_node = nodes.new(type="ShaderNodeBump")
    bsdf_node = nodes.new(type='ShaderNodeBsdfDiffuse')
    output_node = nodes.new(type="ShaderNodeOutputMaterial")
    normal_output_node = nodes.new(type="ShaderNodeTexImage")
    normal_output_node.name = "NormalOutput"
    
    links.new(texture_node.outputs["Color"], bump_node.inputs["Normal"])
    links.new(bump_node.outputs["Normal"], output_node.inputs["Displacement"])
    links.new(bsdf_node.outputs["BSDF"], output_node.inputs["Surface"])

    return mat
    

def generate_final_material():
    mat = bpy.data.materials.new(name="SphereMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    links.clear()
    
    # Elevation map
    elevation_map_node = nodes.new(type='ShaderNodeTexImage')
    elevation_map_node.name = 'ElevationNode'
    
    elevation_color_ramp_node = nodes.new(type='ShaderNodeValToRGB')
    elevation_color_ramp_node.name = 'ElevationColorRamp'
    elevation_color_ramp_node.color_ramp.interpolation = 'EASE'
    elevation_color_ramp_node.color_ramp.elements.new(0.1)
    elevation_color_ramp_node.color_ramp.elements.new(0.15)
    elevation_color_ramp_node.color_ramp.elements.new(0.75)
    elevation_color_ramp_node.color_ramp.elements.new(0.85)
    elevation_color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 1.0, 1.0)
    elevation_color_ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 0.0, 1.0)
    elevation_color_ramp_node.color_ramp.elements[2].color = (0.0, 1.0, 0.0, 1.0)
    elevation_color_ramp_node.color_ramp.elements[3].color = (0.5, 0.5, 0.5, 1.0)
    elevation_color_ramp_node.color_ramp.elements[4].color = (1.0, 1.0, 1.0, 1.0)
    elevation_color_ramp_node.color_ramp.elements[5].color = (1.0, 1.0, 1.0, 1.0)

    # Humidity map
    humidity_map_node = nodes.new(type='ShaderNodeTexImage')
    humidity_map_node.name = 'HumidityNode'

    humidity_color_ramp_node = nodes.new(type='ShaderNodeValToRGB')
    humidity_color_ramp_node.name = 'HumidityColorRamp'
    humidity_color_ramp_node.color_ramp.interpolation = 'EASE'
    humidity_color_ramp_node.color_ramp.elements.new(0.1)
    humidity_color_ramp_node.color_ramp.elements.new(0.15)
    humidity_color_ramp_node.color_ramp.elements.new(0.75)
    humidity_color_ramp_node.color_ramp.elements.new(0.85)
    humidity_color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 1.0, 1.0)
    humidity_color_ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 0.0, 1.0)
    humidity_color_ramp_node.color_ramp.elements[2].color = (0.0, 1.0, 0.0, 1.0)
    humidity_color_ramp_node.color_ramp.elements[3].color = (0.5, 0.5, 0.5, 1.0)
    humidity_color_ramp_node.color_ramp.elements[4].color = (1.0, 1.0, 1.0, 1.0)
    humidity_color_ramp_node.color_ramp.elements[5].color = (1.0, 1.0, 1.0, 1.0)
    
    # Cloud map
    cloud_map_node = nodes.new(type='ShaderNodeTexImage')
    cloud_map_node.name = 'CloudNode'
    
    cloud_color_ramp_node = nodes.new(type='ShaderNodeValToRGB')
    cloud_color_ramp_node.name = 'CloudColorRamp'
    cloud_color_ramp_node.color_ramp.interpolation = 'EASE'
    cloud_color_ramp_node.color_ramp.elements.new(0.5)
    cloud_color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 0.0)
    cloud_color_ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    cloud_color_ramp_node.color_ramp.elements[2].color = (1.0, 1.0, 1.0, 1.0)
    
    cloud_mixer = nodes.new(type='ShaderNodeMixRGB')
    cloud_mixer.name = 'CloudMix'
    
    # Mix elevation and humidity
    sea_filter_value_node = nodes.new(type='ShaderNodeValue')
    sea_filter_value_node.name = 'HumiditySeaLevel'
    sea_filter_value_node.outputs['Value'].default_value = 0.15

    sea_filter_node = nodes.new(type='ShaderNodeMath')
    sea_filter_node.name = 'HumidityGt'
    sea_filter_node.operation = 'GREATER_THAN'
    
    multiply_node = nodes.new(type='ShaderNodeMath')
    multiply_node.name = 'HumidityMult' 
    multiply_node.operation = 'MULTIPLY'

    mixrgb_fac_node = nodes.new(type='ShaderNodeValue')
    mixrgb_fac_node.name = 'HumidityMixFac'
    mixrgb_fac_node.outputs['Value'].default_value = 0.5
    
    mixrgb_node = nodes.new(type='ShaderNodeMixRGB')
    mixrgb_node.name = 'HumidityMix' 

    # Normal map
    normal_map_node = nodes.new(type='ShaderNodeTexImage')
    normal_map_node.name = 'NormalNode'
    
    normal_node = nodes.new(type='ShaderNodeNormalMap')
    normal_node.name = 'NormalNodeN'

    # Diffuse output node
    diffuse_output_node = nodes.new(type='ShaderNodeTexImage')
    diffuse_output_node.name = 'DiffuseOutput'
    
    bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf_node.name = 'PlanetBSDF'
    
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.name = 'PlanetOutput'
    
    # Elevation map path
    links.new(elevation_map_node.outputs['Color'], elevation_color_ramp_node.inputs['Fac'])
    links.new(elevation_map_node.outputs['Color'], sea_filter_node.inputs['Value'])
    links.new(elevation_color_ramp_node.outputs['Color'], mixrgb_node.inputs['Color1'])

    # Humidity map path
    links.new(humidity_map_node.outputs['Color'], multiply_node.inputs[1])
    links.new(sea_filter_value_node.outputs['Value'], sea_filter_node.inputs[1])
    links.new(sea_filter_node.outputs['Value'], multiply_node.inputs[0])
    links.new(multiply_node.outputs['Value'], humidity_color_ramp_node.inputs['Fac'])
    links.new(humidity_color_ramp_node.outputs['Color'], mixrgb_node.inputs['Color2'])
    links.new(mixrgb_fac_node.outputs['Value'], mixrgb_node.inputs['Fac'])
    
    # Mix RGB map
    links.new(mixrgb_node.outputs['Color'], cloud_mixer.inputs['Color1'])
    
    # Mix ground and cloud
    links.new(cloud_map_node.outputs['Color'], cloud_color_ramp_node.inputs['Fac'])
    links.new(cloud_color_ramp_node.outputs['Alpha'], cloud_mixer.inputs['Fac'])
    links.new(cloud_color_ramp_node.outputs['Color'], cloud_mixer.inputs['Color2'])
    links.new(cloud_mixer.outputs['Color'], bsdf_node.inputs['Base Color'])
    links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])
    
    # Normal map path
    links.new(normal_map_node.outputs['Color'], normal_node.inputs['Color'])
    links.new(normal_node.outputs['Normal'], bsdf_node.inputs['Normal'])

    return mat

    
def generate_final_sphere(size, mat):
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=size, ring_count=size)
    sphere = bpy.context.active_object
    
    sphere.data.materials.append(mat)
    sphere.data.materials[0] = mat
    return sphere
    

def set_image_texture(mat, node_name, image):
    image_texture_node = next((node for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE' and node.name == node_name), None)
    if image_texture_node:
        image_texture_node.image = image


def bake_mat_to_image(name, mat, target_node, texture_size, bake_type):
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.ops.mesh.primitive_plane_add(size=2)
    plane = bpy.context.active_object
    bpy.ops.object.material_slot_add()
    plane.material_slots[0].material = mat

    nodes = mat.node_tree.nodes
    baked_normal_node = target_node
    baked_normal_node.image = bpy.data.images.new(name, width=texture_size, height=texture_size)
    baked_normal_node.select = True
    nodes.active = baked_normal_node
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.bake(type=bake_type)
    bpy.data.objects.remove(plane)
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.view_layer.objects.active = None
    bpy.context.view_layer.objects.active = bpy.context.scene.ds_global_properties.sphere
    
    return baked_normal_node.image
        

# UI       
class DS_GlobalProperties(bpy.types.PropertyGroup):
    def toggle_elevation_callback(self, context):
        scene = context.scene
        if scene.ds_global_properties.enable_elevation:
            if scene.ds_global_properties.elevation_map != None and scene.ds_global_properties.normal_map != None:
                set_image_texture(scene.ds_global_properties.sphere_material, "ElevationNode", scene.ds_global_properties.elevation_map)
                set_image_texture(scene.ds_global_properties.sphere_material, "NormalNode", scene.ds_global_properties.normal_map)
        else:
            set_image_texture(scene.ds_global_properties.sphere_material, "ElevationNode", None)
            set_image_texture(scene.ds_global_properties.sphere_material, "NormalNode", None)
        
        
    def toggle_humidity_callback(self, context):
        scene = context.scene
        if scene.ds_global_properties.enable_humidity:
            if scene.ds_global_properties.humidity_map != None:
                set_image_texture(scene.ds_global_properties.sphere_material, "HumidityNode", scene.ds_global_properties.humidity_map)
        else:
            set_image_texture(scene.ds_global_properties.sphere_material, "HumidityNode", None)
            
            
    def toggle_cloud_callback(self, context):
        scene = context.scene
        if scene.ds_global_properties.enable_cloud:
            if scene.ds_global_properties.cloud_map != None:
                set_image_texture(scene.ds_global_properties.sphere_material, "CloudNode", scene.ds_global_properties.cloud_map)
        else:
            set_image_texture(scene.ds_global_properties.sphere_material, "CloudNode", None)
        
        
    state: bpy.props.IntProperty(default=0)
    elevation_map: bpy.props.PointerProperty(type=bpy.types.Image)
    humidity_map: bpy.props.PointerProperty(type=bpy.types.Image)
    normal_map: bpy.props.PointerProperty(type=bpy.types.Image)
    cloud_map: bpy.props.PointerProperty(type=bpy.types.Image)
    sphere: bpy.props.PointerProperty(type=bpy.types.Object) 
    sphere_material: bpy.props.PointerProperty(type=bpy.types.Material) 
    sphere_normal_material: bpy.props.PointerProperty(type=bpy.types.Material) 
    
    purge_toggle: bpy.props.BoolProperty(name="Purge", default=True)
    planet_details: bpy.props.IntProperty(name="Planet Segments", default=128, min=4, max=1024)

    enable_elevation: bpy.props.BoolProperty(name="Enable Elevation Map", default=True, update=toggle_elevation_callback)
    e_tex_size: bpy.props.IntProperty(name="Elevation Texture Size", default=128, min=32, max=8196)
    e_num_octaves: bpy.props.IntProperty(name="Elevation Octaves", default=4, min=1, max=16)
    e_frequency: bpy.props.FloatProperty(name="Elevation Frequency", default=1.0, min=0.0, max=10.0)
    e_amplitude: bpy.props.FloatProperty(name="Elevation Amplitude", default=1.0, min=0.0, max=10.0)
    e_lacunarity: bpy.props.FloatProperty(name="Elevation Lacunarity", default=2.0, min=0.0, max=10.0)
    e_persistence: bpy.props.FloatProperty(name="Elevation Persistence", default=0.5, min=0.0, max=1.0)
    
    enable_humidity: bpy.props.BoolProperty(name="Enable Humidity Map", default=True, update=toggle_humidity_callback)
    h_tex_size: bpy.props.IntProperty(name="Humidity Texture Size", default=128, min=32, max=8196)
    h_num_octaves: bpy.props.IntProperty(name="Humidity Octaves", default=1, min=1, max=16)
    h_frequency: bpy.props.FloatProperty(name="Humidity Frequency", default=1.0, min=0.0, max=10.0)
    h_amplitude: bpy.props.FloatProperty(name="Humidity Amplitude", default=1.0, min=0.0, max=10.0)
    h_lacunarity: bpy.props.FloatProperty(name="Humidity Lacunarity", default=2.0, min=0.0, max=10.0)
    h_persistence: bpy.props.FloatProperty(name="Humidity Persistence", default=0.5, min=0.0, max=1.0)

    enable_cloud: bpy.props.BoolProperty(name="Enable Cloud Map", default=True, update=toggle_cloud_callback)
    c_tex_size: bpy.props.IntProperty(name="Cloud Texture Size", default=128, min=32, max=8196)
    c_num_octaves: bpy.props.IntProperty(name="Cloud Octaves", default=2, min=1, max=16)
    c_frequency: bpy.props.FloatProperty(name="Cloud Frequency", default=1.0, min=0.0, max=10.0)
    c_amplitude: bpy.props.FloatProperty(name="Cloud Amplitude", default=1.0, min=0.0, max=10.0)
    c_lacunarity: bpy.props.FloatProperty(name="Cloud Lacunarity", default=2.0, min=0.0, max=10.0)
    c_persistence: bpy.props.FloatProperty(name="Cloud Persistence", default=0.5, min=0.0, max=1.0)

    export_prefix: bpy.props.StringProperty(name="File Name Prefix", default="")
    export_folder: bpy.props.StringProperty(name="Export Folder", default="", subtype='DIR_PATH')


class DS_Panel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_ds_panel"
    bl_label = "Dust Speck Setup - Procedural Planet Generation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Dust Speck"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.label(text="Initialization settings")
        layout.prop(scene.ds_global_properties, "planet_details", text="Planet Segments")
        layout.prop(scene.ds_global_properties, "purge_toggle", text="Purge file")
        layout.operator(DS_Initialize.bl_idname)
        layout.separator()

        if scene.ds_global_properties.state == 1:
            obj = bpy.context.active_object
            if obj and obj.active_material and obj.active_material == context.scene.ds_global_properties.sphere_material:

                # Get relevant mat variables
                tree = obj.active_material.node_tree
                e_color_ramp = None
                h_color_ramp = None
                c_color_ramp = None
                h_sea_level = None
                h_mix_factor = None
                for node in tree.nodes:
                    if node.type == 'VALTORGB':
                        if node.name == "ElevationColorRamp":
                            e_color_ramp = node
                        elif node.name == "HumidityColorRamp":
                            h_color_ramp = node
                        elif node.name == "CloudColorRamp":
                            c_color_ramp = node
                    elif node.type == 'VALUE':
                        if node.name == 'HumiditySeaLevel':
                            h_sea_level = node
                        elif node.name == 'HumidityMixFac':
                            h_mix_factor = node
                
                # Elevation map
                layout.label(text="Elevation Map Settings")
                layout.prop(scene.ds_global_properties, "enable_elevation", text="Enable Elevation Map")
                if scene.ds_global_properties.enable_elevation:
                    # Generation settings
                    if scene.ds_global_properties.elevation_map:
                        layout.label(text="Generate Elevation Map")
                    else:
                        layout.label(text="Generate Elevation Map (current: None)")
                    row0 = layout.row()
                    row0.prop(scene.ds_global_properties, "e_tex_size", text="Texture Size")
                    row0.prop(scene.ds_global_properties, "e_num_octaves", text="Octaves")
                    row0.prop(scene.ds_global_properties, "e_frequency", text="Frequency")
                    row1 = layout.row()
                    row1.prop(scene.ds_global_properties, "e_amplitude", text="Amplitude")
                    row1.prop(scene.ds_global_properties, "e_lacunarity", text="Lacunarity")
                    row1.prop(scene.ds_global_properties, "e_persistence", text="Persistence")
                    layout.operator(DS_GenerateElevation.bl_idname)
                    # Edition settings (those are part of the material and do not need to be registered)
                    if scene.ds_global_properties.elevation_map:
                        layout.label(text="Edit Elevation Map")
                        layout.template_color_ramp(e_color_ramp, "color_ramp", expand=False)
                layout.separator()

                # Humidity
                layout.label(text="Humidity Map Settings")
                layout.prop(scene.ds_global_properties, "enable_humidity", text="Enable Humidity Map")
                if scene.ds_global_properties.enable_humidity:
                    # Generation settings
                    if scene.ds_global_properties.humidity_map:
                        layout.label(text="Generate Humidity Map")
                    else:
                        layout.label(text="Generate Humidity Map (current: None)")
                    row0 = layout.row()
                    row0.prop(scene.ds_global_properties, "h_tex_size", text="Texture Size")
                    row0.prop(scene.ds_global_properties, "h_num_octaves", text="Octaves")
                    row0.prop(scene.ds_global_properties, "h_frequency", text="Frequency")
                    row1 = layout.row()
                    row1.prop(scene.ds_global_properties, "h_amplitude", text="Amplitude")
                    row1.prop(scene.ds_global_properties, "h_lacunarity", text="Lacunarity")
                    row1.prop(scene.ds_global_properties, "h_persistence", text="Persistence")
                    layout.operator(DS_GenerateHumidity.bl_idname)
                    # Edition settings
                    if scene.ds_global_properties.humidity_map:
                        layout.label(text="Edit Humidity Map")
                        layout.template_color_ramp(h_color_ramp, "color_ramp", expand=True)
                        row = layout.row()
                        row.prop(h_sea_level.outputs[0], "default_value", text="Sea Level")
                        row.prop(h_mix_factor.outputs[0], "default_value", text="Mix Factor")
                layout.separator()

                # Cloud
                layout.label(text="Cloud Map Settings")
                layout.prop(scene.ds_global_properties, "enable_cloud", text="Enable Cloud Map")
                if scene.ds_global_properties.enable_cloud:
                    if scene.ds_global_properties.cloud_map:
                        layout.label(text="Generate Cloud Map")
                    else:
                        layout.label(text="Generate Cloud Map (current: None)")
                    row0 = layout.row()
                    row0.prop(scene.ds_global_properties, "c_tex_size", text="Texture Size")
                    row0.prop(scene.ds_global_properties, "c_num_octaves", text="Octaves")
                    row0.prop(scene.ds_global_properties, "c_frequency", text="Frequency")
                    row1 = layout.row()
                    row1.prop(scene.ds_global_properties, "c_amplitude", text="Amplitude")
                    row1.prop(scene.ds_global_properties, "c_lacunarity", text="Lacunarity")
                    row1.prop(scene.ds_global_properties, "c_persistence", text="Persistence")
                    layout.operator(DS_GenerateCloud.bl_idname)
                    if scene.ds_global_properties.cloud_map:
                            layout.label(text="Edit Cloud Map")
                            layout.template_color_ramp(c_color_ramp, "color_ramp", expand=True)
                layout.separator()
                
                # Export
                layout.label(text="Export Settings")
                export_row = layout.row()
                export_row.operator(DS_ExportMaps.bl_idname)
                export_row.prop(scene.ds_global_properties, "export_prefix", text="File Name Prefix")
                layout.prop(scene.ds_global_properties, "export_folder", text="Export Folder")


class DS_Initialize(bpy.types.Operator):
    bl_idname = "object.ds_initialize"
    bl_label = "Initialize Dust Speck"
    
    def execute(self, context):
        if(context.scene.ds_global_properties.purge_toggle):
            purge_all()
        context.scene.ds_global_properties.sphere_material = generate_final_material()
        context.scene.ds_global_properties.sphere_normal_material = generate_normal_material()
        
        if context.scene.ds_global_properties.sphere:
            bpy.data.meshes.remove(context.scene.ds_global_properties.sphere.data, do_unlink=True)
            bpy.data.objects.remove(context.scene.ds_global_properties.sphere, do_unlink=True)
        
        context.scene.ds_global_properties.sphere = generate_final_sphere(context.scene.ds_global_properties.planet_details, context.scene.ds_global_properties.sphere_material)
        
        # Set object mode and viewport shading
        bpy.ops.object.mode_set(mode='OBJECT')
        area = next(area for area in bpy.context.screen.areas if area.type == 'VIEW_3D')
        space = next(space for space in area.spaces if space.type == 'VIEW_3D')
        space.shading.type = 'MATERIAL'
        context.scene.ds_global_properties.state = 1
        return {'FINISHED'}
    


class DS_GenerateElevation(bpy.types.Operator):
    bl_idname = "object.ds_generate_elevation"
    bl_label = "Generate Elevation"
    
    def execute(self, context):
        scene = context.scene
        texture_size = scene.ds_global_properties.e_tex_size
        normal_mat = scene.ds_global_properties.sphere_normal_material
        final_mat = scene.ds_global_properties.sphere_material
        elevation_num_octaves = scene.ds_global_properties.e_num_octaves
        elevation_frequency = scene.ds_global_properties.e_frequency
        elevation_amplitude = scene.ds_global_properties.e_amplitude
        elevation_lacunarity = scene.ds_global_properties.e_lacunarity
        elevation_persistence = scene.ds_global_properties.e_persistence

        scene.ds_global_properties.elevation_map = generate_fractal_map("elevation", texture_size, elevation_num_octaves, elevation_frequency, elevation_amplitude, elevation_lacunarity, elevation_persistence)
        set_image_texture(normal_mat, "ImageNode", scene.ds_global_properties.elevation_map)
        normal_map_output_node = next((node for node in normal_mat.node_tree.nodes if node.name == 'NormalOutput'), None)
        scene.ds_global_properties.normal_map = bake_mat_to_image("NormalMap", normal_mat, normal_map_output_node, scene.ds_global_properties.e_tex_size, 'NORMAL')
        set_image_texture(final_mat, "ElevationNode", scene.ds_global_properties.elevation_map)
        set_image_texture(final_mat, "NormalNode", scene.ds_global_properties.normal_map)
        return {'FINISHED'}
    

class DS_GenerateHumidity(bpy.types.Operator):
    bl_idname = "object.ds_generate_humidity"
    bl_label = "Generate Humidity"
    
    def execute(self, context):
        scene = context.scene
        texture_size = scene.ds_global_properties.h_tex_size
        humidity_num_octaves = scene.ds_global_properties.h_num_octaves
        humidity_frequency = scene.ds_global_properties.h_frequency
        humidity_amplitude = scene.ds_global_properties.h_amplitude
        humidity_lacunarity = scene.ds_global_properties.h_lacunarity
        humidity_persistence = scene.ds_global_properties.h_persistence
        scene.ds_global_properties.humidity_map = generate_fractal_map("humidity", texture_size, humidity_num_octaves, humidity_frequency, humidity_amplitude, humidity_lacunarity, humidity_persistence)
        set_image_texture(scene.ds_global_properties.sphere_material, "HumidityNode", scene.ds_global_properties.humidity_map)
        return {'FINISHED'}


class DS_GenerateCloud(bpy.types.Operator):
    bl_idname = "object.ds_generate_cloud"
    bl_label = "Generate Cloud"
    
    def execute(self, context):
        scene = context.scene
        texture_size = scene.ds_global_properties.c_tex_size
        cloud_num_octaves = scene.ds_global_properties.c_num_octaves
        cloud_frequency = scene.ds_global_properties.c_frequency
        cloud_amplitude = scene.ds_global_properties.c_amplitude
        cloud_lacunarity = scene.ds_global_properties.c_lacunarity
        cloud_persistence = scene.ds_global_properties.c_persistence
        scene.ds_global_properties.cloud_map = generate_fractal_map("cloud", texture_size, cloud_num_octaves, cloud_frequency, cloud_amplitude, cloud_lacunarity, cloud_persistence)
        set_image_texture(scene.ds_global_properties.sphere_material, "CloudNode", scene.ds_global_properties.cloud_map)
        return {'FINISHED'}


class DS_ExportMaps(bpy.types.Operator):
    bl_idname = "object.ds_export_maps"
    bl_label = "Export Maps"

    def execute(self, context):
        scene = context.scene
        export_folder = scene.ds_global_properties.export_folder
        export_prefix = scene.ds_global_properties.export_prefix
        texture_size = scene.ds_global_properties.e_tex_size
        mat = scene.ds_global_properties.sphere_material
        export_folder = scene.ds_global_properties.export_folder
        export_prefix = scene.ds_global_properties.export_prefix
        if scene.ds_global_properties.enable_elevation and scene.ds_global_properties.elevation_map:
            diffuse_output_node = next((node for node in mat.node_tree.nodes if node.name == 'DiffuseOutput'), None)
            normal_output_node = next((node for node in mat.node_tree.nodes if node.name == 'NormalNode'), None)  
            final_mix_node = next((node for node in mat.node_tree.nodes if node.name == 'CloudMix'), None)
            bsdf_node = next((node for node in mat.node_tree.nodes if node.name == 'PlanetBSDF'), None)
            material_output_node = next((node for node in mat.node_tree.nodes if node.name == 'PlanetOutput'), None)

            links = mat.node_tree.links
            links.new(final_mix_node.outputs['Color'], material_output_node.inputs['Surface'])

            bake_mat_to_image("DiffuseMap", mat, diffuse_output_node, scene.ds_global_properties.e_tex_size, 'COMBINED')
            if diffuse_output_node.image:
                output_filepath = f"{export_folder}/{export_prefix}_diffuse_{texture_size}.png"
                diffuse_output_node.image.save_render(filepath=output_filepath)
            if normal_output_node.image:   
                output_filepath = f"{export_folder}/{export_prefix}_normal_{texture_size}.png"
                normal_output_node.image.save_render(filepath=output_filepath)

            links.new(final_mix_node.outputs['Color'], bsdf_node.inputs['Base Color'])
            links.new(bsdf_node.outputs['BSDF'], material_output_node.inputs['Surface'])

        else:
            message = "Please generate an elevation map before attempting to export."
            print(message)
            show_message_box(message)

        return {'FINISHED'}


def register():
    bpy.utils.register_class(DS_GlobalProperties)
    bpy.utils.register_class(DS_Panel)
    bpy.utils.register_class(DS_Initialize)
    bpy.utils.register_class(DS_GenerateElevation)
    bpy.utils.register_class(DS_GenerateHumidity)
    bpy.utils.register_class(DS_GenerateCloud)
    bpy.utils.register_class(DS_ExportMaps)
    
    bpy.types.Scene.ds_global_properties = bpy.props.PointerProperty(type=DS_GlobalProperties)
    
    if bpy.context.scene.ds_global_properties.sphere_material == None:
        bpy.context.scene.ds_global_properties.state = 0


def unregister():
    bpy.utils.unregister_class(DS_GlobalProperties)
    bpy.utils.unregister_class(DS_Initialize)
    bpy.utils.unregister_class(DS_GenerateElevation)
    bpy.utils.unregister_class(DS_GenerateHumidity)
    bpy.utils.unregister_class(DS_GenerateCloud)
    bpy.utils.unregister_class(DS_Panel)
    bpy.utils.unregister_class(DS_ExportMaps)
    
    del bpy.types.Scene.ds_global_properties
    
    
def show_message_box(message = "", title = "Warning", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

    
if __name__ == "__main__":
    register()
