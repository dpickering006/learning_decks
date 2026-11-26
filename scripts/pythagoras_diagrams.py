"""Original construction diagrams for recognising Pythagoras word problems."""

INK, MUTED = "#183247", "#53687a"
TEAL, ORANGE, BLUE = "#007c78", "#b14c16", "#355fbd"
PALE, WARM = "#e4f5f1", "#fff0df"


def draw_pythagoras(s, v):
    layout = v["layout"]
    if layout == "rotated":
        a,b,c=(450,170),(190,430),(710,430)
        s.triangle([a,b,c])
        s.line([(433,187),(450,204),(467,187)],TEAL,3)
        if v.get("highlight",True):
            s.line([b,c],TEAL,7)
        for xy,label in zip(((270,270),(630,270),(450,483)),v["labels"]):
            s.text(xy,label,32)
        if v.get("vertices"):
            for xy,label in zip(((450,125),(150,445),(750,445)),"ABC"):
                s.text(xy,label,30)
    elif layout == "nonright":
        a,b,c=(180,455),(710,455),(420,170)
        s.triangle([a,b,c])
        for xy,label in zip(((240,280),(610,280),(445,495)),(v["left"],v["right"],v["base"])):
            s.text(xy,label,32)
        if v.get("angle_vertex")=="left":
            s.angle(a,b,c,65,ORANGE)
            s.text((285,417),v["angle"],30,ORANGE)
        else:
            s.angle(c,a,b,50,ORANGE)
            s.text((425,265),v["angle"],30,ORANGE)
    elif layout == "equal-right":
        a,b,c=(250,460),(600,460),(600,110)
        s.triangle([a,b,c]); s.right(*b)
        s.tick(a,b); s.tick(b,c)
        s.text((425,498),v["leg"],32)
        s.text((660,285),v["leg"],32)
        s.text((365,260),v["hyp"],32,TEAL)
        s.angle(a,b,c,55); s.angle(c,a,b,55)
        s.text((350,425),"45°",28,TEAL)
        s.text((568,214),"45°",28,TEAL)
    elif layout == "square":
        a,b,c,d=(280,460),(600,460),(600,140),(280,140)
        s.d.polygon([a,b,c,d],fill=PALE)
        s.line([a,b,c,d,a]); s.line([a,c],TEAL,6); s.right(*b)
        s.text((440,500),v["side"],32)
        s.text((668,300),v["side"],32)
        s.text((398,265),v["diagonal"],32,TEAL)
    elif layout == "rectangle-boundary":
        s.line([(180,180),(710,180),(710,450),(180,450),(180,180)],TEAL,7)
        s.text((445,495),v["width"],32)
        s.text((445,140),v["width"],32)
        s.text((780,315),v["height"],32)
        s.text((110,315),v["height"],32)
        s.right(710,450)
    elif layout == "route":
        west=v.get("west",False)
        a,b,c=((700,450),(200,450),(200,170)) if west else ((200,450),(200,170),(700,170))
        s.triangle([a,b,c],"#f6f9fb")
        s.line([a,b,c],ORANGE,6)
        if v.get("route_focus"):
            s.dashed(a,c,TEAL)
        else:
            s.line([a,c],TEAL,6)
        s.line([(224,b[1]),(224,b[1]+(-24 if west else 24)),(200,b[1]+(-24 if west else 24))],TEAL,3)
        s.text((450,495 if west else 125),v["horizontal"]+" "+v["directions"][0],32,ORANGE)
        s.text((110,310),v["vertical"]+" N",30,ORANGE)
        s.text((490,280 if west else 350),v["diagonal"],32,TEAL)
        s.text((a[0],a[1]+35),"start",24,MUTED)
        s.text((c[0],c[1]-35),"finish",24,MUTED)
        # Arrowheads show the order and direction along the travelled route.
        for p,q in ((a,b),(b,c)):
            dx,dy=q[0]-p[0],q[1]-p[1]
            length=(dx*dx+dy*dy)**.5
            ux,uy=dx/length,dy/length
            x,y=p[0]+dx*.65,p[1]+dy*.65
            s.line([(x-12*ux+7*uy,y-12*uy-7*ux),(x,y),(x-12*ux-7*uy,y-12*uy+7*ux)],ORANGE,3)
    elif layout == "coordinates":
        dx,dy=int(v["horizontal"]),int(v["vertical"])
        a=(260,450); b=(260+dx*35,450-dy*35); foot=(b[0],450)
        for x in range(155,751,35):
            s.line([(x,100),(x,485)],"#e4ebf0",1)
        for y in range(100,486,35):
            s.line([(155,y),(750,y)],"#e4ebf0",1)
        s.dashed(a,foot,ORANGE); s.dashed(foot,b,BLUE)
        s.line([a,b],TEAL,6); s.right(*foot)
        for p in (a,b):
            s.d.ellipse((p[0]-6,p[1]-6,p[0]+6,p[1]+6),fill=TEAL)
        s.text((180,491),v["a"],28)
        s.text((b[0]+90,b[1]-35),v["b"],28)
        s.text(((a[0]+b[0])/2,490),v["horizontal"],30,ORANGE)
        s.text((b[0]+40,(a[1]+b[1])/2),v["vertical"],30,BLUE)
        s.text(((a[0]+b[0])/2-35,(a[1]+b[1])/2-20),v["diagonal"],32,TEAL)
    elif layout == "roof":
        a,b,c,foot=(140,450),(760,450),(450,150),(450,450)
        s.triangle([a,b,c],"#f6f9fb")
        s.d.polygon([a,foot,c],fill=PALE)
        s.line([a,b,c,a]); s.tick(a,c); s.tick(b,c)
        s.dashed(c,foot); s.right(*foot)
        s.text((225,270),v["leg"],30)
        s.text((675,270),v["leg"],30)
        s.text((520,330),v["height"],30,TEAL)
        s.text((295,420),v["half"],30,ORANGE)
        s.line([(140,480),(140,493),(760,493),(760,480)],MUTED,2)
        # White backing separates the whole-base dimension from its guide line.
        s.d.rectangle((365,474,535,512),fill="white")
        s.text((450,493),v["whole"],30)
    elif layout == "rhombus":
        left,top,right,bottom,centre=(200,320),(450,125),(700,320),(450,515),(450,320)
        s.d.polygon([left,top,right,bottom],fill="#f6f9fb")
        s.d.polygon([left,top,centre],fill=PALE)
        s.line([left,top,right,bottom,left])
        s.dashed(left,right); s.dashed(top,bottom)
        s.right(*centre)
        s.line([left,top],TEAL,7)
        for xy,label in (((325,350),"3 cm"),((575,350),"3 cm"),((510,220),"4 cm"),((510,425),"4 cm")):
            s.text(xy,label,30)
        s.text((285,195),"5 cm",32,TEAL)
    elif layout == "cuboid":
        a,b,c,d=(140,440),(580,440),(580,250),(140,250)
        aa,bb,cc,dd=(280,340),(720,340),(720,150),(280,150)
        for p,q in ((a,aa),(aa,bb),(aa,dd)):
            s.dashed(p,q,MUTED)
        for points in ([a,b,c,d,a],[d,dd,cc,c],[b,bb,cc],[dd,aa]):
            s.line(points,MUTED,3)
        s.dashed(a,bb,ORANGE); s.line([bb,cc],BLUE,6); s.line([a,cc],TEAL,6)
        for xy,label,color in (((350,485),"12 cm",INK),((690,415),"9 cm",INK),((790,245),"8 cm",BLUE),((420,417),"15 cm",ORANGE),((415,230),"17 cm",TEAL)):
            s.text(xy,label,30,color)
    elif layout == "parallelogram":
        a,b,c,d=(170,450),(620,450),(740,200),(290,200)
        s.d.polygon([a,b,c,d],fill=PALE)
        s.line([a,b,c,d,a]); s.dashed(a,c,BLUE)
        s.text((400,495),"8 cm",32)
        s.text((170,300),"6 cm",32)
        s.angle(a,b,d,65,ORANGE); s.text((270,410),"60°",30,ORANGE)
        s.text((490,280),"?",32,BLUE)
    else:
        raise ValueError(f"Unknown Pythagoras layout: {layout}")
