import subprocess
import sys
import argparse
import configparser

# 定义可调整参数及其分类
PARAMETERS = {
    'Power Limits': [
        ('stapm', 'Sustained Power Limit (STAPM_LIMIT)'),
        ('fast', 'PPT Limit Fast (PPT_FAST_LIMIT)'),
        ('slow', 'PPT Limit Slow (PPT_SLOW_LIMIT)'),
    ],
    'Current Limits': [
        ('vrm', 'VRM Current Limit (TDC_VDD_LIMIT)'),
        ('vrmsoc', 'VRM SoC Current Limit (TDC_SOC_LIMIT)'),
        ('edc', 'EDC Current Limit VDD (EDC_VDD_LIMIT)'),
        ('edcsoc', 'EDC Current Limit SoC (EDC_SOC_LIMIT)'),
    ],
    'Clocks': [
        ('max-socclk', 'Max SoC Clock Frequency'),
        ('min-socclk', 'Min SoC Clock Frequency'),
        ('max-gfxclk', 'Max GFX Clock Frequency'),
        ('min-gfxclk', 'Min GFX Clock Frequency'),
    ],
    'Temperatures': [
        ('tctl-temp', 'Tctl Temperature Limit'),
        ('apu-skin-temp', 'APU Skin Temp Limit'),
        ('dgpu-skin-temp', 'dGPU Skin Temp Limit'),
    ],
}

def list_parameters():
    print("Available RyzenAdj parameters:\n")
    for group, items in PARAMETERS.items():
        print(f"[{group}]")
        for key, desc in items:
            print(f"  --{key}    {desc}")
        print()


def call_ryzenadj(args_list):
    cmd = ['ryzenadj.exe'] + args_list
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {{e}}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: ryzenadj.exe not found in PATH.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='UI wrapper for ryzenadj.exe'
    )
    parser.add_argument('--list', action='store_true', help='List adjustable parameters')
    # 接受任意 ryzenadj 参数
    parser.add_argument('ryzenargs', nargs=argparse.REMAINDER,
                        help='Arguments passed to ryzenadj.exe')
    args = parser.parse_args()

    if args.list:
        list_parameters()
        sys.exit(0)

    if not args.ryzenargs:
        parser.print_help()
        sys.exit(0)

    # 调用 ryzenadj
    call_ryzenadj(args.ryzenargs)

if __name__ == '__main__':
    main()
