import _bootstrap
import argparse
from rqmc.freeze import freeze

def main():
    p=argparse.ArgumentParser();p.add_argument('--winner',choices=['A','B'],required=True)
    p.add_argument('--baseline',required=True);a=p.parse_args()
    f=freeze(a.winner,a.baseline);print('Frozen:',f['config_hash'])
if __name__=='__main__':main()
