import bpy
import math
import numpy as np
import opensimplex
import random

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
def generate_fractal_map(name, texture_size, num_octaves, base_frequency, base_amplitude, lacunarity, persistence):
    opensimplex.seed(random.randint(1, 1000))
    
    noise_texture = []
    phi_range = np.arange(-math.pi/2, math.pi/2, math.pi/texture_size)
    theta_range = np.arange(0, 2*math.pi, 2*math.pi/texture_size)
    for i, phi in enumerate(phi_range):
        row = []
        print("Generating fractal map ({}): {:.2%}".format(name, float(i)/texture_size), end='\r')
        for theta in theta_range:
            noise_val = 0
            frequency = base_frequency
            amplitude = base_amplitude
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
    return noise_to_image(noise_texture)


def noise_to_image(noise_texture):
    image = bpy.data.images.new(name="ProceduralTexture", width=texture_size, height=texture_size)
    pixels = [channel for row in noise_texture for pixel in row for channel in [pixel, pixel, pixel, 1.0]]  # Grayscale image
    image.pixels = pixels
    image.update()  
    return image


def generate_normal_map(height_map, texture_size):
    bpy.ops.mesh.primitive_plane_add(size=2)
    plane = bpy.context.active_object
    bpy.ops.object.material_slot_add()
    plane.material_slots[0].material = bpy.data.materials.new(name="NormalMaterial")
    
    mat = plane.material_slots[0].material
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    links.clear()
    
    texture_node = nodes.new(type="ShaderNodeTexImage")
    texture_node.image = height_map
    bump_node = nodes.new(type="ShaderNodeBump")
    bsdf_node = nodes.new(type='ShaderNodeBsdfDiffuse')
    output_node = nodes.new(type="ShaderNodeOutputMaterial")
    
    links.new(texture_node.outputs["Color"], bump_node.inputs["Normal"])
    links.new(bump_node.outputs["Normal"], output_node.inputs["Displacement"])
    links.new(bsdf_node.outputs["BSDF"], output_node.inputs["Surface"])
    
    baked_normal_node = nodes.new(type="ShaderNodeTexImage")
    baked_normal_node.image = bpy.data.images.new("BakedNormal", width=texture_size, height=texture_size)
    baked_normal_node.select = True
    nodes.active = baked_normal_node
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.bake(type="NORMAL")
    bpy.data.objects.remove(plane)
    
    return baked_normal_node.image
    

def generate_final_material(height_map, humidity_map, normal_map, cloud_map, sea_level):
    mat = bpy.data.materials.new(name="SphereMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    links.clear()
    
    # Height map
    height_map_node = nodes.new(type='ShaderNodeTexImage')
    height_map_node.image = height_map

    height_color_ramp_node = nodes.new(type='ShaderNodeValToRGB')
    height_color_ramp_node.color_ramp.interpolation = 'EASE'
    height_color_ramp_node.color_ramp.elements.new(0.1)
    height_color_ramp_node.color_ramp.elements.new(0.15)
    height_color_ramp_node.color_ramp.elements.new(0.75)
    height_color_ramp_node.color_ramp.elements.new(0.85)
    height_color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 1.0, 1.0)
    height_color_ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 0.0, 1.0)
    height_color_ramp_node.color_ramp.elements[2].color = (0.0, 1.0, 0.0, 1.0)
    height_color_ramp_node.color_ramp.elements[3].color = (0.5, 0.5, 0.5, 1.0)
    height_color_ramp_node.color_ramp.elements[4].color = (1.0, 1.0, 1.0, 1.0)
    height_color_ramp_node.color_ramp.elements[5].color = (1.0, 1.0, 1.0, 1.0)

    # Humidity map
    humidity_map_node = nodes.new(type='ShaderNodeTexImage')
    humidity_map_node.image = humidity_map

    humidity_color_ramp_node = nodes.new(type='ShaderNodeValToRGB')
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
    cloud_map_node.image = cloud_map
    
    cloud_color_ramp_node = nodes.new(type='ShaderNodeValToRGB')
    cloud_color_ramp_node.color_ramp.interpolation = 'EASE'
    cloud_color_ramp_node.color_ramp.elements.new(0.5)
    cloud_color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 0.0)
    cloud_color_ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    cloud_color_ramp_node.color_ramp.elements[2].color = (1.0, 1.0, 1.0, 1.0)
    
    cloud_mixer = nodes.new(type='ShaderNodeMixRGB')
    
    # Mix height and elevation
    sea_filter_node = nodes.new(type='ShaderNodeMath')
    sea_filter_node.operation = 'GREATER_THAN'
    sea_filter_node.inputs[1].default_value = sea_level
    
    multiply_node = nodes.new(type='ShaderNodeMath')
    multiply_node.operation = 'MULTIPLY'
    
    mixrgb_node = nodes.new(type='ShaderNodeMixRGB')

    # Normal map
    normal_map_node = nodes.new(type='ShaderNodeTexImage')
    normal_map_node.image = normal_map
    
    normal_node = nodes.new(type='ShaderNodeNormalMap')
    
    bsdf_node = nodes.new(type='ShaderNodeBsdfDiffuse')
    
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Height map path
    links.new(height_map_node.outputs['Color'], height_color_ramp_node.inputs['Fac'])
    links.new(height_map_node.outputs['Color'], sea_filter_node.inputs['Value'])
    links.new(sea_filter_node.outputs['Value'], multiply_node.inputs[0])
    links.new(height_color_ramp_node.outputs['Color'], mixrgb_node.inputs['Color1'])

    # Humidity map path
    links.new(humidity_map_node.outputs['Color'], multiply_node.inputs[1])
    links.new(multiply_node.outputs['Value'], humidity_color_ramp_node.inputs['Fac'])
    links.new(humidity_color_ramp_node.outputs['Color'], mixrgb_node.inputs['Color2'])
    
    # Mix RGB map
    links.new(mixrgb_node.outputs['Color'], cloud_mixer.inputs['Color1'])
    
    # Mix ground and cloud
    links.new(cloud_map_node.outputs['Color'], cloud_color_ramp_node.inputs['Fac'])
    links.new(cloud_color_ramp_node.outputs['Alpha'], cloud_mixer.inputs['Fac'])
    links.new(cloud_color_ramp_node.outputs['Color'], cloud_mixer.inputs['Color2'])
    links.new(cloud_mixer.outputs['Color'], bsdf_node.inputs['Color'])
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
    

if __name__ == "__main__":
    texture_size = 256
    sea_level = 0.15

    height_num_octaves = 8
    height_frequency = 1
    height_amplitude = 1
    height_lacunarity = 2
    height_persistence = 0.5

    humidity_num_octaves = 1
    humidity_frequency = 1
    humidity_amplitude = 1
    humidity_lacunarity = 2
    humidity_persistence = 0.5

    cloud_num_octaves = 4
    cloud_frequency = 1
    cloud_amplitude = 1
    cloud_lacunarity = 2
    cloud_persistence = 0.5

    do_purge = True

    if do_purge:
        purge_all()

    bpy.context.scene.render.engine = 'CYCLES'
    height_map = generate_fractal_map(texture_size, height_num_octaves, height_frequency, height_amplitude, height_lacunarity, height_persistence)
    humidity_map = generate_fractal_map(texture_size, humidity_num_octaves, humidity_frequency, humidity_amplitude, humidity_lacunarity, humidity_persistence)
    cloud_map = generate_fractal_map(texture_size, cloud_num_octaves, cloud_frequency, cloud_amplitude, cloud_lacunarity, cloud_persistence)
    normal_map = generate_normal_map(height_map, texture_size)

    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    mat = generate_final_material(height_map, humidity_map, normal_map, cloud_map, sea_level)
    generate_final_sphere(256, mat)