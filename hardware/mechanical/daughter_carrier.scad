// Parametric prototype guide; mm. Reference host top = z0, socket centered x/y0.
// Select "boot", "carrier", or "assembly". Render/print a fit coupon before use.
part = "assembly";
$fn = 48;
tip_z = 0.991; // Samtec MEC1 fully-mated card-tip height above host PCB
pcb_t = 1.57;
module along_y(d,h) { rotate([90,0,0]) cylinder(d=d,h=h,center=true); }
// Daughter body corners are 2 mm radius: quarter-arc points about centre (cx,cz).
function corner(cx,cz,a0) = [for(a=[a0:15:a0+90]) [cx+2*cos(a),cz+2*sin(a)]];

module boot() {
  difference() {
    translate([-21,-6,0]) cube([42,12,16]);
    // Socket body/tails clear; only a guide, never an insertion-depth stop.
    translate([-8.2,-4.9,-.1]) cube([16.4,9.8,10.1]);
    translate([-6.2,-1.1,0]) cube([12.4,2.2,16.1]);
    translate([-15.5,-1.1,10]) cube([31,2.2,6.1]);
    // Key slots front and rear (180-degree images): the J1 pinout is mirrored, so a
    // reversed card is allowed. The key still guides the card before contact.
    for(s=[1,-1]) scale([s,s,1]) translate([-12.9,-4.4,-.1]) cube([3.8,2.8,16.2]);
    for(x=[-18,18]) translate([x,0,-.1]) cylinder(d=2.2,h=16.2);
    // M2 nylon clamp screw on whichever side the key sits; thread/tap only the boot wall, not the PCB.
    for(s=[1,-1]) scale([s,s,1]) translate([-11,-5.4,13]) along_y(1.6,2);
  }
}
module carrier() {
  difference() {
    union() {
      translate([-15,-4,20]) cube([30,2,15]);
      // Key leads the electrical tongue by 0.5 mm, remaining clear of host PCB.
      translate([-12.5,-4,-.5]) cube([3,2,24.5]);
      for(p=[[-10,23],[10,27]]) translate([p[0],-1.4,p[1]]) along_y(4.5,1.2);
    }
    for(p=[[-10,23],[10,27]]) translate([p[0],-2,p[1]]) along_y(2.2,6);
    // Air/thermal relief behind the IR sensor. Front optical cone is unobstructed.
    translate([0,-3,29]) along_y(10,8);
  }
}
if(part=="boot") boot();
if(part=="carrier") carrier();
if(part=="assembly") {
  color("gray") boot();
  translate([0,0,tip_z]) color("orange") carrier();
  translate([0,0,tip_z]) color([0,0.5,0,0.5]) rotate([90,0,0])
    linear_extrude(height=pcb_t,center=true)
      polygon(concat([[-5.885,0],[5.885,0],[5.885,9],[6.885,10]],
        corner(13,12,270),corner(13,33,0),corner(-13,33,90),corner(-13,12,180),
        [[-6.885,10],[-5.885,9]]));
}
