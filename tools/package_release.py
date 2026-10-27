#!/usr/bin/env python3
"""Build local review archives. Does not upload, submit, publish or order."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables'
SKIP={'.git','__pycache__','.resilient_cache','.venv','tmp','deliverables','build','.pio'}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def source_files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and not any(x in SKIP for x in p.relative_to(ROOT).parts) and p.name!='.DS_Store')

def archive(name,files):
    path=OUT/name
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(set(files)):
            z.write(p,'open-cgm-kit/'+str(p.relative_to(ROOT)))
    with zipfile.ZipFile(path) as z:
        bad=z.testzip()
        if bad: raise ValueError(f'Archive CRC failure: {bad}')
    return {'name':name,'bytes':path.stat().st_size,'sha256':sha(path)}

def main():
    OUT.mkdir(exist_ok=True)
    files=source_files()
    # Check upstream byte-for-byte provenance before redistributing the snapshot.
    vendor=ROOT/'vendor/biocoin'
    original=json.loads((vendor/'UPSTREAM_MANIFEST.json').read_text())
    for f in original['files']:
        p=vendor/f['path']
        if sha(p)!=f['sha256']: raise ValueError(f"Changed upstream file: {f['path']}")
    manifest={'revision':'A0','status':'review and supplier RFQ; no hardware fabricated',
              'upstream_commit':original['commit'],
              'files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]}
    (OUT/'package_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    packs=[]
    packs.append(archive('open-cgm-kit-A0.zip',files+[OUT/'package_manifest.json',OUT/'software_verification.json']))
    common=[ROOT/'README.md',ROOT/'docs/A0_PACKAGE.md',ROOT/'LICENSE',*list((ROOT/'LICENSES').glob('*'))]
    print_files=[ROOT/'mechanical/generated/base_fit_prototype.stl',ROOT/'mechanical/generated/lid_fit_prototype.stl',ROOT/'mechanical/open_cgm_A0.scad',ROOT/'mechanical/parameters.json',ROOT/'mechanical/generated/geometry_validation.json',ROOT/'docs/FABRICATION.md',ROOT/'docs/RELEASE_STATUS.md',ROOT/'docs/PRINT_JOB.md']
    packs.append(archive('enclosure-fit-print-A0.zip',common+print_files))
    sensor=[p for p in files if str(p.relative_to(ROOT)).startswith('hardware/')]
    sensor += [ROOT/'mechanical/parameters.json',ROOT/'docs/SENSOR_PROCESS.md',ROOT/'docs/FABRICATION.md',ROOT/'docs/RELEASE_STATUS.md']
    packs.append(archive('sensor-fabrication-RFQ-A0.zip',common+sensor))
    (OUT/'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['name']}\n" for r in packs))
    (OUT/'archives.json').write_text(json.dumps(packs,indent=2)+'\n')
    print(json.dumps({'source_files':len(files),'upstream_files_verified':len(original['files']),'archives':packs},indent=2))

if __name__=='__main__':main()
