import sys
import os
import hashlib
import subprocess

HASHS = {}


def md5sum(filename, blocksize=65536):
    return subprocess.check_output(['md5', filename])


def parse_dir(dir_path, filters=[".dylib", ".so"]):
    for dirpath, dirnames, filenames in os.walk(dir_path):
        for f in filenames:
            print(f)
            if filters is not None and \
                    os.path.splitext(f)[1] not in filters:
                continue
            fn = os.path.join(dirpath, f)
            d = os.path.dirname(fn)
            m = md5sum(fn)
            h = (d, m)
            if h in HASHS:
                HASHS[h].append(fn)
            else:
                HASHS[h] = [fn]

if __name__ == "__main__":
    print("-- analyse", sys.argv[1])
    parse_dir(sys.argv[1])
    print("-- fix similar md5", sys.argv[1])
    basedir = os.getcwd()
    for _, items in HASHS.items():
        directory, md5 = _
        if len(items) <= 1:
            continue
        print(" - fix duplicate", md5, items)
        source = items[0]
        for dest in items[1:]:
            os.unlink(dest)
            os.chdir(directory)
            os.symlink(os.path.basename(source), os.path.basename(dest))
            os.chdir(basedir)
