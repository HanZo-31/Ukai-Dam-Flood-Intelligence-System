"""Draw a design reference using the supplied H02 extent; no frontend implementation."""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
W,H=1440,960
im=Image.new('RGB',(W,H),'#f4f7fb')
d=ImageDraw.Draw(im)
NAVY='#12253a'; BLUE='#1677ef'; MUTED='#6b7c8f'; INK='#172b42'; BORDER='#e4eaf1'


def font(size,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/'+('seguisb.ttf' if bold else 'segoeui.ttf'),size)


def text(x,y,value,size=15,fill=INK,bold=False):
    d.text((x,y),value,font=font(size,bold),fill=fill)


def box(x,y,w,h,fill='white',radius=12,outline=None):
    d.rounded_rectangle((x,y,x+w,y+h),radius=radius,fill=fill,outline=outline,width=1)


def pill(x,y,value,fill,ink):
    width=d.textbbox((0,0),value,font=font(12,True))[2]+22
    box(x,y,width,27,fill,13)
    text(x+11,y+5,value,12,ink,True)
    return width


d.rectangle((0,0,224,H),fill=NAVY)
d.rectangle((224,0,W,68),fill='white')
d.line((224,68,W,68),fill=BORDER)
box(24,24,32,32,BLUE,8)
d.arc((30,32,50,46),0,180,fill='white',width=2)
d.arc((30,26,50,40),0,180,fill='white',width=2)
text(68,20,'UKAI',22,'white',True)
text(68,47,'FLOOD EXPLORER',10,'#98abc0',True)
text(25,109,'WORKSPACE',11,'#8c9fb5',True)
box(16,139,192,45,'#203a55',8)
d.ellipse((30,155,41,166),outline='#77b8ff',width=2)
text(53,150,'Scenario explorer',15,'white',True)
text(31,208,'Compare scenarios',15,'#bac7d7')
text(31,250,'Evidence & downloads',15,'#bac7d7')
d.line((24,299,200,299),fill='#304258')
text(25,324,'STORED SCENARIOS',11,'#8c9fb5',True)
cases=[('H01','15,000 m³/s'),('H02','20,000 m³/s'),('H03','30,000 m³/s'),('2006','Reconstructed historical')]
for i,(name,subtitle) in enumerate(cases):
    y=355+i*76
    if name=='H02':
        box(16,y,192,65,'#164f86',8)
        d.rectangle((16,y+10,19,y+55),fill='#6cc1ff')
    text(31,y+9,name,17,'white',True)
    text(31,y+35,subtitle,12,'#bbd0e7')
text(25,818,'4 supplied simulations',13,'#a6b8cd')
text(25,845,'Local workspace · no account',11,'#8198b1')
d.line((24,890,200,890),fill='#304258')
text(25,911,'DESIGN REFERENCE',11,'#94aac1',True)
text(255,24,'Lower Tapi workspace',17,INK,True)
pill(1191,21,'LOCAL WORKSPACE','#eaf5f0','#267554')
text(256,92,'WORKSPACE  /  SCENARIO EXPLORER',11,MUTED,True)
text(254,116,'Explore flood scenarios',30,INK,True)
text(256,160,'Inspect the supplied simulations and compare their mapped outcomes.',15,MUTED)
pill(1176,112,'UNCALIBRATED','#fff1d7','#9b6817')

metrics=[('PEAK RELEASE','20,000','m³/s','Hypothetical H02 input'),('FLOODED AREA','359.7','km²','Depth greater than 0.1 m'),
         ('MAXIMUM DEPTH','38.06','m','Stored simulation result'),('ARRIVAL RESOLUTION','60','min','Relative to simulation start')]
for i,(label,value,unit,description) in enumerate(metrics):
    x=256+i*291
    box(x,205,275,107,outline=BORDER)
    text(x+19,220,label,10,MUTED,True)
    text(x+19,242,value,28,INK,True)
    valwidth=d.textbbox((0,0),value,font=font(28,True))[2]
    text(x+26+valwidth,255,unit,14,MUTED)
    text(x+19,282,description,11,MUTED)

box(256,333,810,505,outline=BORDER)
text(276,351,'H02 · Flood extent',18,INK,True)
text(276,382,'Supplied geographic outline',12,MUTED)
pill(819,353,'Fit to scenario','#eef4fb','#32679c')
d.line((256,417,1066,417),fill=BORDER)
for i,label in enumerate(('Extent','Depth','Velocity','Arrival')):
    x=278+i*106
    if i==0:
        box(x-8,431,87,34,'#e8f2ff',7)
    text(x,438,label,13,BLUE if i==0 else MUTED,i==0)

maprect=(274,481,1048,760)
d.rounded_rectangle(maprect,radius=8,fill='#f0f4f6')
for x in range(285,1048,65):
    d.line((x,483,x,758),fill='#e2e9ee')
for y in range(490,758,48):
    d.line((276,y,1046,y),fill='#e2e9ee')
payload=json.loads((ROOT/'part_a/assets/extent.geojson').read_text())
geometry=payload['features'][0]['geometry']
polygons=geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
R=6378137.0
def mercator(pair):
    return R*math.radians(pair[0]),R*math.log(math.tan(math.pi/4+math.radians(pair[1])/2))
points=[mercator(p) for poly in polygons for ring in poly for p in ring]
xs,ys=zip(*points)
minx,maxx,miny,maxy=min(xs),max(xs),min(ys),max(ys)
scale=min(714/(maxx-minx),209/(maxy-miny))
cx,cy=(maprect[0]+maprect[2])/2,(maprect[1]+maprect[3])/2
def screen(point):
    x,y=mercator(point)
    return cx+(x-(minx+maxx)/2)*scale,cy-(y-(miny+maxy)/2)*scale
mask=Image.new('L',(W,H),0)
md=ImageDraw.Draw(mask)
for poly in polygons:
    md.polygon([screen(p) for p in poly[0]],fill=170)
    for hole in poly[1:]:
        md.polygon([screen(p) for p in hole],fill=0)
blue=Image.new('RGB',(W,H),'#147fde')
im.paste(blue,(0,0),mask)
d=ImageDraw.Draw(im)
for poly in polygons:
    d.line([screen(p) for p in poly[0]],fill='#2c79b9',width=1)
pill(291,498,'LOCAL EXTENT','#ffffff','#365b7d')
box(995,498,32,65,'white',6,outline=BORDER)
text(1005,501,'+',19,MUTED)
d.line((999,530,1023,530),fill=BORDER)
text(1006,533,'−',19,MUTED)
d.rectangle((294,788,310,799),fill='#398de0')
text(320,782,'Flood extent · depth > 0.1 m',12,MUTED)
text(781,782,'H02 supplied geometry',11,MUTED)

box(1086,333,330,505,outline=BORDER)
text(1106,351,'Scenario evidence',18,INK,True)
text(1106,383,'Hypothetical release / H02',12,MUTED)
d.line((1086,417,1416,417),fill=BORDER)
fields=[('Engine','HEC-RAS 2D diffusion wave'),('Result output interval','15 minutes'),('Arrival clock','From simulation start'),('Producing-run timezone','Unverified'),('Population / buildings','Not calculated')]
for i,(label,value) in enumerate(fields):
    y=437+i*59
    text(1106,y,label,11,MUTED)
    text(1106,y+21,value,13,INK,i==0)
box(1105,744,291,67,'#fff7e8',8)
text(1118,754,'Simulation evidence',12,'#97621b',True)
text(1118,777,'Calibration and source limits stay visible.',11,'#8b7146')
box(256,858,1160,75,'white',12,outline=BORDER)
text(276,875,'Next: compare the four scenarios',16,INK,True)
text(276,900,'Shared colour scales · real values · downloadable evidence',12,MUTED)
box(1204,878,190,36,BLUE,8)
text(1223,887,'Open comparison  →',13,'white',True)
text(256,942,'Interface concept. H02 figures and geographic extent use supplied project files; no basemap or forecast is implied.',10,MUTED)
im.save(HERE/'UKAI_FRONTEND_CONCEPT.png')
print('Design reference saved: '+str(HERE/'UKAI_FRONTEND_CONCEPT.png'))
