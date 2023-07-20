import bpy
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
        
        
def fractalized_opensimplex_noise2(x, y):
    num_octaves = 8
    frequency = 0.05
    amplitude = 1
    lacunarity = 2.0
    persistence = 0.5
    
    n = 0
    for octave in range(0, num_octaves):
        n += amplitude * opensimplex.noise2(frequency * x, frequency * y)
        frequency *= lacunarity
        amplitude *= persistence
    return n
        
        
def generate_height_map(texture_size):
    noise_texture = []
    for i in range(texture_size):
        row = []
        print("Texture generation progress: {:.2%}".format(float(i)/texture_size), end='\r')
        for j in range(texture_size):
            # Generate the noise value at each pixel position
            noise_val = fractalized_opensimplex_noise2(i, j)  # Adjust the frequency as needed
            row.append(noise_val)
        noise_texture.append(row)

    # Create a new image and set the pixels from the noise texture
    image = bpy.data.images.new(name="ProceduralTexture", width=texture_size, height=texture_size)
    pixels = [channel for row in noise_texture for pixel in row for channel in [pixel, pixel, pixel, 1.0]]  # Grayscale image
    image.pixels = pixels
    image.update()  # Pack the image as PNG to make it available in the blend file
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
    

def generate_final_material(height_map, normal_map):
    mat = bpy.data.materials.new(name="SphereMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    links.clear()
    
    # Height map
    height_map_node = nodes.new(type='ShaderNodeTexImage')
    height_map_node.image = height_map
    
    # Normal map
    normal_map_node = nodes.new(type='ShaderNodeTexImage')
    normal_map_node.image = normal_map
    
    normal_node = nodes.new(type='ShaderNodeNormalMap')
    
    color_ramp_node = nodes.new(type='ShaderNodeValToRGB')
    color_ramp_node.color_ramp.interpolation = 'CONSTANT'
    color_ramp_node.color_ramp.elements.new(0.1)
    color_ramp_node.color_ramp.elements.new(0.15)
    color_ramp_node.color_ramp.elements.new(0.75)
    color_ramp_node.color_ramp.elements.new(0.85)
    color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 1.0, 1.0)
    color_ramp_node.color_ramp.elements[1].color = (1.0, 1.0, 0.0, 1.0)
    color_ramp_node.color_ramp.elements[2].color = (0.0, 1.0, 0.0, 1.0)
    color_ramp_node.color_ramp.elements[3].color = (0.5, 0.5, 0.5, 1.0)
    color_ramp_node.color_ramp.elements[4].color = (1.0, 1.0, 1.0, 1.0)
    color_ramp_node.color_ramp.elements[5].color = (1.0, 1.0, 1.0, 1.0)
    
    bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
    
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Height map path
    links.new(height_map_node.outputs['Color'], color_ramp_node.inputs['Fac'])
    links.new(color_ramp_node.outputs['Color'], bsdf_node.inputs['Base Color'])
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
    purge_all()
    bpy.context.scene.render.engine = 'CYCLES'
    maps_size = 2048
    height_map = generate_height_map(maps_size)
    normal_map = generate_normal_map(height_map, maps_size)
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    mat = generate_final_material(height_map, normal_map)
    generate_final_sphere(256, mat)