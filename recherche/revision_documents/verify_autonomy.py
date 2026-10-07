"""Compile chaque note dans un dossier temporaire, sans l'autre note ni les runs."""
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
for dirname,stem in [("note_resultats","note"),("note_communication_encadrants","note_encadrants")]:
    source=HERE.parent/dirname/"latex"
    with tempfile.TemporaryDirectory(prefix="revision-autonomie-") as temp:
        target=Path(temp)
        for path in source.glob("*.tex"):
            shutil.copy2(path,target/path.name)
        shutil.copytree(source/"figures",target/"figures")
        for attempt in range(3):
            result=subprocess.run(["pdflatex","-interaction=nonstopmode","-halt-on-error",stem+".tex"],cwd=target,capture_output=True)
            log=result.stdout.decode("utf-8",errors="replace")
            (HERE/"generated"/f"{stem}_autonomie.log").write_text(log)
            assert result.returncode==0,log[-1500:]
        assert "There were undefined references" not in log
        assert "Rerun to get cross-references right" not in log
        assert "Overfull" not in log
        print(f"{dirname}: compilation isolée réussie, sans référence indéfinie ni débordement")
