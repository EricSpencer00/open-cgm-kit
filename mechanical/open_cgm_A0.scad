// SPDX-License-Identifier: CERN-OHL-W-2.0
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
