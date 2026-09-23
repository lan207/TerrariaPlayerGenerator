"""Build and sign a standalone APK using the official SDK, without Gradle."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import re
import shutil
import zipfile
from prepare import prepare

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / 'mobile'


def java_home_default():
    configured=os.environ.get('JAVA_HOME')
    if configured: return Path(configured)
    for folder in os.environ.get('PATH','').split(os.pathsep):
        executable=Path(folder)/'javac.exe'
        if not executable.is_file() or not (Path(folder)/'keytool.exe').is_file(): continue
        version=subprocess.run([str(executable),'-version'],capture_output=True,text=True)
        match=re.search(r'(\d+)(?:\.\d+)?',version.stderr or version.stdout)
        if version.returncode==0 and match and int(match.group(1))>=17: return Path(folder).parent
    return Path()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sdk', type=Path, default=ROOT / '.test-tools/android-sdk')
    parser.add_argument('--java-home', type=Path, default=java_home_default())
    args = parser.parse_args()
    sdk, java = args.sdk.resolve(), args.java_home.resolve()
    tools = sorted(sdk.rglob('aapt2.exe'))
    platforms = sorted(sdk.rglob('android.jar'))
    if not tools or not platforms:
        sys.exit('Missing Android SDK: run python mobile/setup_android.py or pass --sdk PATH.')
    if not (java / 'bin/javac.exe').is_file():
        sys.exit('Pass --java-home PATH pointing to JDK 17 or newer.')
    javac_version = subprocess.run([str(java/'bin/javac.exe'),'-version'],capture_output=True,text=True)
    match = re.search(r'(\d+)(?:\.\d+)?', javac_version.stderr or javac_version.stdout)
    if javac_version.returncode or not match or int(match.group(1)) < 17:
        sys.exit('Android builds require JDK 17 or newer.')
    def revision(path):
        source = path.parent / 'source.properties'
        match = re.search(r'^Pkg.Revision=(\d+)',source.read_text(encoding='utf-8',errors='replace'),re.M) if source.is_file() else None
        return int(match.group(1)) if match else 0
    api_levels=[]
    for platform in platforms:
        source=platform.parent/'source.properties'
        content=source.read_text(encoding='utf-8',errors='replace') if source.is_file() else ''
        match=re.search(r'^AndroidVersion.ApiLevel=(\d+)',content,re.M)
        api_levels.append(int(match.group(1)) if match else 0)
    if max(api_levels) < 35:
        sys.exit('Android SDK platform 35 is required; run python mobile/setup_android.py.')
    if max(map(revision,tools)) < 35:
        sys.exit('Android build-tools 35 are required; run python mobile/setup_android.py.')
    tool = tools[-1].parent
    android = platforms[-1]
    required=[tool/'aapt2.exe',tool/'zipalign.exe',tool/'lib/d8.jar',tool/'lib/apksigner.jar',
              java/'bin/javac.exe',java/'bin/java.exe',java/'bin/keytool.exe']
    missing=[str(path) for path in required if not path.is_file()]
    if missing: sys.exit('Missing Android build component(s):\n'+'\n'.join(missing))
    env = dict(os.environ, JAVA_HOME=str(java))
    # Windows environment keys are case insensitive.
    for key in list(env):
        if key.lower() == 'path': env[key] = str(java / 'bin') + os.pathsep + env[key]

    def run(*command):
        subprocess.run([str(x) for x in command], check=True, env=env, cwd=MOBILE)

    assets = prepare()
    build = MOBILE / 'build'
    classes, dex = build / 'classes', build / 'dex'
    classes.mkdir(exist_ok=True)
    dex.mkdir(exist_ok=True)
    run(tool / 'aapt2.exe', 'compile', '--dir', MOBILE / 'res', '-o', build / 'resources.zip')
    run(tool / 'aapt2.exe', 'link', '-o', build / 'resources.apk', '--manifest', MOBILE / 'AndroidManifest.xml',
        '-I', android, '-A', assets, '--auto-add-overlay', build / 'resources.zip')
    run(java / 'bin/javac.exe', '-encoding', 'UTF-8', '-source', '8', '-target', '8',
        '-classpath', android, '-d', classes, *sorted((MOBILE / 'src').rglob('*.java')))
    # Invoke tool jars directly so paths with spaces work without cmd/batch quoting.
    run(java / 'bin/java.exe', '-cp', tool / 'lib/d8.jar', 'com.android.tools.r8.D8',
        '--lib', android, '--min-api', '26', '--output', dex, *sorted(classes.rglob('*.class')))
    # Repack entries instead of appending: zipfile otherwise changes central-directory
    # UTF-8 flags on aapt2 entries while retaining the old local headers.
    with zipfile.ZipFile(build / 'resources.apk') as resources, \
            zipfile.ZipFile(build / 'unsigned.apk', 'w', compression=zipfile.ZIP_DEFLATED) as apk:
        for entry in resources.infolist():
            apk.writestr(entry.filename, resources.read(entry), compress_type=entry.compress_type)
        for path in dex.glob('*.dex'): apk.write(path, path.name)
    run(tool / 'zipalign.exe', '-f', '4', build / 'unsigned.apk', build / 'aligned.apk')
    signing = MOBILE / '.signing'
    signing.mkdir(exist_ok=True)
    keystore = signing / 'local-test.p12'
    if not keystore.exists():
        run(java / 'bin/keytool.exe', '-genkeypair', '-keystore', keystore, '-storetype', 'PKCS12',
            '-storepass', 'android', '-keypass', 'android', '-alias', 'playerstudio', '-keyalg', 'RSA',
            '-keysize', '2048', '-validity', '10000', '-dname', 'CN=Player Studio Local Build')
    version = re.sub(r'[^0-9A-Za-z_.-]', '_', os.environ.get('GITHUB_SHA', 'local'))[:12]
    versioned_output = ROOT / 'dist' / f'PlayerStudio-android-{version}.apk'
    versioned_output.parent.mkdir(exist_ok=True)
    run(java / 'bin/java.exe', '-jar', tool / 'lib/apksigner.jar', 'sign', '--ks', keystore,
        '--ks-key-alias', 'playerstudio', '--ks-pass', 'pass:android', '--key-pass', 'pass:android',
        '--out', versioned_output, build / 'aligned.apk')
    run(java / 'bin/java.exe', '-jar', tool / 'lib/apksigner.jar', 'verify', '--verbose', versioned_output)
    run(tool / 'aapt2.exe', 'dump', 'badging', versioned_output)
    shutil.copy2(versioned_output,ROOT/'dist'/'PlayerStudio-android.apk')
    sidecar=Path(str(versioned_output)+'.idsig')
    if sidecar.is_file(): shutil.copy2(sidecar,ROOT/'dist'/'PlayerStudio-android.apk.idsig')
    output=ROOT/'dist'/'PlayerStudio-android.apk'
    print(f'APK: {output} ({output.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
