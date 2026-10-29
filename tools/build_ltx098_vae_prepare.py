"""Build the model-free native old-VAE asset preparer; no APK modification."""
import argparse
from build_ltx098_prepare import build as build_native, inputs as native_inputs


def inputs():return native_inputs(vae=True)


def build(android=False):return build_native(android=android,vae=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--android',action='store_true');build(parser.parse_args().android)
