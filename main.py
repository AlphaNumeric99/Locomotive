import argparse
import io
import sys
import json
import os
import argparse
import hashlib
import zipfile
import shutil
from net import download

parser = argparse.ArgumentParser(description='Train LibreTranslate compatible models')
parser.add_argument('--config',
    type=str,
    default="model-config.json",
    help='Path to model-config.json. Default: %(default)s')

args = parser.parse_args() 
try:
    with open(args.config) as f:
        config = json.loads(f.read())
except Exception as e:
    print(f"Cannot open config file: {e}")
    exit(1)

print(f"Training {config['from']['name']} --> {config['to']['name']} ({config['version']})")
print(f"Data sources: {len(config['sources'])}")


current_dir = os.path.dirname(__file__)
cache_dir = os.path.join(current_dir, "cache")
os.makedirs(cache_dir, exist_ok=True)


sources = {}

for s in config['sources']:
    md5 = hashlib.md5(s.encode('utf-8')).hexdigest()
    dataset_path = os.path.join(cache_dir, md5)
    zip_path = dataset_path + ".zip"

    if not os.path.isdir(dataset_path):
        if not os.path.isfile(zip_path):
            def print_progress(progress):
                print(f"\r{os.path.basename(zip_path)} [{int(progress)}%]     ", end='\r')
            
            download(s, cache_dir, progress_callback=print_progress, basename=os.path.basename(zip_path))
            print()

        os.makedirs(dataset_path, exist_ok=True)
        print(f"Extracting {zip_path} to {dataset_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dataset_path)
        
        os.unlink(zip_path)
    else:
        subfolders = [ f.path for f in os.scandir(dataset_path) if f.is_dir()]
        if len(subfolders) == 1:
            # Move files from subfolder
            for f in [f.path for f in os.scandir(subfolders[0]) if f.is_file()]:
                shutil.move(f, dataset_path)
            
            shutil.rmtree(subfolders[0])
        
        # Find source, target files
        source, target = None, None
        for f in [f.path for f in os.scandir(dataset_path) if f.is_file()]:
            if "target" in f.lower():
                target = f
            if "source" in f.lower():
                source = f
            
        if source is not None and target is not None:
            sources[s] = {
                'source': source,
                'target': target,
                'hash': md5
            }

for k in sources:
    print(f" - {k} ({sources[k]['hash']})")

spm_train_exe = shutil.which("spm_train")
if spm_train_exe is None:
    if sys.platform == 'win32':
        download("")
# TODO: check spm binaries on Windows