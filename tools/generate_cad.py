#!/usr/bin/env python3
"""Generate original A0 sensor artwork and watertight mechanical fit prototypes.

No sensor chemistry or clinical performance is implied by CAD generation.
Run from any directory with dependencies in requirements-cad.txt installed.
"""
from __future__ import annotations
import collections
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np
import mapbox_earcut as earcut
from shapely.geometry import Point, Polygon, MultiPolygon, GeometryCollection, box
from shapely.ops import unary_union
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parents[1]
P = json.loads((ROOT / "mechanical/parameters.json").read_text())
# A0 contains manually routed electrode features, not a general autorouter.
# Reject a changed specification instead of silently emitting stale geometry.
EXPECTED_A0_PARAMETERS = 'a3dca002a2ae9fc69cd69ca96797197317090621913baf5b3d609bf1380aa92d'
if hashlib.sha256(json.dumps(P,sort_keys=True,separators=(',',':')).encode()).hexdigest() != EXPECTED_A0_PARAMETERS:
    raise ValueError('Unsupported parameter change: revise and verify the A0 generator/routes together. Edit the standalone OpenSCAD for exploratory mechanical variants.')
OUT = ROOT / "mechanical/generated"
OUT.mkdir(parents=True, exist_ok=True)

def polygons(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, (MultiPolygon, GeometryCollection)):
        return [p for x in g.geoms for p in polygons(x)]
    return []

def rounded(w, h, r, center=(0, 0)):
    x, y = center
    return box(x-w/2+r,y-h/2+r,x+w/2-r,y+h/2-r).buffer(r,quad_segs=24)

def triangulate(g, z, up):
    out = []
    for poly in polygons(g):
        rings = [list(poly.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in poly.interiors]
        flat = np.array([p for r in rings for p in r], dtype=np.float64)
        ends = np.cumsum([len(r) for r in rings], dtype=np.uint32)
        idx = earcut.triangulate_float64(flat, ends).reshape((-1,3))
        for tri in idx:
            q = np.column_stack((flat[tri], np.full(3, z)))
            if (np.cross(q[1]-q[0], q[2]-q[0])[2] > 0) != up:
                q = q[[0,2,1]]
            out.append(q)
    return out

def layered_mesh(layers):
    """Boundary mesh of planar CSG slices, with no internal coincident faces."""
    out=[]
    for i, (lo,hi,g) in enumerate(layers):
        prev = layers[i-1][2] if i else GeometryCollection()
        nxt = layers[i+1][2] if i+1 < len(layers) else GeometryCollection()
        out += triangulate(g.difference(prev),lo,False)
        out += triangulate(g.difference(nxt),hi,True)
        for poly in polygons(g):
            for ring in [poly.exterior,*poly.interiors]:
                coords=list(ring.coords)
                # Shapely ring winding can vary after Boolean operations.
                for a,b in zip(coords,coords[1:]):
                    mid=np.array([(a[0]+b[0])/2,(a[1]+b[1])/2])
                    d=np.array(b)-np.array(a)
                    n=np.array([d[1],-d[0]])
                    probe=mid+n/(np.linalg.norm(n) or 1)*1e-6
                    outward = not g.contains(Point(*probe))
                    q=np.array([[*a,lo],[*b,lo],[*b,hi],[*a,hi]],float)
                    tris=[q[[0,1,2]],q[[0,2,3]]]
                    if not outward: tris=[t[[0,2,1]] for t in tris]
                    out += tris
    return np.array(out)

def weld_and_split_t_junctions(tris):
    # Boolean intersections may add collinear vertices on a layer interface.
    # Split an edge whenever another mesh vertex lies strictly inside it.
    vertices=np.unique(np.round(tris.reshape(-1,3),8),axis=0)
    pending=list(tris)
    result=[]
    while pending:
        t=pending.pop()
        split=False
        for i,j,k in [(0,1,2),(1,2,0),(2,0,1)]:
            a,b=t[i],t[j]; d=b-a; norm=np.dot(d,d)
            if norm < 1e-16: continue
            f=((vertices-a)@d)/norm
            dist=np.linalg.norm(vertices-(a+f[:,None]*d),axis=1)
            hits=np.where((f>1e-7)&(f<1-1e-7)&(dist<1e-7))[0]
            if len(hits):
                p=vertices[hits[0]]
                pending += [np.array([a,p,t[k]]),np.array([p,b,t[k]])]
                split=True
                break
        if not split: result.append(t)
    return np.array(result)

def write_stl(name,tris):
    tris=weld_and_split_t_junctions(tris)
    # Validate exactly the float32 coordinates serialized by binary STL.
    tris=tris.astype(np.float32).astype(np.float64)
    area2=np.linalg.norm(np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]),axis=1)
    tris=tris[area2>1e-7]
    path=OUT/f"{name}.stl"
    with path.open("wb") as f:
        f.write(("Open CGM A0 fit prototype; mm; NOT a validated medical device".encode()+b" "*80)[:80])
        f.write(struct.pack("<I",len(tris)))
        for t in tris:
            n=np.cross(t[1]-t[0],t[2]-t[0]); n/=np.linalg.norm(n)
            f.write(struct.pack("<12fH",*n,*t.flatten(),0))
    return tris

def validate(tris):
    counts=collections.Counter()
    directed=collections.Counter()
    for t in tris:
        vs=[tuple(x) for x in np.round(t,7)]
        for a,b in zip(vs,vs[1:]+vs[:1]):
            counts[tuple(sorted([a,b]))]+=1
            directed[(a,b)]+=1
    bad=sum(v!=2 for v in counts.values())
    inconsistent=sum(directed[(a,b)] != directed[(b,a)] for a,b in counts)
    volume=float(np.sum(np.einsum('ij,ij->i',tris[:,0],np.cross(tris[:,1],tris[:,2])))/6)
    if bad or inconsistent or volume <= 0:
        raise ValueError(f"mesh failed: edges={bad}, winding={inconsistent}, volume={volume}")
    return {"triangles":len(tris),"nonmanifold_edges":bad,"winding_errors":inconsistent,"volume_mm3":round(volume,3),"bounds_mm":[tris.min((0,1)).tolist(),tris.max((0,1)).tolist()]}

def mechanical():
    h=P['housing']; c=(24,21)
    floor=rounded(48,42,7,c)
    holes=unary_union([Point(*xy).buffer(1.4,quad_segs=16) for xy in h['screw_centers']])
    floor=floor.difference(holes)
    outer=Point(*c).buffer(17,quad_segs=48)
    inner=Point(*c).buffer(14.3,quad_segs=48)
    pillars=unary_union([Point(*xy).buffer(3.5,quad_segs=24) for xy in h['screw_centers']])
    # A 1-mm high exit at the floor for a flat test coupon. Supplier fits actual FPC.
    slot=box(24-6.4,21,24+6.4,45)
    ring=outer.difference(inner).union(pillars).difference(holes)
    base=write_stl('base_fit_prototype',layered_mesh([(0,1.6,floor),(1.6,2.6,ring.difference(slot)),(2.6,9.6,ring)]))
    lid_shape=outer.union(pillars).difference(holes)
    lid=write_stl('lid_fit_prototype',layered_mesh([(0,1.6,lid_shape)]))
    coupon=P['coupon']
    outline=Polygon([(0,6),(.75,6),(.75,0),(11.25,0),(11.25,6),(12,6),(12,40),(0,40)])
    coupon_mesh=write_stl('electrode_substrate_envelope',layered_mesh([(0,.125,outline)]))
    return {'base_fit_prototype':base,'lid_fit_prototype':lid,'electrode_substrate_envelope':coupon_mesh}

def dxf_write(path,layers):
    lines=['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC','0','SECTION','2','ENTITIES']
    for layer, geom in layers.items():
        for poly in polygons(geom):
            for ring in [poly.exterior,*poly.interiors]:
                pts=list(ring.coords)[:-1]
                lines+=['0','LWPOLYLINE','8',layer,'90',str(len(pts)),'70','1']
                for x,y in pts: lines+=['10',f'{x:.6f}','20',f'{y:.6f}']
    lines+=['0','ENDSEC','0','EOF']
    path.write_text('\n'.join(lines)+'\n')

def svg_polygon(poly, fill, stroke='none', width=.03):
    chunks=[]
    for p in polygons(poly):
        d=' '.join('M '+' '.join(f'{x:.4f},{40-y:.4f}' for x,y in list(r.coords)[:-1])+' Z' for r in [p.exterior,*p.interiors])
        chunks.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" fill-rule="evenodd"/>')
    return ''.join(chunks)

def electrode():
    from shapely.geometry import LineString
    c=P['coupon']
    outline=Polygon([(0,6),(.75,6),(.75,0),(11.25,0),(11.25,6),(12,6),(12,40),(0,40)])
    layers={'SUBSTRATE':outline}
    traces=[]
    pads=[]
    for n in range(1,21):
        x=1.25+(n-1)*.5
        pad=box(x-.175,.5,x+.175,3.5)
        pads.append(pad)
        layers[f'CONTACT_{n:02d}']=pad
    pts={7:[(4.25,2),(4.25,12),(3.3,16),(3.3,33)],8:[(4.75,2),(4.75,18),(5.5,22),(5.5,33)],14:[(7.75,2),(7.75,16),(8.5,20),(8.5,33)]}
    for n,path in pts.items():
        g=LineString(path).buffer(.1,cap_style=2,join_style=2)
        layers[f'TRACE_{n:02d}']=g; traces.append(g)
    layers['WE_PT']=Point(8.5,33).buffer(.6,quad_segs=48)
    layers['CE_PT']=box(4.8,30,6.2,36)
    layers['RE_AGCL']=box(2.7,31.5,3.9,34.5)
    layers['GOX_REGION']=Point(8.5,33).buffer(.6,quad_segs=48)
    layers['PASSIVATION']=outline.difference(unary_union(pads+[layers['WE_PT'],layers['CE_PT'],layers['RE_AGCL']]))
    layers['TAIL_STIFFENER']=box(.75,0,11.25,5)
    layers['WET_END_BOUNDARY']=box(0,29,12,40)
    dxf_write(ROOT/'hardware/electrode_A0_layers.dxf',layers)
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="12mm" height="40mm" viewBox="0 0 12 40">'
    svg+=svg_polygon(outline,'#f5e8bf','#314347',.05)
    svg+=svg_polygon(unary_union(pads+traces),'#bd923e')
    for key,color in [('WE_PT','#5b6a73'),('CE_PT','#5b6a73'),('RE_AGCL','#e7e8e9')]: svg+=svg_polygon(layers[key],color,'#23363b',.03)
    svg+='<g font-family="sans-serif" font-size=".55" fill="#14292d"><text x=".8" y="35.8">1</text><text x="10.6" y="35.8">20</text><text x="7.9" y="5.4">WE</text><text x="2.7" y="4.8">RE</text><text x="5" y="3.4">CE</text><text x=".8" y="21">A0 / BENCH</text></g></svg>'
    (ROOT/'hardware/electrode_A0.svg').write_text(svg)
    # Native KiCad board for conductor routing review; active metal/chemistry use DXF RFQ layers.
    pcb=['(kicad_pcb (version 20240108) (generator "open-cgm-kit")','(general (thickness 0.125))','(paper "A4")','(layers (0 "F.Cu" signal) (31 "B.Cu" signal) (37 "F.SilkS" user "f.silkscreen") (39 "F.Mask" user) (44 "Edge.Cuts" user))','(setup (pad_to_mask_clearance 0))','(net 0 "") (net 1 "WE1") (net 2 "RE0") (net 3 "CE0")']
    netmap={14:(1,'WE1'),7:(2,'RE0'),8:(3,'CE0')}
    pcb+=['(footprint "OpenCGM:Sensor_A0" (layer "F.Cu") (at 0 0) (attr smd)','(property "Reference" "SENSOR1" (at 6 24 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))']
    for n in range(1,21):
        net=netmap.get(n)
        ns=f'(net {net[0]} "{net[1]}")' if net else ''
        # KiCad's top-view Y axis is downward; match the contact-side SVG/DXF.
        pcb.append(f'(pad "{n}" smd rect (at {1.25+(n-1)*.5} 38) (size 0.35 3) (layers "F.Cu" "F.Mask") {ns})')
    for n,x,y,w,hh,shape in [(14,8.5,33,1.2,1.2,'circle'),(7,3.3,33,1.2,3,'rect'),(8,5.5,33,1.4,6,'rect')]:
        net=netmap[n]
        pcb.append(f'(pad "{n}" smd {shape} (at {x} {40-y}) (size {w} {hh}) (layers "F.Cu" "F.Mask") (net {net[0]} "{net[1]}"))')
    pcb.append(')')
    for n,path in pts.items():
        for a,b in zip(path,path[1:]): pcb.append(f'(segment (start {a[0]} {40-a[1]}) (end {b[0]} {40-b[1]}) (width 0.2) (layer "F.Cu") (net {netmap[n][0]}))')
    coords=list(outline.exterior.coords)
    for a,b in zip(coords,coords[1:]): pcb.append(f'(gr_line (start {a[0]} {40-a[1]}) (end {b[0]} {40-b[1]}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts"))')
    pcb.append(')')
    (ROOT/'hardware/electrode_A0.kicad_pcb').write_text('\n'.join(pcb)+'\n')
    electrode_drawing(layers)
    # Check no electrically separate patterned nets intersect, and all features fit.
    net_shapes=[]
    for n,end in [(7,layers['RE_AGCL']),(8,layers['CE_PT']),(14,layers['WE_PT'])]:
        g=unary_union([layers[f'CONTACT_{n:02d}'],layers[f'TRACE_{n:02d}'],end])
        assert outline.covers(g),f'net {n} outside substrate'
        assert isinstance(g,Polygon),f'net {n} disconnected'
        net_shapes.append((n,g))
    clearances=[]
    for i,(n,g) in enumerate(net_shapes):
        for m,other in net_shapes[i+1:]:
            d=g.distance(other)
            assert d>=.15-1e-6,(n,m,d)
            clearances.append({'pins':[n,m],'min_spacing_mm':round(d,4)})
    return {'connected_nets':[7,8,14],'pad_count':20,'minimum_net_spacing':clearances,'note':'Geometry checks only. No KiCad DRC, electrochemical or FPC mating test performed.'}

def electrode_drawing(layers):
    fig=plt.figure(figsize=(11.69,8.27),facecolor='white')
    ax=fig.add_axes([.06,.16,.38,.72])
    for key,color in [('SUBSTRATE','#f8f0d4'),('TRACE_07','#bd923e'),('TRACE_08','#bd923e'),('TRACE_14','#bd923e'),('WE_PT','#63747c'),('CE_PT','#63747c'),('RE_AGCL','#d6dbe0')]:
        for poly in polygons(layers[key]): ax.add_patch(plt.Polygon(list(poly.exterior.coords),facecolor=color,edgecolor='#4c5e63',linewidth=.5))
    for n in range(1,21):
        for poly in polygons(layers[f'CONTACT_{n:02d}']):ax.add_patch(plt.Polygon(list(poly.exterior.coords),facecolor='#bd923e'))
    def dim(a,b,label,where):
        ax.annotate('',a,b,arrowprops={'arrowstyle':'<->','lw':.8,'color':'#273d42'})
        ax.text(*where,label,fontsize=9,ha='center',va='center',color='#273d42',bbox={'facecolor':'white','edgecolor':'none','pad':1})
    dim((0,42),(12,42),'12.00',(6,42))
    dim((-3,0),(-3,40),'40.00',(-3,20))
    dim((.75,-2),(11.25,-2),'10.50 dry tail',(6,-2))
    ax.plot([0,0],[40,43],color='#7e8c90',lw=.5);ax.plot([12,12],[40,43],color='#7e8c90',lw=.5)
    ax.annotate('',(6,-6),(6,-3.1),arrowprops={'arrowstyle':'->','lw':1})
    ax.text(6,-7,'Insertion toward connector',fontsize=8,ha='center')
    ax.text(.65,4.3,'1',fontsize=9,fontweight='bold');ax.text(10.5,4.3,'20',fontsize=9,fontweight='bold')
    ax.text(-.2,39.3,'Contact-side view\nOrigin at body envelope (0,0)',fontsize=8,va='top')
    ax.set_xlim(-5,17);ax.set_ylim(-8,45);ax.set_aspect('equal');ax.axis('off')
    fig.text(.48,.86,'ELECTRODE AND TERMINATION',fontsize=12,fontweight='bold',color='#183a3d')
    spec=[
        'All coordinates and dimensions are millimeters.',
        'Nominal geometry; tolerances require supplier DFM.',
        '',
        'Pt WE: diameter 1.20; center (8.50, 33.00).',
        'Ag/AgCl RE: 1.20 x 3.00; center (3.30, 33.00).',
        'Pt CE: 1.40 x 6.00; center (5.50, 33.00).',
        'Wet-end boundary: y >= 29.00. Keep tail dry.',
        '',
        '20 pads; 0.50 pitch; 0.35 width; 3.00 exposed length.',
        'Pad centers x = 1.25 + 0.50*(pin - 1), y = 2.00.',
        '20-contact tail width: 10.50; body width: 12.00.',
        'Tail contact length extends y=0.50 to 3.50.',
        'Stiffener region y=0.00 to 5.00; substrate 0.125 proposed.',
        'Mated tail 0.30 incl. stiffener; supplier checks tolerances.',
        '',
        'J5 Molex 5034802000: pin 7 RE0, pin 8 CE0, pin 14 WE1.',
        'All other coupon contacts have no electrical connection.',
        'Pin 1 left with tail below in this contact-side view.',
        'Map against actual connector/board: do not mirror.',
        '',
        'Layer DXF: outline, contacts, routes, Pt, Ag/AgCl, GOx,',
        'passivation and stiffener. Materials/process are RFQ inputs.',
        'Tail-tip rounding and insertion details: supplier to propose.',
        'No process recipe, sterility, insertion or clinical claim.',
    ]
    for i,line in enumerate(spec):fig.text(.48,.82-i*.026,line,fontsize=8.5,color='#344e53')
    fig.text(.06,.95,'OPEN CGM / CUSTOM SENSOR COUPON',fontsize=18,fontweight='bold',color='#183a3d')
    fig.text(.06,.07,'A0 - REQUEST FOR QUOTE / DESIGN REVIEW ONLY     |     2026-10-26     |     Not released for manufacture',fontsize=10,color='#344e53')
    svg_path=ROOT/'hardware/electrode_A0_drawing.svg'
    fig.savefig(svg_path)
    svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines()).rstrip()+'\n')
    fig.savefig(ROOT/'hardware/electrode_A0_drawing.png',dpi=160)
    plt.close(fig)

def write_scad():
    text='''// SPDX-License-Identifier: CERN-OHL-W-2.0
// Open CGM A0 fit prototype. Units: mm. Not a validated wearable or sensor.
// Select part = "base", "lid", "coupon", or "assembly".
part = "assembly";
flange_width=48; flange_height=42; flange_radius=7;
floor_thickness=1.6; outer_diameter=34; inner_diameter=28.6;
wall_height=8; lid_thickness=1.6; screw_spacing=36;
screw_clearance=2.8; screw_boss_diameter=7;
slot_width=12.8; slot_height=1;
$fn=192;
module roundrect(w,h,r){offset(r=r) square([w-2*r,h-2*r],center=true);}
module screws(){for(x=[-screw_spacing/2,screw_spacing/2]) translate([x,0,-1]) cylinder(h=wall_height+floor_thickness+lid_thickness+2,d=screw_clearance);}
module outline(){union(){circle(d=outer_diameter);for(x=[-screw_spacing/2,screw_spacing/2])translate([x,0])circle(d=screw_boss_diameter);}}
module base(){
  difference(){union(){
    linear_extrude(floor_thickness) roundrect(flange_width,flange_height,flange_radius);
    translate([0,0,floor_thickness]) linear_extrude(wall_height) difference(){outline();circle(d=inner_diameter);}
  } screws(); translate([-slot_width/2,0,floor_thickness])cube([slot_width,flange_height,slot_height]);}
}
module lid(){difference(){linear_extrude(lid_thickness)outline();screws();}}
module coupon(){linear_extrude(.125)polygon([[0,6],[.75,6],[.75,0],[11.25,0],[11.25,6],[12,6],[12,40],[0,40]]);}
if(part=="base")base();
if(part=="lid")lid();
if(part=="coupon")coupon();
if(part=="assembly"){color("ivory")base();translate([0,0,14])color("teal")lid();}
'''
    (ROOT/'mechanical/open_cgm_A0.scad').write_text(text)
    pad=rounded(56,50,12).difference(Point(0,0).buffer(5,quad_segs=32))
    dxf_write(OUT/'adhesive_pad_diecut_A0.dxf',{'CUT':pad})
    # 1:1-mm artwork: no assumption about medical adhesive or skin compatibility.
    paths=[]
    for p in polygons(pad):
        d=' '.join('M '+' '.join(f'{x+28:.3f},{25-y:.3f}' for x,y in list(r.coords)[:-1])+' Z' for r in [p.exterior,*p.interiors])
        paths.append(f'<path d="{d}" fill="none" stroke="black" stroke-width="0.1"/>')
    (OUT/'adhesive_pad_diecut_A0.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="56mm" height="50mm" viewBox="0 0 56 50">'+''.join(paths)+'</svg>')

def preview(meshes):
    fig=plt.figure(figsize=(12,7),facecolor='#f0f2ed')
    ax=fig.add_subplot(121,projection='3d',facecolor='#f0f2ed')
    for name,color,offset in [('base_fit_prototype','#e1dfd3',0),('lid_fit_prototype','#286c6c',16)]:
        t=meshes[name].copy();t[:,:,2]+=offset
        ax.add_collection3d(Poly3DCollection(t,facecolors=color,edgecolor='none',alpha=.98))
    ax.set_xlim(0,48);ax.set_ylim(0,42);ax.set_zlim(0,20);ax.set_box_aspect((48,42,25));ax.view_init(30,-55);ax.set_axis_off()
    ax.set_title('ENCLOSURE / FIT PROTOTYPE',loc='left',fontweight='bold',fontsize=12,color='#173739')
    ax2=fig.add_subplot(122,facecolor='#f0f2ed');ax2.set_aspect('equal');ax2.set_xlim(-3,24);ax2.set_ylim(-2,43);ax2.axis('off')
    ax2.add_patch(plt.Polygon([(0,6),(.75,6),(.75,0),(11.25,0),(11.25,6),(12,6),(12,40),(0,40)],facecolor='#eee0b5',edgecolor='#aeb4ad'))
    for n in range(1,21):
        x=1.25+(n-1)*.5;ax2.add_patch(plt.Rectangle((x-.175,.5),.35,3,facecolor='#bd923e'))
    for x,xx,ys in [(4.25,3.3,[12,16]),(4.75,5.5,[18,22]),(7.75,8.5,[16,20])]:ax2.plot([x,x,xx,xx],[2,ys[0],ys[1],33],color='#bd923e',lw=2)
    ax2.add_patch(plt.Circle((8.5,33),.6,color='#52656d'));ax2.add_patch(plt.Rectangle((4.8,30),1.4,6,color='#52656d'));ax2.add_patch(plt.Rectangle((2.7,31.5),1.2,3,facecolor='#dedfe1',edgecolor='#52656d'))
    for txt,xy,xytext in [('Pt working + GOx',(8.5,33),(14,35)),('Ag/AgCl reference',(3.3,33),(14,29)),('Pt counter',(5.5,31),(14,23)),('20-contact dry tail',(6,2),(14,7))]:ax2.annotate(txt,xy,xytext,color='#173739',fontsize=9,arrowprops={'arrowstyle':'-','color':'#667c7a'})
    ax2.set_title('OUR SENSOR / A0 MASK LAYOUT',loc='left',fontweight='bold',fontsize=12,color='#173739')
    fig.text(.06,.95,'OPEN CGM',fontsize=27,fontweight='bold',color='#173739')
    fig.text(.06,.885,'Own sensing element. Open electrochemical readout. Resilient calibration.',fontsize=11,color='#526966')
    fig.text(.06,.055,'A0: CAD + supplier RFQ package. Chemistry, connector fit, and on-body performance remain unvalidated.',fontsize=10,color='#526966')
    fig.subplots_adjust(top=.78,bottom=.12,wspace=.1)
    fig.savefig(OUT/'design_preview.png',dpi=150,facecolor=fig.get_facecolor());plt.close(fig)

def main():
    write_scad(); meshes=mechanical()
    report={'revision':'A0','units':'mm','status':'quote / fit prototype only','meshes':{n:validate(t) for n,t in meshes.items()},'electrode':electrode()}
    (OUT/'geometry_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    preview(meshes)
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
