"""Download official Android SDK platform/build tools into this workspace only."""
import hashlib
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / '.test-tools' / 'android-sdk'
PACKAGES = [
    ('platform-35_r02.zip', '0bb560a90a7a2cbd0dd8348224d518b638fe7949', 'platform'),
    ('build-tools_r35_windows.zip', 'af059bb67cf7786f45ee0db85e2d24985df1b4b6', 'build-tools'),
]

for name, expected, folder in PACKAGES:
    archive = DEST / name
    DEST.mkdir(parents=True, exist_ok=True)
    if not archive.exists() or hashlib.sha1(archive.read_bytes()).hexdigest() != expected:
        print(f'Downloading {name} from dl.google.com...', flush=True)
        with urllib.request.urlopen('https://dl.google.com/android/repository/' + name, timeout=120) as response:
            with archive.open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
    if hashlib.sha1(archive.read_bytes()).hexdigest() != expected:
        raise RuntimeError(f'Checksum mismatch: {name}')
    with zipfile.ZipFile(archive) as z:
        z.extractall(DEST / folder)
    print(f'Installed {folder}', flush=True)
print('Android SDK ready.')
