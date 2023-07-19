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
    num_octaves = 4
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
        
        
def generate_procedural_texture(texture_size):
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


def create_large_textured_sphere(texture):
    bpy.context.scene.cursor.location = (0, 0, 0)
    # Add a new UV sphere mesh with 256 slices
    bpy.ops.mesh.primitive_uv_sphere_add(segments=256, ring_count=256)

    # Get the newly created sphere object
    sphere = bpy.context.active_object

    # Add a new material to the sphere
    mat = bpy.data.materials.new(name="SphereMaterial")
    sphere.data.materials.append(mat)

    # Assign the texture to the material
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    links.clear()
    
    # Height map
    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.image = texture
    
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
    
    diffuse_node = nodes.new(type='ShaderNodeBsdfDiffuse')
    
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    
    links.new(tex_node.outputs['Color'], color_ramp_node.inputs['Fac'])
    links.new(color_ramp_node.outputs['Color'], diffuse_node.inputs['Color'])
    links.new(diffuse_node.outputs['BSDF'], output_node.inputs['Surface'])

    # Assign the material to the sphere
    sphere.data.materials[0] = mat

if __name__ == "__main__":
    purge_all()
    texture = generate_procedural_texture(256)
    create_large_textured_sphere(texture)