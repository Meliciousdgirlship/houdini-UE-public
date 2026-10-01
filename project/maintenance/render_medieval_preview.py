"""Orthographic z-buffer preview of actual OBJ geometry (Pillow + NumPy)."""
from pathlib import Path
import numpy as np
import sys
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parents[1]
obj=Path(sys.argv[1]) if len(sys.argv)>1 else root/'exports/medieval_inn_v006.obj'
colors={}; key=None
for line in obj.with_suffix('.mtl').read_text().splitlines():
    if line.startswith('newmtl '): key=line.split()[1]
    elif line.startswith('Kd '): colors[key]=np.array([float(x) for x in line.split()[1:]])
verts=[]; polys=[]; mats=[]
ue_ready='UE-ready' in obj.read_text().splitlines()[0]
for line in obj.read_text().splitlines():
    if line.startswith('v '):
        x,y,z=map(float,line.split()[1:4]); verts.append([x/100,-y/100,z/100] if ue_ready else [x,z,y])
    elif line.startswith('usemtl '): key=line.split()[1]
    elif line.startswith('f '):
        polys.append(np.array([verts[int(x.split('/')[0])-1] for x in line.split()[1:]])); mats.append(key)
v=np.array(verts); lo=v.min(0); hi=v.max(0)
polys.insert(0,np.array([(lo[0]-1,lo[1]-1,-.06),(hi[0]+1,lo[1]-1,-.06),(hi[0]+1,hi[1]+1,-.06),(lo[0]-1,hi[1]+1,-.06)])); mats.insert(0,'ground'); colors['ground']=np.array([.83,.81,.75])
camera=np.array([1.,-1.9,1.15]); camera/=np.linalg.norm(camera)
right=np.cross([0,0,1],camera); right/=np.linalg.norm(right)
up=np.cross(camera,right); transform=np.stack([right,up,camera],axis=1)
allproj=np.vstack(polys)@transform; mn=allproj.min(0); mx=allproj.max(0)
W,H=1600,1200; scale=min(1400/(mx[0]-mn[0]),850/(mx[1]-mn[1]))
canvas=np.full((H,W,3),[238,233,223],dtype=np.uint8); zbuffer=np.full((H,W),-np.inf)
light=np.array([-.35,-.65,1.]); light/=np.linalg.norm(light)
for poly,material in zip(polys,mats):
    p=poly@transform
    p[:,0]=(p[:,0]-(mn[0]+mx[0])/2)*scale+W/2
    p[:,1]=1020-(p[:,1]-mn[1])*scale
    normal=np.cross(poly[1]-poly[0],poly[2]-poly[0]); normal/=max(np.linalg.norm(normal),1e-8)
    color=(np.clip(colors[material]*(.79+.21*abs(np.dot(normal,light))),0,1)*255).astype(np.uint8)
    for i in range(1,len(p)-1):
        a,b,c=p[[0,i,i+1]]
        x0=max(0,int(np.floor(min(a[0],b[0],c[0])))); x1=min(W-1,int(np.ceil(max(a[0],b[0],c[0]))))
        y0=max(0,int(np.floor(min(a[1],b[1],c[1])))); y1=min(H-1,int(np.ceil(max(a[1],b[1],c[1]))))
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-8 or x0>x1 or y0>y1: continue
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1]; xx=xx+.5; yy=yy+.5
        aa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        bb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den; cc=1-aa-bb
        depth=aa*a[2]+bb*b[2]+cc*c[2]
        mask=(aa>=-1e-6)&(bb>=-1e-6)&(cc>=-1e-6)&(depth>zbuffer[y0:y1+1,x0:x1+1])
        zbuffer[y0:y1+1,x0:x1+1][mask]=depth[mask]; canvas[y0:y1+1,x0:x1+1][mask]=color
image=Image.fromarray(canvas); draw=ImageDraw.Draw(image)
font='C:/Windows/Fonts/arial.ttf'; bold='C:/Windows/Fonts/arialbd.ttf'
title=obj.stem.replace('_',' ').upper() if len(sys.argv)>1 else 'THE GOLDEN STAG'
draw.text((75,50),title,font=ImageFont.truetype(bold,42),fill='#352e26')
draw.text((77,105),'MEDIEVAL TOWN  /  PROCEDURAL BUILDING COLLECTION',font=ImageFont.truetype(font,20),fill='#706454')
draw.text((77,1090),'Warm plaster  /  dark timber  /  modular architecture',font=ImageFont.truetype(font,22),fill='#554b3e')
draw.text((77,1130),'Actual Houdini geometry | Material-color study; not a final UE render',font=ImageFont.truetype(font,17),fill='#807365')
target=obj.with_suffix('.png'); image.save(target); print(target)
