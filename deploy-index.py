# -*- coding: utf-8 -*-
"""
青花微课 - 精简部署工具（仅更新 index.html）
运行: python deploy-index.py
会提示输入服务器密码，自动上传 index.html 并部署到 qhwk2016.com
"""
import os, sys, getpass

HOST = "43.139.55.178"
PORT = 22
USER = "ubuntu"
LOCAL_INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
REMOTE_TMP = "/tmp/qhwk-site/index.html"
SITE_INDEX = "/var/www/qhwk2016/index.html"


def run_sudo(ssh, cmd, pwd):
    """Execute sudo command, feed password via stdin (not exposed in process list)."""
    stdin, stdout, stderr = ssh.exec_command("sudo -S " + cmd)
    stdin.write(pwd + "\n")
    stdin.flush()
    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return rc, out, err


def main():
    if not os.path.exists(LOCAL_INDEX):
        print("[X] index.html not found: " + LOCAL_INDEX)
        sys.exit(1)

    size = os.path.getsize(LOCAL_INDEX)
    print("=" * 50)
    print("  qhwk2016.com - deploy index.html only")
    print("  server: {}@{}:{}".format(USER, HOST, PORT))
    print("  local:  {} ({} bytes)".format(LOCAL_INDEX, size))
    print("=" * 50)

    pwd = os.environ.get("QHWK_PWD") or getpass.getpass("\npassword for {}@{}: ".format(USER, HOST))

    import paramiko
    print("\n[1/4] connecting...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, port=PORT, username=USER, password=pwd, timeout=15)
    except Exception as e:
        print("[X] SSH connect failed: " + str(e))
        sys.exit(1)
    print("    SSH connected!")

    print("\n[2/4] uploading index.html...")
    ssh.exec_command("mkdir -p /tmp/qhwk-site")[1].channel.recv_exit_status()
    sftp = ssh.open_sftp()
    sftp.put(LOCAL_INDEX, REMOTE_TMP)
    sftp.close()
    print("    uploaded ({} bytes)".format(size))

    print("\n[3/4] deploying...")
    rc, out, err = run_sudo(ssh, "cp {} {}".format(REMOTE_TMP, SITE_INDEX), pwd)
    if rc != 0:
        print("[X] cp failed: " + err)
        ssh.close(); sys.exit(1)
    run_sudo(ssh, "chown www-data:www-data {}".format(SITE_INDEX), pwd)
    rc, out, err = run_sudo(ssh, "nginx -t 2>&1 && systemctl reload nginx", pwd)
    if rc == 0:
        print("    deployed + nginx reloaded")
    else:
        print("    [!] nginx reload warning: " + err.strip())

    print("\n[4/4] verifying...")
    stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/")
    code = stdout.read().decode("utf-8", errors="replace").strip()
    print("    local HTTP: " + code)
    stdin, stdout, stderr = ssh.exec_command("stat -c '%y' " + SITE_INDEX)
    ts = stdout.read().decode("utf-8", errors="replace").strip()
    print("    file mtime: " + ts)

    ssh.close()
    print("\n" + "=" * 50)
    print("  DONE! Visit https://qhwk2016.com")
    print("  (press Ctrl+Shift+R to bypass browser cache)")
    print("=" * 50)


if __name__ == "__main__":
    try:
        import paramiko
    except ImportError:
        print("paramiko not found, installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko"])
    main()
