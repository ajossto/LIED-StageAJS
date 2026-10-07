"""Planches de contrôle du rendu PDF, sans modifier les documents."""
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
OUT=HERE/"generated/relecture"
OUT.mkdir(exist_ok=True)
for dirname,stem in [("note_resultats","note"),("note_communication_encadrants","note_encadrants")]:
    pdf=HERE.parent/dirname/"latex"/f"{stem}.pdf"
    with tempfile.TemporaryDirectory(prefix="rev-pdf-") as temp:
        subprocess.run(["pdftoppm","-scale-to","650","-png",str(pdf),str(Path(temp)/"page")],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        pages=sorted(Path(temp).glob("page-*.png"),key=lambda p:int(p.stem.split("-")[-1]))
        for offset in range(0,len(pages),12):
            sheet=Image.new("RGB",(4*470,3*690),"#cccccc")
            draw=ImageDraw.Draw(sheet)
            for i,path in enumerate(pages[offset:offset+12]):
                img=Image.open(path).convert("RGB")
                img.thumbnail((450,650))
                x=(i%4)*470+10;y=(i//4)*690+24
                sheet.paste(img,(x,y));draw.text((x,y-19),f"{stem} — page {offset+i+1}",fill="black")
            target=OUT/f"{stem}_{offset+1:03d}.png"
            sheet.save(target)
            print(target)
