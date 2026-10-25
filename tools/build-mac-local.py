#!/usr/bin/env python3
"""Native ARM Debug build using packaged Qt and the local dependency prefix."""
import argparse
import os
from pathlib import Path
import platform
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / 'local-mac'
PREFIX = LOCAL / 'prefix'
SOURCE = ROOT / 'tdesktop'
ENV = dict(os.environ)
ENV.update({
    'MACOSX_DEPLOYMENT_TARGET': '14.0',
    'PATH': str(LOCAL / 'qt/bin') + ':/opt/homebrew/bin:' + ENV.get('PATH', ''),
    'PKG_CONFIG_PATH': ':'.join([
        str(PREFIX / 'lib/pkgconfig'),
        '/opt/homebrew/opt/openssl@3/lib/pkgconfig',
        '/opt/homebrew/lib/pkgconfig',
    ]),
    'DYLD_LIBRARY_PATH': str(PREFIX / 'lib'),
})
COMMON = [
    '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Debug',
    '-DCMAKE_C_FLAGS_DEBUG=-O1 -g0', '-DCMAKE_CXX_FLAGS_DEBUG=-O1 -g0',
    '-DCMAKE_OBJC_FLAGS_DEBUG=-O1 -g0', '-DCMAKE_OBJCXX_FLAGS_DEBUG=-O1 -g0',
    '-DCMAKE_OSX_ARCHITECTURES=arm64', '-DCMAKE_OSX_DEPLOYMENT_TARGET=14.0',
    '-DCMAKE_INSTALL_PREFIX=' + str(PREFIX),
    '-DCMAKE_PREFIX_PATH=' + str(PREFIX) + ';' + str(LOCAL / 'qt')
        + ';/opt/homebrew;/opt/homebrew/opt/openssl@3',
    '-DOPENSSL_ROOT_DIR=/opt/homebrew/opt/openssl@3',
]


def run(command, cwd, log):
    command = [str(part) for part in command]
    print('Running', command[0], 'in', cwd, flush=True)
    with (LOCAL / 'logs' / (log + '.log')).open('a') as output:
        output.write('\nCOMMAND: ' + repr(command) + '\n')
        output.flush()
        subprocess.run(command, cwd=cwd, env=ENV, stdout=output,
                       stderr=subprocess.STDOUT, check=True)


def cmake_library(name, options):
    source = LOCAL / 'src' / name
    build = source / 'build-local'
    run(['cmake', '-S', source, '-B', build, *COMMON, *options], source, name)
    run(['cmake', '--build', build, '--parallel', '2'], source, name)
    run(['cmake', '--install', build], source, name)


def ffmpeg():
    # Reuse the exact codec/filter selection in this pinned upstream release.
    prepare = (SOURCE / 'Telegram/build/prepare/prepare.py').read_text()
    block = prepare.split('configureFFmpeg() {', 1)[1].split('\n    }', 1)[0]
    options = re.findall(r'--(?:enable|disable)-[a-zA-Z0-9_-]+(?:=[a-zA-Z0-9_,.-]+)?', block)
    options = [value for value in options if value != '--enable-cross-compile']
    source = LOCAL / 'src/ffmpeg'
    run(['./configure', '--prefix=' + str(PREFIX), '--arch=arm64',
         '--target-os=darwin', '--disable-debug', '--enable-shared',
         '--disable-static', '--extra-cflags=-mmacosx-version-min=14.0 -O1 -g0 -DCONFIG_SAFE_BITSTREAM_READER=1',
         '--extra-ldflags=-mmacosx-version-min=14.0 -lc++', *options], source, 'ffmpeg')
    run(['make', '-j2'], source, 'ffmpeg')
    run(['make', 'install'], source, 'ffmpeg')


def glib():
    source = LOCAL / 'src/glib-2.90.1'
    build = source / 'build-local'
    meson = LOCAL / 'build-tools/bin/meson'
    run([meson, 'setup', build, source, '--prefix=' + str(PREFIX),
         '--buildtype=debugoptimized', '-Ddebug=false', '-Dtests=false',
         '-Dintrospection=disabled', '-Ddocumentation=false', '-Dman-pages=disabled',
         '-Ddtrace=disabled', '-Dsystemtap=disabled', '-Dnls=disabled',
         '-Dlibmount=disabled', '-Dselinux=disabled'], source, 'glib')
    run(['ninja', '-C', build, '-j2'], source, 'glib')
    run([meson, 'install', '-C', build], source, 'glib')


def client(configure_only):
    build = LOCAL / 'client-build'
    run(['cmake', '-S', SOURCE, '-B', build, '-UQt6*', '-UQT_*', *COMMON,
         '-Dtg_owt_DIR=' + str(PREFIX / 'lib/cmake/tg_owt'),
         '-DQt6_DIR=' + str(LOCAL / 'qt/lib/cmake/Qt6'),
         '-DQSB_EXECUTABLE=' + str(LOCAL / 'qt/bin/qsb'),
         '-DDESKTOP_APP_MAC_ARCH=arm64', '-DDESKTOP_APP_USE_PACKAGED=ON',
         '-DDESKTOP_APP_DISABLE_SWIFT6=ON', '-DDESKTOP_APP_DISABLE_AUTOUPDATE=ON',
         '-DDESKTOP_APP_DISABLE_CRASH_REPORTS=ON', '-DTDESKTOP_API_TEST=ON',
         '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'], SOURCE, 'client-configure')
    if not configure_only:
        run(['cmake', '--build', build, '--target', 'Telegram', '--parallel', '2', '--', '-k', '0'],
            SOURCE, 'client-build')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['ada', 'openal-soft', 'ffmpeg', 'tg_owt',
                                         'glib', 'harfbuzz', 'md4c', 'client'])
    parser.add_argument('--configure-only', action='store_true')
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        parser.error('This local build configuration targets an Apple Silicon Mac.')
    (LOCAL / 'logs').mkdir(parents=True, exist_ok=True)
    if args.stage == 'ada':
        cmake_library('ada', ['-DADA_TESTING=OFF', '-DADA_TOOLS=OFF',
                             '-DADA_INCLUDE_URL_PATTERN=OFF'])
    elif args.stage == 'openal-soft':
        cmake_library('openal-soft', ['-DALSOFT_UTILS=OFF', '-DALSOFT_EXAMPLES=OFF',
                                    '-DALSOFT_TESTS=OFF', '-DLIBTYPE=STATIC'])
    elif args.stage == 'ffmpeg':
        ffmpeg()
    elif args.stage == 'tg_owt':
        cmake_library('tg_owt', ['-DTG_OWT_BUILD_AUDIO_BACKENDS=OFF'])
    elif args.stage == 'glib':
        glib()
    elif args.stage == 'harfbuzz':
        cmake_library('harfbuzz-14.6.0', ['-DBUILD_SHARED_LIBS=ON',
            '-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-compatibility_version,61460.0.0,-current_version,61460.0.0',
            '-DHB_HAVE_FREETYPE=ON', '-DHB_BUILD_SUBSET=OFF', '-DHB_BUILD_RASTER=OFF',
            '-DHB_BUILD_VECTOR=OFF', '-DHB_BUILD_GPU=OFF', '-DHB_BUILD_UTILS=OFF'])
    elif args.stage == 'md4c':
        cmake_library('md4c-0.6.0', ['-DBUILD_SHARED_LIBS=ON', '-DBUILD_MD2HTML_EXECUTABLE=OFF'])
    else:
        client(args.configure_only)
    print('Completed:', args.stage, flush=True)


if __name__ == '__main__':
    main()
