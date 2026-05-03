#!/usr/bin/env python3

import os

patches = [
    {
        "file": ".local/share/pipx/venvs/flintrock/lib/python3.14/site-packages/flintrock/flintrock.py",
        "lines": (295,295),
        "replacement": '''
@click.option('--hdfs-version', default='3.4.2')'''
    },
    {
        "file": ".local/share/pipx/venvs/flintrock/lib/python3.14/site-packages/flintrock/flintrock.py",
        "lines": (293,293),
        "replacement": '''
@click.option('--java-version', type=click.IntRange(min=8), default=21)'''
    },
    {
         "file": ".local/share/pipx/venvs/flintrock/lib/python3.14/site-packages/flintrock/scripts/setup-ephemeral-storage.py",
         "lines": (215, 219),
         "replacement": '''
    for (num, device) in enumerate(sorted(non_root_block_devices, key=lambda d: d.kname)):
        if device.kname not in ['/dev/xvda', '/dev/nvme0n1']:
            ephemeral_devices.append(
                BlockDevice(
                    kname=device.kname,
                    mountpoint='/media/ephemeral' + str(num)))'''
    },
    {
        "file": ".local/share/pipx/venvs/flintrock/lib/python3.14/site-packages/flintrock/services.py",
        "lines": (367,367),
        "replacement": '''
                    python3 /tmp/download-package.py "{download_source}" "spark"'''
    },
    {
        "file": ".local/share/pipx/venvs/flintrock/lib/python3.14/site-packages/flintrock/services.py",
        "lines": (183,183),
        "replacement": '''
                python3 /tmp/download-package.py "{download_source}" "hadoop"'''
    },
    {
        "file": ".local/share/pipx/venvs/flintrock/lib/python3.14/site-packages/flintrock/scripts/download-package.py",
        "lines": (38,38),
        "replacement": '''
                subprocess.check_call(['aws', 's3', 'cp', '--no-sign-request', url, download_path])'''
    },
    {
        "file": ".local/share/pipx/venvs/flintrock/lib/python3.14/site-packages/flintrock/core.py",
        "lines": (676,676),
        "replacement": '''
            sudo yum install -y python3.14'''
    },
    {
        "file": ".local/share/pipx/venvs/flintrock/lib/python3.14/site-packages/flintrock/core.py",
        "lines": (661,661),
        "replacement": '''
            python3 /tmp/setup-ephemeral-storage.py'''
    },
    {
        "file": ".local/share/pipx/venvs/flintrock/lib/python3.14/site-packages/flintrock/core.py",
        "lines": (583,600),
        "replacement": '''
    ssh_check_output(
        client=client,
        command="""
            set -e
            # Install dependencies manually (minimal GUI/headless support)
            sudo yum install -y \\
                alsa-lib \\
                dejavu-sans-fonts \\
                fontconfig \\
                libX11 \\
                libXext \\
                libXi \\
                libXrender \\
                libXtst
            echo "Getting temurin"
            wget https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.11%2B10/OpenJDK21U-jdk_x64_linux_hotspot_21.0.11_10.tar.gz -O /tmp/temurin21.tar.gz
            cd /opt
            sudo tar -xzf /tmp/temurin21.tar.gz
            sudo mv jdk-21.0.11+10 temurin-21
            # Set JAVA_HOME
            echo 'export JAVA_HOME=/opt/temurin-21' | sudo tee /etc/profile.d/java.sh
            echo 'export PATH=$JAVA_HOME/bin:$PATH' | sudo tee -a /etc/profile.d/java.sh
            source /etc/profile.d/java.sh
            # Verify
            java -version
            sudo yum remove -y java-1.6.0-openjdk java-1.7.0-openjdk
            source /etc/environment
        """)'''
    }
]

def apply_patch(patch):
    file_path = patch["file"]
    start, end = patch["lines"]
    replacement = patch["replacement"].lstrip('\n').rstrip('\n')
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    with open(file_path, 'r') as f:
        lines = f.readlines()
    # Convert to 0-based indices
    start_idx = start - 1
    end_idx = end
    new_lines = lines[:start_idx] + [replacement + '\n'] + lines[end_idx:]
    with open(file_path, 'w') as f:
        f.writelines(new_lines)
    print(f"Patched {file_path}: lines {start}-{end}")

# Main patching loop
if __name__ == "__main__":
    for patch in patches:
        apply_patch(patch)
