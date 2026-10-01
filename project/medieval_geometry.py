"""Stylized medieval kit. Y-up, metres; geometry and material groups are deterministic.

Embedded with the design and detail modules into V006's Python SOP by the builder.
"""
import hashlib
import json
import math
import random
import hou
import copy
if 'resolve_spec' not in globals():
    from medieval_design import resolve_spec, DEFAULT_SPEC, OPTIONS

PALETTES = {
    "oxblood": {"plaster": (.79, .71, .56), "roof": (.38, .105, .08), "shutter": (.26, .34, .25)},
    "slate": {"plaster": (.82, .80, .68), "roof": (.17, .27, .34), "shutter": (.38, .22, .13)},
    "moss": {"plaster": (.73, .65, .47), "roof": (.23, .31, .19), "shutter": (.35, .21, .13)},
}

def material_colors(spec):
    colors = dict(PALETTES[spec["palette"]])
    colors.update(wood=(.22, .115, .058), wood_light=(.40, .245, .12), stone=(.43, .43, .37), stone_light=(.54, .53, .45), iron=(.10, .115, .105), glass=(.12, .18, .17), glow=(.95, .61, .20), brass=(.65, .43, .12), foliage=(.23, .34, .14), cloth=(.75, .63, .39))
    colors['roof_light'] = tuple(min(1, c * 1.16) for c in colors['roof'])
    colors['roof_dark'] = tuple(c * .84 for c in colors['roof'])
    colors.update(terracotta=(.61,.26,.13),fruit=(.68,.15,.08),produce=(.56,.64,.18),cream=(.91,.83,.61),banner=(.30,.13,.22))
    return colors

def spec_from_parms(parent):
    spec = copy.deepcopy(DEFAULT_SPEC)
    for name, choices in OPTIONS.items():
        spec[name] = choices[parent.evalParm('md_' + name)]
    spec['seed'] = parent.evalParm('md_seed')
    spec['overrides'] = json.loads(parent.evalParm('md_overrides'))
    return spec

def build_geometry(geo, spec):
    geo.clear()
    sizes = resolve_spec(spec)
    colors = material_colors(spec)
    cd = geo.addAttrib(hou.attribType.Prim, 'Cd', (1., 1., 1.))
    mat = geo.addAttrib(hou.attribType.Prim, 'material_key', '')
    part = geo.addAttrib(hou.attribType.Prim, 'building_part', '')
    geo.addAttrib(hou.attribType.Global, 'design_spec', '')
    geo.setGlobalAttribValue('design_spec', json.dumps(spec))
    groups = {}

    def mesh(vertices, faces, material, label):
        points = []
        for position in vertices:
            p = geo.createPoint()
            p.setPosition(position)
            points.append(p)
        group = groups.setdefault(material, geo.findPrimGroup(material) or geo.createPrimGroup(material))
        for face in faces:
            prim = geo.createPolygon()
            # Houdini polygons use the reverse winding of conventional OBJ faces.
            for i in reversed(face):
                prim.addVertex(points[i])
            prim.setAttribValue(cd, colors[material])
            prim.setAttribValue(mat, material)
            prim.setAttribValue(part, label)
            group.add(prim)

    def box(c, size, material='wood', label='frame'):
        x, y, z = c
        a, b, d = (v / 2 for v in size)
        v = [(x-a,y-b,z-d),(x+a,y-b,z-d),(x+a,y+b,z-d),(x-a,y+b,z-d),(x-a,y-b,z+d),(x+a,y-b,z+d),(x+a,y+b,z+d),(x-a,y+b,z+d)]
        mesh(v, [(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(0,1,5,4),(3,7,6,2)], material, label)

    def beam(a, b, thickness, material='wood', label='frame'):
        a, b = hou.Vector3(a), hou.Vector3(b)
        axis = (b-a).normalized()
        ref = hou.Vector3((0,1,0)) if abs(axis[1]) < .9 else hou.Vector3((1,0,0))
        u = axis.cross(ref).normalized() * thickness / 2
        v = axis.cross(u).normalized() * thickness / 2
        verts = [tuple(p + u*su + v*sv) for p in (a,b) for su,sv in ((-1,-1),(1,-1),(1,1),(-1,1))]
        mesh(verts, [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)], material, label)

    def cylinder(cx, y, cz, radius, height, material, label, sides=10):
        verts = [(cx+radius*math.cos(i*2*math.pi/sides), yy, cz+radius*math.sin(i*2*math.pi/sides)) for yy in (y,y+height) for i in range(sides)]
        faces = [tuple(range(sides)), tuple(reversed(range(sides,sides*2)))]
        faces += [(i, i+sides, (i+1)%sides+sides, (i+1)%sides) for i in range(sides)]
        mesh(verts, faces, material, label)

    def rng_for(label):
        return random.Random(int.from_bytes(hashlib.sha256((str(spec['seed'])+label).encode()).digest()[:8], 'little'))

    def roof(cx, cz, w, d, eave, rise, label, over=.42):
        hx, hz = w/2+over, d/2+over
        mesh([(cx-hx,eave,cz-hz),(cx+hx,eave,cz-hz),(cx,eave+rise,cz-hz),(cx-hx,eave,cz+hz),(cx+hx,eave,cz+hz),(cx,eave+rise,cz+hz)], [(0,3,5,2),(1,2,5,4)], 'roof_dark', label)
        # Broad overlapping shingles: subordinate texture, stable roof silhouette.
        rows = max(3, round(math.hypot(hx,rise)/.5))
        columns = max(3, round(2*hz/.62))
        rand = rng_for(label)
        for side in (-1,1):
            for row in range(rows):
                t0, t1 = row/rows, min(1,(row+1.07)/rows)
                for col in range(columns):
                    z0 = cz-hz + col*2*hz/columns + .012
                    z1 = cz-hz + (col+1)*2*hz/columns - .012
                    x0, x1 = cx+side*hx*(1-t0), cx+side*hx*(1-t1)
                    y0,y1 = eave+rise*t0+.045, eave+rise*t1+.045
                    vertices=[(x0,y0,z0),(x1,y1,z0),(x1,y1,z1),(x0,y0,z1)]
                    mesh(vertices, [(3,2,1,0)] if side < 0 else [(0,1,2,3)], rand.choices(['roof','roof_light','roof_dark'], [7,2,1])[0], label+'_shingles')
        beam((cx,eave+rise+.055,cz-hz-.04),(cx,eave+rise+.055,cz+hz+.04),.16,'roof_dark',label+'_ridge')
        for z in (cz-hz-.025,cz+hz+.025):
            for side in (-1,1):
                beam((cx+side*hx,eave-.04,z),(cx,eave+rise,z),.19,'wood',label+'_fascia')
        for side in (-1,1):
            beam((cx+side*hx,eave-.03,cz-hz),(cx+side*hx,eave-.03,cz+hz),.18,'wood',label+'_eave')

    w,d,levels,fh = (sizes[k] for k in ('width','depth','floors','floor_height'))
    base = .42
    height = base + levels*fh
    rich = spec['detail'] == 'rich'
    decorated = spec['detail'] != 'restrained'
    side = {'left_wing':-1,'right_wing':1}.get(spec['layout'],0)
    wing_w,wing_d = w*.42,d*.70
    wing_x,wing_z = side*(w/2+wing_w/2-.13),d*.14
    wing_h = base + fh*.92

    def facade(cx,cz,bw,bd,floors,floor_h,label,has_door=False, main=False):
        top = base+floors*floor_h
        box((cx,base/2,cz),(bw+.16,base,bd+.16),'stone',label+'_foundation')
        box((cx,(base+top)/2,cz),(bw,top-base,bd),'stone' if spec['purpose'] in ('smithy','watchhouse') else 'plaster',label+'_walls')
        # Four complete elevations; side-facing windows use the same module.
        for facing in ('front','back','left','right'):
            front = facing == 'front'
            length = bw if facing in ('front','back') else bd
            n = max(2,round(length/2.25))
            positions = [(i+.5)*length/n-length/2 for i in range(n)]
            def pos(u,y,out=0):
                if facing == 'front': return (cx+u,y,cz-bd/2-out)
                if facing == 'back': return (cx-u,y,cz+bd/2+out)
                if facing == 'left': return (cx-bw/2-out,y,cz-u)
                return (cx+bw/2+out,y,cz+u)
            def surface_box(u,y,out,sz,matname,tag):
                finalsize = sz if facing in ('front','back') else (sz[2],sz[1],sz[0])
                box(pos(u,y,out),finalsize,matname,tag)
            for floor in range(floors+1):
                beam(pos(-length/2,base+floor*floor_h,.08),pos(length/2,base+floor*floor_h,.08),.18,'wood',label+'_floor_beam')
            for i in range(n+1):
                u = -length/2 + i*length/n
                if has_door and front and abs(u)<.9:
                    start_y = base+floor_h if floors>1 else top
                else:
                    start_y = base
                if start_y < top:
                    beam(pos(u,start_y,.07),pos(u,top,.07),.17,'wood',label+'_post')
            for floor in range(floors):
                for i,u in enumerate(positions):
                    if has_door and front and floor==0 and abs(u)<1.5: continue
                    if main and spec['purpose']=='home' and front and floor==0 and u<0: continue
                    if main and spec['purpose']=='home' and front and floor==0 and u<0: continue
                    if main and side and facing == ('right' if side>0 else 'left') and floor==0: continue
                    if main and spec['layout'] in ('tower','tower_bridge') and facing=='right' and abs(u)<1.25: continue
                    yy = base+floor*floor_h+floor_h*.57
                    ww,wh = min(1.04,length/n*.50),floor_h*.46
                    if spec['purpose']=='watchhouse': ww*=.42;wh*=.85
                    if spec['purpose']=='smithy': ww*=1.16;wh*=.65
                    tag=label+'_window'
                    surface_box(u,yy,.065,(ww,wh,.06),'glass',tag)
                    for du in (-ww/2,ww/2): surface_box(u+du,yy,.13,(.10,wh+.18,.13),'wood',tag+'_frame')
                    for dy in (-wh/2,wh/2): surface_box(u,yy+dy,.14,(ww+.18,.11,.14),'wood',tag+'_frame')
                    surface_box(u,yy,.15,(.055,wh,.07),'wood_light',tag+'_mullion')
                    surface_box(u,yy,.15,(ww,.055,.07),'wood_light',tag+'_mullion')
                    surface_box(u,yy-wh/2-.06,.22,(ww+.30,.13,.38),'stone_light',tag+'_sill')
                    if decorated:
                        for du in (-ww*.75,ww*.75):
                            surface_box(u+du,yy,.15,(ww*.35,wh,.09),'shutter',tag+'_shutters')
                    if rich and floor>0:
                        beam(pos(u-length/n*.38,base+floor*floor_h+.12,.13),pos(u+length/n*.38,base+floor*floor_h+.55,.13),.09,'wood',label+'_brace')
        return top

    facade(0,0,w,d,levels,fh,'main',True,True)
    rise=sizes['roof_height']
    # Plaster-filled gable ends and their timber frame.
    for z in (-d/2,d/2):
        mesh([(-w/2,height,z),(w/2,height,z),(0,height+rise*.94,z)],[(0,2,1)] if z<0 else [(0,1,2)],'plaster','gable_wall')
        beam((0,height,z-.075 if z<0 else z+.075),(0,height+rise*.94,z-.075 if z<0 else z+.075),.19,'wood','gable_kingpost')
        for s in (-1,1):
            beam((s*w*.43,height,z),(0,height+rise*.90,z),.17,'wood','gable_brace')
    roof(0,0,w,d,height,rise,'main_roof',sizes['roof_overhang'])
    if side:
        facade(wing_x,wing_z,wing_w,wing_d,1,fh*.92,'wing')
        wing_rise=min(rise*.62,wing_w*.47)
        for zz in (-wing_d/2,wing_d/2):
            mesh([(wing_x-wing_w/2,wing_h,wing_z+zz),(wing_x+wing_w/2,wing_h,wing_z+zz),(wing_x,wing_h+wing_rise*.94,wing_z+zz)],[(0,2,1)] if zz<0 else [(0,1,2)],'plaster','wing_gable')
        roof(wing_x,wing_z,wing_w,wing_d,wing_h,wing_rise,'wing_roof',.30)

    # One clearly readable public entrance, with an arched door and a roofed porch.
    front=-d/2
    door_h=2.10
    box((0,base+door_h/2,front-.11),(1.32,door_h,.12),'wood_light','door')
    for x in (-.72,.72): box((x,base+door_h/2,front-.16),(.16,door_h+.20,.22),'stone_light','door_jamb')
    for i in range(9):
        a=i*math.pi/9; b=(i+1)*math.pi/9
        beam((.73*math.cos(a),base+door_h+.55*math.sin(a),front-.17),(.73*math.cos(b),base+door_h+.55*math.sin(b),front-.17),.17,'stone_light','door_arch')
    mesh([(-.65,base+door_h,front-.12),(.65,base+door_h,front-.12)]+[(.65*math.cos(i*math.pi/10),base+door_h+.47*math.sin(i*math.pi/10),front-.12) for i in range(1,10)], [tuple(reversed(range(11)))], 'wood_light','door_arch_fill')
    for x in (-.44,-.22,0,.22,.44): beam((x,base+.03,front-.19),(x,base+door_h-.05,front-.19),.022,'wood','door_planks')
    for y in (base+.55,base+1.55): box((0,y,front-.21),(1.22,.08,.055),'iron','door_strap')
    box((.38,base+1.05,front-.25),(.10,.13,.08),'brass','door_handle')
    porch_w=min(3.1,w*.39)
    porch_d=1.65 if spec['purpose']=='inn' else 1.25
    porch_z=front-porch_d/2
    box((0,.30,porch_z),(porch_w+.30,.25,porch_d+.2),'stone','porch_landing')
    for i in range(3):
        box((0,.07*(i+1),front-porch_d-.75+i*.26),(porch_w+.45,.14*(i+1),.32),'stone_light','entry_steps')
    for x in (-porch_w/2,porch_w/2):
        beam((x,.4,front-porch_d+.12),(x,2.85,front-porch_d+.12),.20,'wood','porch_post')
        beam((x,2.22,front-porch_d+.12),(x*.55,2.85,front-porch_d+.12),.13,'wood','porch_brace')
    roof(0,porch_z,porch_w,porch_d,2.85,.83,'porch_roof',.20)
    # A chimney placed off the ridge and away from the entrance silhouette.
    chimney_x=-w*.27
    chimney_top=height+rise*.95+.55
    box((chimney_x,(height+chimney_top)/2,d*.21),(.68,chimney_top-height,.73),'stone','chimney')
    box((chimney_x,chimney_top,d*.21),(.86,.18,.91),'stone_light','chimney_cap')
    box((chimney_x,chimney_top+.10,d*.21),(.47,.035,.52),'iron','chimney_opening')
    if decorated:
        # Signboard and lanterns sit alongside the entrance, keeping the route clear.
        sign_x=-porch_w/2-.62
        beam((sign_x,3.05,front),(sign_x,3.05,front-.85),.10,'iron','sign_bracket')
        box((sign_x,2.59,front-.79),(.80,.63,.13),'wood','signboard')
        mesh([(sign_x-.22,2.59,front-.87),(sign_x,2.83,front-.87),(sign_x+.22,2.59,front-.87),(sign_x,2.35,front-.87)],[(0,1,2,3)],'brass','sign_crest')
        for x in (-1.0,1.0):
            box((x,1.92,front-.3),(.20,.30,.20),'glow','lantern_glass')
            for dy in (-.20,.20): box((x,1.92+dy,front-.3),(.29,.09,.27),'iron','lantern_cap')
        for i in range(2 if spec['purpose']=='inn' else 1):
            x=w*.34+i*.68; z=front-.68
            cylinder(x,.07,z,.30,.73,'wood_light','barrel')
            for y in (.18,.62): cylinder(x,y,z,.31,.055,'iron','barrel_hoop')
        if spec['purpose']=='shop':
            awning_x=w*.30
            box((awning_x,2.25,front-.65),(w*.28,.11,1.25),'cloth','shop_awning')
            box((awning_x,.66,front-.64),(w*.25,1.1,.70),'wood_light','shop_counter')
        if spec['purpose']=='smithy':
            box((w*.30,.52,front-1.05),(.70,.65,.65),'stone','anvil_base')
            box((w*.30,.94,front-1.05),(.96,.20,.42),'iron','anvil')
        if rich or spec['purpose']=='home':
            x=-w*.33; z=front-.48
            box((x,.35,z),(1.1,.55,.55),'wood_light','planter')
            for i in range(5): cylinder(x-.4+i*.2,.58,z,.19,.23+(i%2)*.12,'foliage','plant',6)
    if spec['purpose']=='smithy':
        # Distinct open-air forge, alongside the entry rather than across it.
        forge_x=-w*.32
        box((forge_x,.72,front-.85),(1.65,1.4,1.15),'stone','forge_hearth')
        box((forge_x,1.12,front-1.44),(1.05,.68,.05),'iron','forge_opening')
        box((forge_x,.91,front-1.48),(.70,.14,.06),'glow','forge_coals')
        box((forge_x,2.5,front-.65),(.65,2.3,.65),'stone','forge_flue')
    if spec['purpose'] in ('guildhall','watchhouse'):
        for sign in (-1,1):
            box((sign*w*.32,height-.95,front-.22),(.65,1.65,.08),'cloth' if spec['purpose']=='guildhall' else 'shutter','civic_banner')
            box((sign*w*.32,height-.92,front-.28),(.13,.62,.04),'brass','banner_emblem')

    if spec['layout'] in ('tower','tower_bridge'):
        # Reuse v003 ring-band tower construction and full timber/stone bridge rules.
        from pathlib import Path
        legacy_source=globals().get('LEGACY_PARTS_SOURCE')
        if legacy_source is None:
            legacy_source=Path(__file__).with_name('medieval_legacy_parts.py').read_text(encoding='utf-8')
        tw=max(2.8,w*.32); td=max(3.0,d*.55)
        gap=3.4 if spec['layout']=='tower_bridge' else -.14
        tx=w/2+gap+tw/2; tz=0
        deck=base+fh
        tower_top=max(height+1.15,deck+2.65)
        legacy_colors={'WOOD':(.30,.18,.09),'WOOD_LIGHT':(.42,.28,.15),'WOOD_DARK':(.20,.12,.065),'STONE':(.48,.46,.41),'STONE_LIGHT':(.59,.56,.49),'STONE_DARK':(.39,.38,.35)}
        keys={'WOOD':'wood','WOOD_LIGHT':'wood_light','WOOD_DARK':'wood','STONE':'stone','STONE_LIGHT':'stone_light','STONE_DARK':'stone'}
        def material_for(color):
            if isinstance(color,str): return color
            return keys[min(legacy_colors,key=lambda k:sum((legacy_colors[k][i]-color[i])**2 for i in range(3)))]
        def legacy_face(points,color,label):
            mesh(points,[tuple(range(len(points)))],material_for(color),label)
        def prism(profile,zmin,zmax,color,label):
            pts=[]
            for p in profile:
                if not pts or sum(abs(p[i]-pts[-1][i]) for i in (0,1))>1e-7: pts.append(p)
            if len(pts)>1 and sum(abs(pts[0][i]-pts[-1][i]) for i in (0,1))<1e-7: pts.pop()
            if len(pts)<3: return
            area=sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))
            if abs(area)<1e-8: return
            if area<0: pts.reverse()
            n=len(pts)
            vertices=[(x,y,z) for z in (zmin,zmax) for x,y in pts]
            faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
            mesh(vertices,faces,material_for(color),label)
        env=dict(math=math,hou=hou,tower_x=tx,tower_z=tz,make_point=lambda p:p,add_face=legacy_face,
                 make_box=lambda c,s,col,label:box(c,s,material_for(col),label),make_prism=prism,
                 DECK_THICKNESS=.16,BEAM_HEIGHT=.20,RAIL_HEIGHT=.95,WALL_EMBED=.08,
                 PIER_WIDTH=.28,ARCH_THICKNESS=.24,ARCH_SEGMENTS=20,**legacy_colors)
        exec(legacy_source,env)
        env['add_band'](0,.35,tw/2+.13,td/2+.13,'stone_light','tower_foot')
        env['add_band'](.35,deck,tw/2,td/2,'stone','tower_lower')
        env['add_band'](deck,tower_top,tw/2+.18,td/2+.18,'plaster','tower_upper')
        for y in (deck,tower_top): env['add_band'](y-.12,y+.12,tw/2+.24,td/2+.24,'wood','tower_band')
        for sx in (-1,1):
            for sz in (-1,1):
                beam((tx+sx*(tw/2+.19),deck,tz+sz*(td/2+.19)),(tx+sx*(tw/2+.19),tower_top,tz+sz*(td/2+.19)),.18,'wood','tower_post')
        for yy in (deck*.55,deck+(tower_top-deck)*.55):
            for sz in (-1,1):
                box((tx,yy,sz*(td/2+.205)),(.55,1.0,.055),'glass','tower_window')
                for sx in (-1,1): box((tx+sx*.33,yy,sz*(td/2+.25)),(.12,1.18,.12),'stone_light','tower_window_frame')
        tr=tw*.73
        for z in (-td/2-.18,td/2+.18):
            mesh([(tx-tw/2-.18,tower_top,z),(tx+tw/2+.18,tower_top,z),(tx,tower_top+tr*.94,z)],[(0,2,1)] if z<0 else [(0,1,2)],'plaster','tower_gable')
        roof(tx,tz,tw+.36,td+.36,tower_top,tr,'tower_roof',.28)
        if spec['layout']=='tower_bridge':
            left=w/2; right=tx-tw/2-.18
            env['make_arch_support'](left,right,deck,0,1.55)
            env['make_timber_bridge'](left,right,deck,0,1.55)
            # Closed exterior doors align with the bridge deck; no traversable interiors.
            for xx in (left+.11,right-.10):
                box((xx,deck+1.05,0),(.12,2.1,1.15),'wood_light','bridge_door')
                for zz in (-.66,.66): box((xx,deck+1.10,zz),(.22,2.2,.15),'stone_light','bridge_door_frame')
                box((xx,deck+2.22,0),(.22,.18,1.47),'stone_light','bridge_door_lintel')
    from pathlib import Path
    style_source=globals().get('STYLE_SOURCE')
    if style_source is None:
        style_source=Path(__file__).with_name('medieval_identities.py').read_text(encoding='utf-8')
    style_namespace={}
    exec(style_source,style_namespace)
    style_namespace['apply_identity'](locals())
    # Small paving apron follows the entry rather than covering the whole plot.
    for row in range(4):
        for col in range(5):
            box(((col-2)*.57,.035,front-porch_d-1.0-row*.46),(.53,.07,.42),'stone_light' if (row+col)%3 else 'stone','entry_paving')
    return sizes

def export_obj(geometry, path, spec, coordinate_space='houdini'):
    """Preserve named material slots explicitly; OBJ does not transport primitive Cd."""
    from pathlib import Path
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    colors=material_colors(spec)
    if coordinate_space not in ('houdini','unreal'): raise ValueError('Unknown coordinate space')
    header='# Medieval town kit; Z-up; centimetres; UE-ready' if coordinate_space=='unreal' else '# Medieval town kit; Y-up; metres'
    lines=[header, 'mtllib ' + path.with_suffix('.mtl').name, 'o building_test', 'g building_test']
    points=list(geometry.points())
    index={p.number(): i+1 for i,p in enumerate(points)}
    for p in points:
        x,y,z=p.position()
        position=(x*100,-z*100,y*100) if coordinate_space=='unreal' else (x,y,z)
        lines.append('v %.7f %.7f %.7f' % position)
    previous=None
    uv_index=0
    for prim in sorted(geometry.prims(), key=lambda p: p.attribValue('material_key')):
        material=prim.attribValue('material_key')
        if material!=previous:
            lines.append('usemtl '+material); previous=material
        normal=prim.normal()
        drop=max(range(3),key=lambda axis: abs(normal[axis]))
        axes=[axis for axis in range(3) if axis!=drop]
        face=[]
        for vertex in reversed(prim.vertices()):
            point=vertex.point()
            position=point.position()
            lines.append('vt %.7f %.7f' % (position[axes[0]],position[axes[1]]))
            uv_index+=1
            face.append(str(index[point.number()])+'/'+str(uv_index))
        lines.append('f '+' '.join(face))
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    mtl=[]
    for name,color in colors.items():
        mtl.extend(['newmtl '+name,'Kd %.5f %.5f %.5f' % color,'Ka 0.05 0.05 0.05','Ks 0 0 0','Ns 8',''])
    path.with_suffix('.mtl').write_text('\n'.join(mtl),encoding='utf-8')
