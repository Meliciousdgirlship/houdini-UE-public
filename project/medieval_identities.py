"""Per-purpose silhouettes and handmade exterior props for the v006 collection."""
import math

def apply_identity(c):
    box,beam,mesh,cylinder,roof=[c[k] for k in ('box','beam','mesh','cylinder','roof')]
    w,d,fh,height,base,front,rise=[c[k] for k in ('w','d','fh','height','base','front','rise')]
    purpose=c['spec']['purpose'];rich=c['rich'];decorated=c['decorated']
    def pot(x,z,scale=1,flowers=True):
        cylinder(x,0,z,.27*scale,.40*scale,'terracotta','pot')
        cylinder(x,.35*scale,z,.32*scale,.10*scale,'terracotta','pot_rim')
        if flowers:
            for i in range(5):
                angle=i*math.tau/5
                px=x+math.cos(angle)*.17*scale;pz=z+math.sin(angle)*.17*scale
                beam((px,.4*scale,pz),(px,.76*scale,pz),.04*scale,'foliage','flower_stem')
                cylinder(px,.74*scale,pz,.09*scale,.08*scale,'cream' if i%2 else 'fruit','flower',6)
    def crate(x,y,z,s=.7):
        box((x,y+s/2,z),(s,s,s),'wood_light','crate')
        for zz in (-s/2-.025,s/2+.025):
            beam((x-s*.44,y+.06,z+zz),(x+s*.44,y+s-.06,z+zz),.07,'wood','crate_brace')
        for yy in (.08,s-.08): box((x,y+yy,z),(s+.06,.08,s+.06),'wood','crate_band')
    def shield(x,y,z):
        vertices=[(x-.34,y+.4,z),(x+.34,y+.4,z),(x+.30,y-.08,z),(x,y-.46,z),(x-.30,y-.08,z)]
        mesh(vertices,[tuple(reversed(range(5)))],'banner','shield')
        box((x,y,z-.04),(.10,.63,.06),'brass','shield_device')
    def railing(x,z,width,y):
        box((x,y,z),(width,.17,.95),'wood','balcony_deck')
        for zz in (z-.43,z+.43):
            for i in range(9):
                xx=x-width/2+width*i/8
                beam((xx,y,zz),(xx,y+.87,zz),.08,'wood','balcony_spindle')
            beam((x-width/2,y+.9,zz),(x+width/2,y+.9,zz),.13,'wood_light','balcony_rail')
    if purpose=='inn':
        if c['levels']>1:
            railing(0,front-.65,min(w*.66,6.2),base+fh)
            for x in (-w*.24,w*.24): beam((x,base+fh-1.0,front),(x,base+fh-.1,front-1.05),.16,'wood','balcony_bracket')
        # Tall paired chimney pots and a roof-ridge weather vane.
        for x in (-w*.27-.19,-w*.27+.19): cylinder(x,height+rise*.95+.62,d*.21,.13,.52,'terracotta','chimney_pot')
        if decorated:
            x=-w*.40;z=front-2.1
            cylinder(x,.80,z,.65,.13,'wood_light','tavern_table')
            cylinder(x,.05,z,.12,.75,'wood','table_leg')
            for dx in (-.9,.9):
                box((x+dx,.47,z),(.40,.12,1.2),'wood_light','tavern_bench')
                for dz in (-.43,.43):box((x+dx,.23,z+dz),(.16,.46,.16),'wood','bench_leg')
            for dx in (-.22,.22):cylinder(x+dx,.87,z,.09,.16,'cream','tankard')
            # Hanging mug emblem, visibly different from the generic diamond sign.
            sx=-c['porch_w']/2-.62
            box((sx,2.59,front-.90),(.27,.33,.07),'cream','inn_mug_sign')
            beam((sx+.16,2.66,front-.92),(sx+.28,2.58,front-.92),.06,'brass','mug_handle')
    elif purpose=='home':
        # Projecting low bay window gives the cottage a softer, smaller silhouette.
        x=-w*.36;z=front-.38
        box((x,1.48,z),(1.30,1.22,.65),'wood_light','cottage_bay')
        box((x,1.55,z-.34),(1.02,.76,.05),'glass','bay_glass')
        for dx in (-.35,0,.35):box((x+dx,1.55,z-.39),(.055,.85,.08),'cream','bay_mullion')
        roof(x,z,1.55,.88,2.18,.53,'bay_roof',.14)
        if decorated:
            for x,z in ((w*.38,front-.6),(w*.43,front-1.45),(-w*.40,front-1.65)):pot(x,z)
            # Short picket fence at one edge, never across the front door.
            x=w/2+.6
            for i in range(8):
                z=front-2.1+i*.47
                box((x,.45,z),(.10,.90,.13),'cream','picket')
                mesh([(x-.07,.9,z-.08),(x+.07,.9,z-.08),(x,1.05,z-.08)],[(0,1,2)],'cream','picket_tip')
            for yy in (.26,.64):beam((x,yy,front-2.1),(x,yy,front+1.2),.07,'wood_light','fence_rail')
            beam((-w*.33,1.1,front-1.25),(-w*.43,2.45,front-.15),.07,'wood','broom_handle')
            box((-w*.33,.95,front-1.25),(.36,.35,.12),'cloth','broom_head')
    elif purpose=='shop':
        # Long striped street canopy and goods create a distinctly commercial frontage.
        x=w*.30;span=w*.38;z=front-1.05
        for i in range(8):
            xa=x-span/2+i*span/8;xb=xa+span/8
            mesh([(xa,2.62,front-.08),(xb,2.62,front-.08),(xb,2.16,front-1.65),(xa,2.16,front-1.65)],[(3,2,1,0)],'cream' if i%2 else 'banner','striped_awning')
            box(((xa+xb)/2,2.04,front-1.65),(span/8,.26,.06),'cream' if i%2 else 'banner','awning_valance')
        for xx in (x-span/2,x+span/2):beam((xx,.05,front-1.65),(xx,2.18,front-1.65),.09,'wood','stall_post')
        box((x,.92,z),(span,.17,.75),'wood_light','market_table')
        for i in range(3):
            xx=x-span*.32+i*span*.32
            box((xx,1.08,z),(span*.27,.18,.63),'wood','produce_tray')
            for j in range(6):cylinder(xx+(j%3-1)*.13,1.18,z+(j//3-.5)*.22,.09,.12,'fruit' if i%2 else 'produce','market_goods',7)
        if decorated:
            for i in range(3):crate(-w*.35+(i%2)*.72,(i//2)*.68,front-1.18,.64)
            beam((-w*.37,1.0,front-2.25),(-w*.37,.1,front-2.7),.09,'wood','price_board_leg')
            box((-w*.37,.75,front-2.35),(.65,.90,.10),'iron','price_board')
            for yy in (.55,.75,.95):box((-w*.37,yy,front-2.42),(.43,.035,.03),'cream','chalk_lines')
    elif purpose=='smithy':
        # Wide lean-to work shelter and stockyard balance the low stone main mass.
        x=w*.36;span=w*.42
        for xx in (x-span/2,x+span/2):beam((xx,.05,front-2.25),(xx,2.6,front-2.25),.20,'wood','forge_shelter_post')
        mesh([(x-span/2-.2,3.10,front),(x+span/2+.2,3.10,front),(x+span/2+.2,2.60,front-2.5),(x-span/2-.2,2.60,front-2.5)],[(3,2,1,0)],'roof_dark','forge_lean_to')
        for xx in (x-span/2,x+span/2):beam((xx,2.6,front-2.25),(xx,3.1,front),.18,'wood','shelter_rafter')
        if decorated:
            box((x,.83,front-1.9),(1.6,.18,.65),'wood_light','workbench')
            for dx in (-.60,.60):box((x+dx,.42,front-1.9),(.18,.84,.50),'wood','workbench_leg')
            for i in range(4):box((x-.5+i*.3,.98,front-1.9),(.22,.16,.40),'iron','ingot')
            beam((x+.15,1.09,front-1.8),(x+.63,1.09,front-1.8),.07,'wood','hammer_handle')
            box((x+.12,1.1,front-1.8),(.20,.18,.25),'iron','hammer_head')
            for i in range(5):beam((w/2+.4+i*.13,.1,front+.5),(w/2+.8+i*.13,1.65,front+1.1),.09,'iron','metal_stock')
            cylinder(-w*.43,0,front-1.7,.40,.55,'iron','quench_tub')
            cylinder(-w*.43,.53,front-1.7,.35,.015,'glass','water')
    elif purpose=='guildhall':
        # Central roof lantern, ceremonial pediment and carved column bases.
        y=height+rise;z=d*.08
        box((0,y+.38,z),(1.15,.88,1.15),'wood','bell_lantern')
        for xx in (-.42,.42):box((xx,y+.45,z-.59),(.13,.65,.10),'brass','lantern_column')
        box((0,y+.45,z-.61),(.55,.58,.035),'iron','bell_opening')
        cylinder(0,y+.21,z-.65,.20,.30,'brass','bell')
        roof(0,z,1.6,1.6,y+.87,.93,'lantern_cap',.12)
        for xx in (-c['porch_w']/2,c['porch_w']/2):
            box((xx,.65,front-1.1),(.48,1.3,.48),'stone_light','ceremonial_column_base')
        shield(0,height+.65,front-.18)
        if decorated:
            for xx in (-w*.40,w*.40):
                cylinder(xx,0,front-1.1,.48,.48,'stone_light','ceremonial_planter')
                cylinder(xx,.48,front-1.1,.37,1.05,'foliage','topiary',8)
            for i in range(4):box((0,.045,front-2.2-i*.5),(1.65,.035,.48),'banner','ceremonial_runner')
    elif purpose=='watchhouse':
        # Stone corner buttresses, barred slit windows and tower crown.
        for xx in (-w/2-.1,w/2+.1):
            for zz in (-d/2,d/2):box((xx,height*.42,zz),(.50,height*.84,.64),'stone_light','buttress')
        if 'tx' in c:
            tx,td,tw,top=[c[k] for k in ('tx','td','tw','tower_top')]
            for xx in (-1,1):
                for i in range(5):box((tx+xx*(tw/2+.28),top+.3,-td/2+i*td/4),(.42,.75,.40),'stone_light','tower_merlon')
            for zz in (-1,1):
                for i in range(1,4):box((tx-tw/2+i*tw/4,top+.3,zz*(td/2+.28)),(.40,.75,.42),'stone_light','tower_merlon')
        shield(0,2.6,front-.38)
        # Essential guard props remain visible even with restrained decoration.
        x=-w*.33;z=front-1.05
        for dx in (-.6,.6):beam((x+dx,0,z),(x+dx,1.5,z),.12,'wood','weapon_rack')
        beam((x-.68,1.18,z),(x+.68,1.18,z),.12,'wood','rack_crossbar')
        for i in range(4):
            xx=x-.45+i*.3
            beam((xx,.08,z-.15),(xx,2.13,z-.15),.055,'wood_light','spear_shaft')
            mesh([(xx-.10,2.10,z-.16),(xx+.10,2.10,z-.16),(xx,2.45,z-.16)],[(0,1,2)],'iron','spear_tip')
        cylinder(w*.34,0,front-1.0,.15,.65,'stone','brazier_stand')
        cylinder(w*.34,.65,front-1.0,.34,.26,'iron','brazier')
        cylinder(w*.34,.91,front-1.0,.25,.12,'glow','brazier_coals')
