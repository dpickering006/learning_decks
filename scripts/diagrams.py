"""Original, phone-readable geometry sketches for questions and explanations.

All labels are drawn with the bundled OFL font so maths glyphs render identically
on the authoring machine and in GitHub Actions. No network access is needed.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = Path(__file__).resolve().parents[1] / "assets/fonts/NotoSans-Regular.ttf"
MATH_FONT = FONT.with_name("NotoSansMath-Regular.ttf")
INK, MUTED = "#183247", "#53687a"
TEAL, ORANGE, BLUE = "#007c78", "#b14c16", "#355fbd"
PALE, WARM = "#e4f5f1", "#fff0df"
DIAGRAMS = {}

for visual_file in sorted((FONT.parents[2] / "visuals").glob("*.json")):
    entries = json.loads(visual_file.read_text())
    if DIAGRAMS.keys() & entries.keys():
        raise ValueError(f"Duplicate diagram keys in {visual_file}")
    DIAGRAMS.update(entries)


@lru_cache(maxsize=None)
def needs_math_font(character):
    """Pillow does not fall back automatically for missing math glyphs."""
    for index, path in enumerate((FONT, MATH_FONT)):
        font = ImageFont.truetype(str(path), 32)
        glyph, missing = font.getmask(character), font.getmask("\uffff")
        if glyph.size != missing.size or bytes(glyph) != bytes(missing):
            return bool(index)
    raise ValueError(f"No bundled font supports {character!r}")


def scene(number, family, title, steps, description, question=None, **values):
    key = f"tri-{number:03d}"
    answer = dict(family=family, title=title, steps=steps, **values)
    answer["alt"] = description + " " + " ".join(steps)
    DIAGRAMS[key + "-answer"] = answer
    if question is not None:
        DIAGRAMS[key + "-question"] = dict(answer, title="Sketch the problem",
            steps=[], alt="Problem diagram; all given measurements are also in the question.",
            **question)


scene(1, "triangle", "Move the angles, keep their sizes",
      ["Parallel lines give matching alternate angles.", "a + b + c = 180° on the straight line."],
      "A line through the top vertex is parallel to the base. Angles a and b appear beside c at the top.",
      angles=("a", "b", "c"), parallel=True)
scene(2, "triangle", "Use the whole 180°",
      ["52° + 67° + ? = 180°", "? = 180° − 119° = 61°"],
      "The two known angles and the missing angle fill the triangle's angle total.",
      angles=("52°", "67°", "61°"), question={"angles": ("52°", "67°", "?")})
scene(3, "triangle", "Equal sides → equal opposite angles",
      ["Each matching side faces a matching angle.", "The two base angles are equal."],
      "Matching ticks mark the sloping sides. Matching a labels mark the angles opposite them.",
      angles=("a", "a", ""), ticks=True)
scene(4, "triangle", "Share the remaining angle equally",
      ["180° − 40° = 140°", "Each base angle = 140° ÷ 2 = 70°"],
      "The equal sloping sides face equal base angles of 70 degrees.",
      angles=("70°", "70°", "40°"), ticks=True,
      question={"angles": ("?", "?", "40°")})
scene(5, "triangle", "Compare two ways to make 180°",
      ["a + b + c = 180°     and     e + c = 180°", "Subtract c from both: e = a + b."],
      "The base extends past the right vertex. Exterior angle e sits next to interior angle c.",
      angles=("a", "c", "b"), exterior="e")
scene(6, "triangle", "The exterior angle combines two angles",
      ["47° + ? = 118°", "? = 118° − 47° = 71°"],
      "Exterior angle 118 degrees equals the opposite interior angles 47 and 71 degrees.",
      angles=("47°", "", "71°"), exterior="118°",
      question={"angles": ("47°", "", "?")})
scene(7, "triangle", "Three equal sides, three equal angles",
      ["a + a + a = 180°", "a = 180° ÷ 3 = 60°"],
      "All three sides have matching ticks; all three angles are 60 degrees.",
      angles=("60°", "60°", "60°"), ticks=True, equilateral=True)
scene(8, "budget", "The angle budget is already exceeded",
      ["95° + 90° = 185°", "There is no room for a positive third angle."],
      "An angle-total bar reaches 185 degrees, five degrees beyond the 180-degree limit.")
scene(9, "area", "Two copies fill one parallelogram",
      ["Parallelogram area = base × height", "Each triangle gets half: A = ½ × b × h."],
      "Two differently shaded congruent triangles share a diagonal in a parallelogram.",
      base="b", height="h", double=True)
scene(10, "area", "Height meets the base line at 90°",
      ["Use perpendicular height, not a sloping side.", "The foot can lie outside the triangle."],
      "An obtuse triangle has a dashed perpendicular from its apex to the extended base line.",
      base="chosen base", height="height", outside=True)
scene(11, "area", "Halve base × perpendicular height",
      ["A = ½ × 12 × 7", "A = 42 cm²"],
      "A dashed height of 7 cm meets the 12 cm base at a right angle.",
      base="12 cm", height="7 cm", question={})
scene(12, "right", "The legs are already perpendicular",
      ["Use the two legs as base and height.", "A = ½ × 8 × 15 = 60 cm²"],
      "The 8 cm and 15 cm sides meet at the marked right angle.",
      base="8 cm", vertical="15 cm", hyp="", angle="", question={})
scene(13, "area", "Undo the area calculation",
      ["35 = ½ × 10 × h", "h = 2 × 35 ÷ 10 = 7 cm"],
      "A triangle of area 35 square cm has base 10 cm and perpendicular height 7 cm.",
      base="10 cm", height="7 cm", inside="35 cm²", question={"height": "h = ?"})
scene(14, "inequality", "Even stretched flat, they fall short",
      ["4 cm + 6 cm = 10 cm < 11 cm", "Bending the two sides reduces their reach."],
      "End-to-end segments of 4 cm and 6 cm leave a 1 cm gap against an 11 cm segment.",
      question={"unsolved": True})
scene(15, "right", "Look across from the right angle",
      ["The facing side is the hypotenuse.", "It is always the longest side."],
      "The sloping side opposite the square right-angle marker is highlighted as the hypotenuse.",
      base="leg", vertical="leg", hyp="hypotenuse", angle="", highlight="hyp")
scene(16, "right", "Check the right-angle marker first",
      ["Pythagoras applies to right triangles.", "Find the 90° angle before using it."],
      "A square marker and 90-degree label identify the right angle.",
      base="a", vertical="b", hyp="c", angle="", show90=True)
scene(17, "squares", "Add the areas of the two small squares",
      ["Square on a + square on b = square on c", "a² + b² = c²"],
      "Squares are drawn outward on each side of a right triangle. Their areas are a squared, b squared and c squared.",
      labels=("a²", "b²", "c²"))
scene(18, "right", "Square, add, then take the square root",
      ["c² = 6² + 8² = 36 + 64 = 100", "c = √100 = 10 cm"],
      "The 6 cm and 8 cm legs meet at a right angle; the hypotenuse is 10 cm.",
      base="8 cm", vertical="6 cm", hyp="10 cm", angle="", highlight="hyp",
      question={"hyp": "c = ?", "highlight": ""})
scene(19, "right", "A missing leg means subtract",
      ["b² = 13² − 5² = 169 − 25 = 144", "b = √144 = 12 cm"],
      "The 13 cm hypotenuse faces the right angle; the legs are 5 cm and 12 cm.",
      base="5 cm", vertical="12 cm", hyp="13 cm", angle="", highlight="vertical",
      question={"vertical": "b = ?", "highlight": ""})
scene(20, "squares", "Add square areas, not side lengths",
      ["36 + 64 = 100, so c = √100 = 10 cm.", "6 + 8 = 14 is not the hypotenuse."],
      "Squares on the 6 cm and 8 cm legs have areas 36 and 64 square cm. The hypotenuse square has area 100 square cm.",
      labels=("36", "64", "100"), numeric=True)
scene(21, "right", "The diagonal makes a right triangle",
      ["d² = 9² + 12² = 225", "d = √225 = 15 cm"],
      "A 9 cm by 12 cm rectangle is split by its diagonal, which is 15 cm long.",
      base="9 cm", vertical="12 cm", hyp="15 cm", angle="", context="screen", highlight="hyp",
      question={"hyp": "d = ?", "highlight": ""})
scene(22, "right", "The ladder is the hypotenuse",
      ["h² = 10² − 6² = 64", "h = √64 = 8 m"],
      "A 10 m ladder leans against a vertical wall. Its foot is 6 m from the wall; its vertical reach is 8 m.",
      base="6 m", vertical="8 m", hyp="10 m", angle="", context="ladder", highlight="vertical",
      question={"vertical": "h = ?", "highlight": ""})
scene(23, "right", "Test the longest side's square",
      ["7² + 24² = 49 + 576 = 625", "25² = 625: equal, so the angle is 90°."],
      "The longest side is 25 cm, opposite the angle between the 7 cm and 24 cm sides.",
      base="24 cm", vertical="7 cm", hyp="25 cm", angle="", show90=True)
scene(24, "converse", "The square totals do not match",
      ["5² + 6² = 61     but     8² = 64", "61 ≠ 64, so this is not a right triangle."],
      "A triangle has sides 5, 6 and 8 cm. The angle opposite 8 cm has no right-angle marker.",
      question={})
scene(25, "similar", "Same shape, one scale factor",
      ["Matching angles stay equal.", "Every corresponding length is multiplied by k."],
      "Two triangles have equal angle markings. Their matching sides are a and ka, b and kb.",
      labels=("a", "b", "ka", "kb"), factor="× k")
scene(26, "similar", "Match angles before matching sides",
      ["A ↔ D, B ↔ E, C ↔ F", "Opposite A and D: BC ↔ EF."],
      "Triangles ABC and DEF have matching angle arcs. Sides BC and EF, opposite A and D, are highlighted.",
      labels=("", "", "", ""), vertices=True, match_side=True)
scene(27, "similar", "Two matching angles force the third",
      ["In each triangle: c = 180° − a − b.", "The third angles match too: AA similarity."],
      "Both triangles have angles a and b, so each remaining angle is c.",
      labels=("", "", "", ""), angle_names=True)
scene(28, "similar", "Divide new length by original length",
      ["k = 10 ÷ 4 = 2.5", "Multiply every original side by 2.5."],
      "A corresponding side increases from 4 cm to 10 cm.",
      labels=("4 cm", "", "10 cm", ""), factor="× 2.5", question={"factor": "× ?"})
scene(29, "similar", "Use the same multiplier twice",
      ["6 → 9 means multiply by 1.5.", "10 × 1.5 = 15 cm"],
      "Corresponding sides are 6 and 9 cm, and 10 and 15 cm.",
      labels=("6 cm", "10 cm", "9 cm", "15 cm"), factor="× 1.5",
      question={"labels": ("6 cm", "10 cm", "9 cm", "?"), "factor": ""})
scene(30, "similar", "Lengths × 3; area × 9",
      ["A′ = ½ × (3b) × (3h)", "A′ = 9 × (½ × b × h) = 9A"],
      "The enlarged right triangle is divided into nine copies of the original triangle.",
      labels=("b", "h", "3b", "3h"), factor="× 3", grid=True)
scene(31, "similar", "Same shape AND same size",
      ["Scale factor 1 leaves every length unchanged.", "The triangles can fit exactly on each other."],
      "Two triangles have identical dimensions, labelled a and b in both.",
      labels=("a", "b", "a", "b"), factor="× 1", congruent=True)
scene(32, "right", "Name sides from the marked angle",
      ["Opposite: across from θ.", "Adjacent: touches θ, but is not the hypotenuse."],
      "Theta is at the bottom left. The vertical side is opposite; the base is adjacent; the slope is the hypotenuse.",
      base="adjacent", vertical="opposite", hyp="hypotenuse", angle="θ", role_colors=True,
      question={"base": "", "vertical": "", "hyp": "", "role_colors": False})
scene(33, "right", "Sine connects opposite and hypotenuse",
      ["sin θ = opposite ÷ hypotenuse", "SOH: Sine, Opposite, Hypotenuse"],
      "Theta is marked; the opposite side O and hypotenuse H are highlighted.",
      base="A", vertical="O", hyp="H", angle="θ", ratio="sin")
scene(34, "right", "Cosine connects adjacent and hypotenuse",
      ["cos θ = adjacent ÷ hypotenuse", "CAH: Cosine, Adjacent, Hypotenuse"],
      "Theta is marked; the adjacent side A and hypotenuse H are highlighted.",
      base="A", vertical="O", hyp="H", angle="θ", ratio="cos")
scene(35, "right", "Tangent connects opposite and adjacent",
      ["tan θ = opposite ÷ adjacent", "TOA: Tangent, Opposite, Adjacent"],
      "Theta is marked; the opposite side O and adjacent side A are highlighted.",
      base="A", vertical="O", hyp="H", angle="θ", ratio="tan")
scene(36, "right", "Rearrange the sine ratio",
      ["sin θ = O ÷ H", "Multiply by H: O = H × sin θ."],
      "The known hypotenuse H and angle theta determine the opposite side O.",
      base="", vertical="O = ?", hyp="H", angle="θ", ratio="sin", question={"ratio": ""})
scene(37, "right", "Use sine: opposite over hypotenuse",
      ["O = 10 × sin 30°", "O = 10 × 0.5 = 5 cm"],
      "Opposite the 30-degree angle is the 5 cm side; the hypotenuse is 10 cm.",
      base="", vertical="5 cm", hyp="10 cm", angle="30°", ratio="sin",
      question={"vertical": "?", "ratio": ""})
scene(38, "right", "Use tangent: opposite over adjacent",
      ["O = 8 × tan 35° ≈ 5.6017", "O ≈ 5.6 cm   •   Calculator in degrees"],
      "The 8 cm side is adjacent to 35 degrees; the opposite side is about 5.6 cm.",
      base="8 cm", vertical="5.6 cm", hyp="", angle="35°", ratio="tan",
      question={"vertical": "?", "ratio": ""})
scene(39, "right", "Use cosine: adjacent over hypotenuse",
      ["A = 12 × cos 40° ≈ 9.1925", "A ≈ 9.2 cm   •   Calculator in degrees"],
      "The hypotenuse is 12 cm; the side adjacent to 40 degrees is about 9.2 cm.",
      base="9.2 cm", vertical="", hyp="12 cm", angle="40°", ratio="cos",
      question={"base": "?", "ratio": ""})
scene(40, "right", "Use inverse tangent to find the angle",
      ["tan θ = 7 ÷ 10 = 0.7", "θ = tan⁻¹(0.7) ≈ 35.0°   •   Degrees"],
      "The side opposite theta is 7 cm; the adjacent side is 10 cm. Theta is approximately 35 degrees.",
      base="10 cm", vertical="7 cm", hyp="", angle="35.0°", ratio="tan",
      question={"angle": "θ = ?", "ratio": ""})


class Sketch:
    def __init__(self, spec):
        self.img = Image.new("RGB", (900, 720), "white")
        self.d = ImageDraw.Draw(self.img)
        self.fonts = {size: ImageFont.truetype(str(FONT), size) for size in (24, 28, 30, 32, 34, 36)}
        self.math_fonts = {size: ImageFont.truetype(str(MATH_FONT), size) for size in self.fonts}
        self.text((450, 45), spec["title"], 32)
        self.d.line((40, 85, 860, 85), fill="#dce6ed", width=2)
        self.text((450, 535), "Schematic • not to scale", 24, MUTED)
        if spec["steps"]:
            self.d.rounded_rectangle((30, 568, 870, 700), radius=16, fill=PALE)
            for y, step in zip((605, 659), spec["steps"]):
                self.text((450, y), step, 30, TEAL)

    def text(self, xy, text, size=34, color=INK):
        if not text:
            return
        runs = []
        for character in str(text):
            font = self.math_fonts[size] if needs_math_font(character) else self.fonts[size]
            if runs and runs[-1][0] is font:
                runs[-1][1] += character
            else:
                runs.append([font, character])
        width = sum(font.getlength(run) for font, run in runs)
        bounds = [font.getbbox(run, anchor="ls") for font, run in runs]
        top, bottom = min(b[1] for b in bounds), max(b[3] for b in bounds)
        left, baseline = xy[0] - width/2, xy[1] - (top+bottom)/2
        if left < 8 or left+width > 892 or baseline+top < 0 or baseline+bottom > 720:
            raise ValueError(f"Label outside image: {text!r} at {xy}")
        for font, run in runs:
            self.d.text((left,baseline),run,font=font,fill=color,anchor="ls")
            left += font.getlength(run)

    def line(self, points, color=INK, width=5):
        self.d.line(points, fill=color, width=width, joint="curve")

    def triangle(self, points, fill=PALE):
        self.d.polygon(points, fill=fill)
        self.line([*points, points[0]])

    def dashed(self, a, b, color=TEAL):
        length = math.dist(a, b)
        for start in range(0, int(length), 20):
            end = min(start + 11, length)
            self.line([(a[0] + (b[0]-a[0])*t/length, a[1] + (b[1]-a[1])*t/length)
                       for t in (start, end)], color, 3)

    def angle(self, vertex, a, b, radius=45, color=TEAL, count=1):
        start, end = [math.degrees(math.atan2(p[1]-vertex[1], p[0]-vertex[0])) % 360 for p in (a, b)]
        if (end - start) % 360 > 180:
            start, end = end, start
        if end < start:
            end += 360
        for offset in range(count):
            r = radius + offset*7
            self.d.arc((vertex[0]-r, vertex[1]-r, vertex[0]+r, vertex[1]+r), start, end, fill=color, width=3)

    def tick(self, a, b):
        x, y = (a[0]+b[0])/2, (a[1]+b[1])/2
        length = math.dist(a, b)
        dx, dy = -(b[1]-a[1])/length*12, (b[0]-a[0])/length*12
        self.line([(x-dx, y-dy), (x+dx, y+dy)], ORANGE, 4)

    def right(self, x, y):
        self.line([(x-24, y), (x-24, y-24), (x, y-24)], TEAL, 3)


def triangle(s, v):
    a, b, c = (170, 455), (690, 455), (430, 175)
    positions = ((267,421),(594,421),(430,265))
    if v.get("equilateral"):
        a,b,c=(230,455),(630,455),(430,455-200*math.sqrt(3))
        positions=((307,420),(553,420),(430,205))
    s.triangle([a, b, c])
    if v.get("parallel"):
        s.line([(80,175),(820,175)], MUTED, 3)
        # Matching chevrons explicitly mark the parallel lines.
        for x, y in ((760,175),(600,455)):
            s.line([(x-9,y-7),(x,y),(x-9,y+7)], MUTED, 3)
        s.angle(c, (80,175), a, 60, ORANGE)
        s.angle(c, b, (820,175), 60, BLUE)
        s.text((330,206), "a", color=ORANGE)
        s.text((530,206), "b", color=BLUE)
    if v.get("ticks"):
        s.tick(a,c); s.tick(c,b)
        if v.get("equilateral"):
            s.tick(a,b)
    colors = (ORANGE, ORANGE if v.get("ticks") else BLUE, TEAL)
    for p, rays, xy, label, color in zip((a,b,c), ((b,c),(c,a),(a,b)),
            positions, v["angles"], colors):
        if label:
            s.angle(p,*rays, color=color)
            s.text(xy,label,color=color)
    if v.get("exterior"):
        s.line([b,(845,455)], MUTED, 3)
        s.angle(b,(845,455),c,60,TEAL)
        s.text((765,365),v["exterior"],color=TEAL)


def area(s, v):
    a, b = (135,455), (660,455)
    c = (420,175)
    if v.get("outside"):
        a, b, c = (140,455), (580,455), (720,175)
        s.dashed(b,(800,455),MUTED)
    if v.get("double"):
        a,b,c=(100,455),(560,455),(330,190)
        d=(790,190)
        s.triangle([c,b,d],WARM)
    s.triangle([a,b,c])
    foot=(c[0],455)
    s.dashed(c,foot)
    s.line([(foot[0],431),(foot[0]+24,431),(foot[0]+24,455)],TEAL,3)
    s.text(((a[0]+b[0])/2,495),v["base"])
    s.text((c[0]+76,315),v["height"],30,TEAL)
    if v.get("inside"):
        s.text((310,393),v["inside"],30)


def right(s, v):
    a,b,c=(140,455),(670,455),(670,165)
    if v.get("context")=="screen":
        s.d.rounded_rectangle((140,165,670,455),radius=10,fill="#eef3f8",outline=MUTED,width=5)
    if v.get("context")=="ladder":
        s.d.rectangle((670,130,700,455),fill="#dce6ed")
        s.line([(90,455),(755,455)],MUTED,5)
        s.text((742,150),"wall",28,MUTED)
    if v.get("context")=="wire":
        s.d.rectangle((670,135,688,455),fill="#dce6ed")
        s.line([(90,455),(755,455)],MUTED,5)
        s.text((744,150),"pole",28,MUTED)
    if v.get("context")=="ramp":
        s.line([(90,455),(810,455)],MUTED,4)
        s.line([(670,165),(810,165)],MUTED,5)
    if v.get("context")=="path":
        s.line([(75,455),(825,455)],MUTED,12)
        s.text((770,495),"path",28,MUTED)
        s.text((140,405),"bench",28,MUTED)
        s.text((737,135),"tree",28,MUTED)
    s.triangle([a,b,c])
    colors={"base":INK,"vertical":INK,"hyp":INK}
    if v.get("role_colors"):
        colors.update(base=TEAL,vertical=ORANGE,hyp=BLUE)
    pairs={"sin":("vertical","hyp"),"cos":("base","hyp"),"tan":("vertical","base")}
    if v.get("ratio"):
        colors={key:"#aab6c0" for key in colors}
        first,second=pairs[v["ratio"]]
        colors[first],colors[second]=ORANGE,BLUE
    if v.get("highlight"):
        colors[v["highlight"]]=TEAL
    for key,points in (("base",[a,b]),("vertical",[b,c]),("hyp",[a,c])):
        s.line(points,colors[key],6)
    if v.get("context")=="ladder":
        # Small transverse rungs distinguish the ladder from the wall.
        for t in (.18,.32,.46,.60,.74,.88):
            x,y=a[0]+(c[0]-a[0])*t,a[1]+(c[1]-a[1])*t
            s.line([(x-5,y-9),(x+5,y+9)],ORANGE,3)
    s.right(*b)
    s.text((405,496),v["base"],32,colors["base"])
    s.text((774,310),v["vertical"],30,colors["vertical"])
    s.text((382,258),v["hyp"],32,colors["hyp"])
    if v.get("angle"):
        s.angle(a,b,c,70,TEAL)
        s.text((294,420),v["angle"],32,TEAL)
    if v.get("show90"):
        s.text((601,408),"90°",30,TEAL)


def scaled_squares(s, v):
    # A 3:4:5 triangle with outward squares, scaled to fit the full panel.
    a,b,c=(420,320),(580,320),(420,200)
    shapes=[([(420,200),(420,320),(300,320),(300,200)],(360,260),ORANGE,WARM),
            ([(420,320),(580,320),(580,480),(420,480)],(500,400),TEAL,PALE),
            ([(580,320),(420,200),(540,40),(700,160)],(560,180),BLUE,"#e9efff")]
    def p(point):
        return ((point[0]-450)*.85+450, point[1]*.85+100)
    for (points,center,color,fill),label in zip(shapes,v["labels"]):
        points=[p(point) for point in points]
        s.d.polygon(points,fill=fill)
        s.line([*points,points[0]],color,4)
        s.text(p(center),label,36,color)
    s.triangle([p(a),p(b),p(c)],"white")
    x,y=p(a)
    s.line([(x+20,y),(x+20,y-20),(x,y-20)],TEAL,3)
    if v.get("numeric"):
        s.text((145,240),"Areas",30,MUTED)
        s.text((145,278),"in cm²",30,MUTED)
        s.text(p((514,250)),"10",28,BLUE)
        s.text(p((443,258)),"6",28,ORANGE)
        s.text(p((500,300)),"8",28,TEAL)
    else:
        s.text(p((443,258)),"a",30,ORANGE)
        s.text(p((500,300)),"b",30,TEAL)
        s.text(p((514,250)),"c",30,BLUE)


def similar(s, v):
    if v.get("congruent"):
        tris=[[(120,450),(360,450),(360,270)],[(540,450),(780,450),(780,270)]]
    elif v.get("grid"):
        tris=[[(100,450),(200,450),(200,375)],[(480,450),(780,450),(780,225)]]
    else:
        tris=[[(90,450),(310,450),(310,285)],[(475,450),(805,450),(805,202.5)]]
    for i,(a,b,c) in enumerate(tris):
        s.triangle([a,b,c])
        s.right(*b)
        s.angle(a,b,c,32,ORANGE)
        s.angle(c,a,b,28,BLUE,count=2)
        s.text(((a[0]+b[0])/2,490),v["labels"][i*2],30,TEAL)
        s.text((b[0]+43,(b[1]+c[1])/2),v["labels"][i*2+1],28,BLUE)
        if v.get("vertices"):
            for xy,name in zip(((a[0]-12,a[1]+37),(b[0]+5,b[1]+37),(c[0]+5,c[1]-32)),("ABC","DEF")[i]):
                s.text(xy,name,30)
        if v.get("match_side"):
            s.line([b,c],ORANGE,8)
        if v.get("angle_names"):
            s.text((a[0]+65,a[1]-22),"a",30,ORANGE)
            s.text((c[0]-27,c[1]+68),"b",30,BLUE)
            s.text((b[0]-35,b[1]-40),"c",30,TEAL)
    if v.get("factor"):
        s.line([(305,165),(590,165)],TEAL,3)
        s.line([(578,157),(590,165),(578,173)],TEAL,3)
        s.text((447,131),v["factor"],32,TEAL)
    if v.get("grid"):
        a,b,c=tris[1]
        w,h=b[0]-a[0],b[1]-c[1]
        for i in (1,2):
            t=i/3
            s.line([(a[0]+w*t,450),(a[0]+w*t,450-h*t)],TEAL,2)
            s.line([(a[0]+w*t,450-h*t),(b[0],450-h*t)],TEAL,2)
            s.line([(a[0]+w*t,450),(b[0],450-h*(1-t))],TEAL,2)


def draw_diagram(kind: str, directory: Path) -> Path:
    v=DIAGRAMS[kind]
    s=Sketch(v)
    family=v["family"]
    if family in {"triangle","area","right","similar"}:
        {"triangle":triangle,"area":area,"right":right,"similar":similar}[family](s,v)
    elif family=="squares":
        scaled_squares(s,v)
    elif family=="pythagoras":
        from pythagoras_diagrams import draw_pythagoras
        draw_pythagoras(s,v)
    elif family=="budget":
        s.text((450,175),"Triangle angle total: 180°",34)
        s.d.rounded_rectangle((90,255,755,340),radius=8,fill="#eef3f8")
        s.d.rectangle((90,255,432,340),fill=WARM)
        s.d.rectangle((432,255,756,340),fill="#e9efff")
        s.text((260,297),"95°",36,ORANGE); s.text((580,297),"90°",36,BLUE)
        s.line([(738,225),(738,380)],TEAL,4)
        s.text((660,407),"180° limit",30,TEAL)
        s.text((450,463),"Total 185°: 5° too much",34,ORANGE)
    elif family=="inequality":
        s.line([(100,250),(340,250)],TEAL,8)
        s.line([(340,250),(700,250)],BLUE,8)
        s.text((220,209),"4 cm",34,TEAL); s.text((520,209),"6 cm",34,BLUE)
        s.line([(100,375),(760,375)],INK,7)
        s.text((430,420),"11 cm",34)
        s.dashed((700,250),(760,250),ORANGE)
        if not v.get("unsolved"):
            s.text((750,300),"1 cm gap",28,ORANGE)
        for x in (100,760):
            s.dashed((x,270),(x,355),MUTED)
    elif family=="converse":
        a,b,c=(170,455),(710,455),(380,175)
        s.triangle([a,b,c])
        s.text((235,290),"5 cm",32)
        s.text((580,290),"6 cm",32)
        s.text((440,495),"8 cm",32,BLUE)
        s.angle(c,a,b,48,ORANGE)
        s.text((397,285),"?" if not v["steps"] else "≠ 90°",30,ORANGE)
    else:
        raise ValueError(f"Unknown diagram family: {family}")
    if not v["steps"]:
        s.img = s.img.crop((0,0,900,565))
    buffer=io.BytesIO()
    s.img.save(buffer,format="PNG")
    raw=buffer.getvalue()
    path=directory/f"ld-triangles-{kind}-{hashlib.sha256(raw).hexdigest()[:12]}.png"
    path.write_bytes(raw)
    return path
