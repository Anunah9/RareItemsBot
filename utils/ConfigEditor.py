import os
from pathlib import Path


def get_config_files(_path_configs):
    files = os.listdir(_path_configs)
    return files


if __name__ == '__main__':
    path_configs = r'C:\Users\Sasha\Desktop\openVpn\configs'
    configs = get_config_files(path_configs)
    print(configs)
    for config in configs:
        print(config)
        with open(Path(path_configs, config), 'a') as f:
            f.writelines('route-nopull')

