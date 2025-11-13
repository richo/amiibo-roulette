#!/usr/bin/env python3
import argparse
import os
import random
import subprocess
import sys
import tempfile


def mklog(c):
    def inner(m):
        print('[' + c + '] ' + m)
        sys.stdout.flush()
    return inner

log = mklog('+')
err = mklog('!')

def arg_parser():
    parser = argparse.ArgumentParser(description='Load random amiibo')
    parser.add_argument('source', type=str, help='Source of amiibo to load')
    parser.add_argument('--process', dest='process', action='store_true',
                        default=False,
                        help="Process the file with mfubin2eml before loading")
    parser.add_argument('--single', dest='single', action='store_true',
            default=False,
            help='Load the specified amiibo instead of random one')
    parser.add_argument('--reveal', dest='reveal', action='store_true',
            default=False,
            help='Tell you which amiibo is being loaded if you hate surprises')
    parser.add_argument('--device', dest='device', action='store',
            default="/dev/ttyACM0",
            help='Use the specified device')
    return parser

class Mfubin2emlWrapper(object):
    def __init__(self, mfubin2eml):
        self.bin = mfubin2eml

    def convert(self, path):
        log("Invoking mfubin2eml")
        proc = subprocess.Popen([self.bin, path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        eml = tempfile.NamedTemporaryFile(suffix=".eml")

        log("eml path: {}".format(eml.name))
        assert os.path.exists(eml.name)

        log("Writing eml")
        n = eml.write(out)
        eml.flush()

        commands = err.splitlines()[-2:]
        assert commands[0].startswith(b"hf mf eload u"), "Didn't get load commands correctly"
        assert os.path.exists(eml.name)
        return eml, commands[1]

class ProxmarkWrapper(object):
    def __init__(self, path):
        self.path = path
        self.device = None

    def load_eml(self, path):
        assert path.endswith(".eml"), "Path is not an eml file"
        # hf mfu eload -f u coco.eml
        self.run("hf mfu eload -f {}".format(path))

    def simulate(self):
        self.run("hf mfu sim -t 7")


    def run(self, cmd):
        log(cmd)
        self.proxmark = subprocess.Popen([self.path, "-c", cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE)
        out, err = self.proxmark.communicate()
        log(str(out))

def get_random_file(path, suffix):
    def bins():
        for root, _, files in os.walk(path):
            for filename in files:
                fullpath = os.path.join(root, filename)
                if fullpath.endswith(suffix):
                    yield fullpath
    return random.choice([bin for bin in bins()])

def main():
    parser = arg_parser()
    args = parser.parse_args()
    suffix = ".bin" if args.process else ".eml"

    if args.single:
        amiibo = args.source
        assert amiibo.endswith(suffix), "Must specify file of type {}".format(suffix)
    else:
        amiibo = get_random_file(args.source, suffix)
        if args.reveal:
            log("Loading {}".format(amiibo))

    if args.process:
        mfubin2eml = os.environ["MFUBIN2EML"]
        wrapper = Mfubin2emlWrapper(mfubin2eml)
        # TODO(richo) verify this actually works
        eml, loadcommand = wrapper.convert(amiibo)
        assert os.path.exists(eml.name)
    else:
        eml = amiibo


    proxmark = os.environ["PROXMARK"]
    pm = ProxmarkWrapper(proxmark)
    # TODO(richo) Actually support this option again for proxmark3 instead of the pm3 wrapper
    pm.device = args.device

    pm.load_eml(eml.name)
    pm.simulate()

if __name__ == '__main__':
    main()
