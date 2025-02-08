# Dust Speck
This project was started upon discovering [Toni Sagristà's blog post on procedural generation of planetary surfaces](https://tonisagrista.com/blog/2021/procedural-planetary-surfaces/).
The outcome is a Blender plugin that allows users to **procedurally generate textured planets**. Random elevation is generated using [simplex noise](https://en.wikipedia.org/wiki/Simplex_noise).
The results can then be exported to any major game engine.

## Screenshots
<img width="1183" alt="Screenshot 2025-02-08 212947" src="https://github.com/user-attachments/assets/c2398de8-759b-40ee-bd21-bd7bfc13a61e" />

<table>
<tr>
<td>
Diffuse map
<img width="512" alt="showcase_diffuse_1024" src="https://github.com/user-attachments/assets/c3e75433-5a2d-4274-af33-d5276fdad70a" />
</td>
<td>
Normal map
<img width="512" alt="showcase_normal_1024" src="https://github.com/user-attachments/assets/f4121bb5-4812-47d2-8423-00e123c75c89" />
</td>
</tr>
</table>

## Install instructions
### Prerequisite : Install [OpenSimplex](https://github.com/lmas/opensimplex)
**Note: OpenSimplex is distributed under a MIT license**

Open Powershell as admin
```
cd "C:\Program Files\Blender Foundation\Blender 4.1\4.1\python\bin"
.\python.exe -m pip install --upgrade pip
.\python.exe -m pip install opensimplex
```

### Known issues
- For exported maps to match the preview, it is advised to enable elevation, humidity and clouds. This will be fixed in a future release.
