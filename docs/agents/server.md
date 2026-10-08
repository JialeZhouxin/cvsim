# Deploy target: Oracle Cloud 服务器

本仓库有一个长期运行的部署环境，用于在云端跑完整的测试套件、提供 Lab 的 Web 服务，以及脱离本机做长时间计算。

## 关于本文的占位符

本文**故意不含**服务器 IP、主机名、私钥路径等具体值 —— 仓库是公开的，那类信息只留在本机 `~/.ssh/config`。

| 占位符 | 真实值在哪 |
|---|---|
| `<SERVER_IP>` | 本机 `~/.ssh/config` 的 `Host oracle1` 段；或 OCI 控制台实例页 |
| `<PRIVATE_IP>` | 同上（VCN 内网地址，通常 `10.0.0.x`） |
| `<HOSTNAME>` | 同上（形如 `instance-<创建日期>-<时分>`） |
| `<PRIVATE_KEY_PATH>` | 本机 `~/.ssh/config` 的 `IdentityFile` 行 |

需要具体值时执行 `ssh -G oracle1 | grep -E 'hostname|identityfile|user'`。

## 连接

连接方式：本机 `~/.ssh/config` 里已配好别名 `oracle1`，`ssh oracle1` 直接进。

真实 IP 与私钥路径只存在那份本机配置里，**不写进仓库**。配置形状如下（值用占位符）：

```
Host oracle1
    HostName <SERVER_IP>
    User opc
    IdentityFile <PRIVATE_KEY_PATH>
    IdentitiesOnly yes
    ServerAliveInterval 30
    ServerAliveCountMax 4
```

- 私钥：Oracle 控制台生成的那把 RSA 2048（真实路径见本机 config）
- 主机密钥已写入本机 `known_hosts`，不会弹 `yes/no`
- **用户名是 `opc`，不是 `ubuntu`**。这台机器的 `ubuntu` 用户不存在，试它会得到 `Permission denied (publickey)`；`opc` 才是 Oracle Linux 镜像的默认用户（`sudo -n` 免密到 root，属镜像默认行为）

## 规格

| 项 | 值 |
|---|---|
| 主机名 | `<HOSTNAME>`（OCI 控制台可见） |
| 公网 IP | `<SERVER_IP>` |
| 私网 IP | `<PRIVATE_IP>`（VCN 内网） |
| OS | Oracle Linux Server 9.8 |
| 内核 | `6.12.0-206.104.4.4.el9uek.x86_64` |
| 架构 | x86_64 |
| CPU | 2 核 |
| 内存 | **498 MiB** + 4.5 GB swap |
| 磁盘 | 30 GB（约 12 GB 已用） |
| systemd | 内存 cgroup 已设护栏，见下 |

**498 MiB 内存是这台机器最重要的约束**。任何 `dnf` 操作实测需要 341 MB RAM + 2665 MB swap，因此所有工具都装在 `~/.local` 下（静态二进制），不走系统包管理。

## Oracle 闲置回收规则与保活

### 官方规则（原文出处）

**实例回收** — `https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm#compute__idleinstances`

> Idle Always Free compute instances may be reclaimed by Oracle. Oracle will deem virtual machine and bare metal compute instances as idle if, during a 7-day period, the following are true:
>
> - CPU utilization for the 95th percentile is less than 20%
> - Network utilization is less than 20%
> - Memory utilization is less than 20% *(applies to A1 shapes only)*

**账户回收** — `https://www.oracle.com/cloud/free/faq/`

> Accounts left idle for 30 days or more may be deemed abandoned and become eligible for suspension or termination.

要点：

- 只看**资源利用率**，不看进程是否存在。挂一个空转进程不影响指标。
- 三条是 **AND**：全部低于阈值才判 idle。
- 本机是 `VM.Standard.E2.1.Micro`，**内存那条不适用**；网络 15 天累计 RX/TX 约 4.4 GB，平均约 20 kbps，离 20% 门槛差两个数量级 → 实际只需顶住 CPU。
- 95 百分位读的是"第 95 百分位那个值"，不是平均值。要让这个数超过 20%，需要约 5% 以上的采样点落在高负载 —— 偶尔跑一下不够，7 天里约需 8.4 小时。

### 不确定性（官方未说明，别当成事实）

- E2.1.Micro 的 CPU 利用率分母是 1/8 OCPU 基线还是整机 vCPU，文档没写。下面按保守假设（分母 = vCPU）取参。
- "升级成 PAYG 账户可免回收"只是社区共识，官方 FAQ 未确认。
- 官方没承诺回收前的通知或宽限期。唯一可靠反馈是 **OCI 控制台 → 实例 → Metrics → CPU utilization**（从 VM 内部读不到 OCI 的 host metrics）。

### 保活实现

`oci-keepalive.timer` → `oci-keepalive.service`。仓库内源文件：`scripts/systemd/oci-keepalive.{service,timer}` + 负载脚本 `scripts/oci_keepalive.py`，测试 `tests/test_oci_keepalive.py`。

| 项 | 值 |
|---|---|
| 触发 | 每天 `00:30 GMT`，跑 3.5 小时（`12600` 秒） |
| 负载 | `CPUQuota=50%` → 约 0.5 vCPU，即整机 2 vCPU 的 ~25% |
| 实测配额效果 | 配额 30% 时单位用量 0.298 vCPU，机器侧仅多 0.03 vCPU 基线 |
| 内存 | `MemoryMax=64M`，实测峰值 **2.8 MB** |
| 优先级 | `Nice=19` + `CPUWeight=10`，实测负载期间 Lab 健康检查 200、SSH 往返约 1 s |
| SELinux | 装在 `/usr/local/bin`（`bin_t`），systemd 的 `init_t` 可直接 exec —— 见下文"systemd 起不来" |

3.5 h/天 = 一天约 15% 的采样点在高位，高于 95 百分位所需的 5%，留有余量。

**调参**：`ExecStart` 里 `12600` 是持续秒数、`0.9` 是每秒内燃烧比例；`CPUQuota` 决定实际负载高度。保守些就加时长。

### 运行状态与验证

```bash
systemctl list-timers oci-keepalive.timer   # 下次触发时间
systemctl status oci-keepalive              # 运行中 / 上次结果
journalctl -u oci-keepalive                 # 历史
```

负载是不是真被算进"利用率"，只能看 OCI 控制台的 CPU 曲线，本机看不到。

### 账户级：每月登一次控制台

30 天账户闲置这条在服务器上跑负载解决不了。**约定：每月至少登一次 OCI 控制台**（登录即算活动）。

### 回滚保活

```bash
sudo systemctl disable --now oci-keepalive.timer
sudo rm /etc/systemd/system/oci-keepalive.service /etc/systemd/system/oci-keepalive.timer
sudo rm /usr/local/bin/oci_keepalive.py
sudo systemctl daemon-reload
```
## 部署了什么

```
/home/opc/cv-photonic-notes        项目源码（git archive 传的，非 git clone）
/home/opc/cv-photonic-notes/.venv  虚拟环境（约 280 MB）
/home/opc/.local/bin/{uv,uvx}      uv 0.12.18
/usr/local/bin/{uv,uvx}            同上副本（SELinux 需要，见下）
/home/opc/.local/node/bin/node     Node v22.23.2（前端 leaf 测试要用）
/home/opc/.local/share/uv/python/  uv 托管的 CPython 3.12.14
```

| 工具 | 版本 | 说明 |
|---|---|---|
| Python | 3.12.14 | uv 托管。系统自带的是 3.9.25，**不满足** `requires-python = ">=3.10,<3.15"` |
| uv | 0.12.18 | `~/.local/bin` 与 `/usr/local/bin` 各一份 |
| Node | v22.23.2 | 与 CI 的 `frontend` job 一致（CI 钉 node 22） |

安装的依赖分组：**base + dev + lab**。跳过了三个重量级 extra：

```bash
# 需要时再装（jax 的 jaxlib 很大）
cd ~/cv-photonic-notes && uv sync --extra jax --extra gbs
```

- 跳过 `jax`：导致 `tests/test_backend.py`、`tests/test_fock_ad_f4.py` 的部分用例 skip
- 跳过 `gbs`（thewalrus）：导致 `tests/test_walrus.py` skip
- 跳过 `sf`（strawberryfields）：非运行时依赖

## Lab 服务（公网）

```
公网地址   http://<SERVER_IP>:8000
systemd    cvsim-lab.service   (enabled，开机自启)
绑定       0.0.0.0:8000
```

```bash
sudo systemctl status cvsim-lab      # 状态
sudo journalctl -u cvsim-lab -f      # 日志
sudo systemctl restart cvsim-lab     # 重启
```

### ⚠️ 这个服务没有任何鉴权

搜遍 `cvsim/lab/*.py` 确认：**没有 token、没有中间件、没有 CORS 配置、没有 TLS**。公网任何人访问该地址都能直接提交计算。别人能：

- 消耗你 2 核的 CPU（实测最重合法请求 `cutoff=30, view.n=512, lim=50` 约 0.39s CPU）
- 看到你提交的电路参数与返回结果（明文 HTTP）

已加的两层护栏（写在 unit 里，可随时撤）：

```ini
# uvicorn：限制并发与空闲连接，避免一个客户端占满 worker 饿死 sshd
--limit-concurrency 32 --timeout-keep-alive 5 --timeout-graceful-shutdown 10

# cgroup：上限低于物理内存才会生效（498M 的机器，服务实测峰值 87 MB）
MemoryMax=300M
MemorySwapMax=1G
OOMScoreAdjust=200
```

**参数边界（实测）** —— 唯一无上界的是 `nmode`，但 numpy 自己兜住了：

| 参数 | 上限 | 代码位置 |
|---|---|---|
| `view.n` | 2–512 | `cvsim/lab/ir.py:252` |
| `cutoff` | 1–30 | `cvsim/lab/schema.py:146` |
| `view.lim` | ≤ 50 | `cvsim/lab/ir.py:248` |
| `shots` | ≤ 100000 | `cvsim/lab/schema.py:155` |
| `rounds` | ≤ 100 | `cvsim/lab/schema.py:156` |
| `nmode` | **无上界**（只查 `>= 1`） | `cvsim/fock/circuit.py:252` |

`nmode` 实压测结果：`8`/`16` → 500；`32`/`64` → 422 `array is too big`；`200` → 422 `maximum supported dimension for an ndarray is currently 64`。内存全程 83 MB 不动。

### 静态资源挂在根路径

`server.py` 末行是 `app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True))`，所以：

```
GET /            → index.html
GET /app.js      → 静态 JS
GET /style.css   → 静态 CSS
```

**不是** `/static/app.js`（那样会 404）。

## 本机开发的地址不同

```bash
uv run python -m cvsim.lab     # 只绑 127.0.0.1:8000，仅本机可访问
```

`cvsim/lab/__main__.py` 里 `host` 是硬编码的 `"127.0.0.1"`。要对外必须用 systemd 那份配置（绑 `0.0.0.0`），或 SSH 端口转发：

```bash
ssh -L 8000:127.0.0.1:8000 oracle1
```

## 测试

```bash
cd ~/cv-photonic-notes
uv run pytest -q                        # 完整套件（约 15 分钟）
uv run pytest tests/test_lab_golden.py  # 单独看 golden
uv run ruff check cvsim tests examples scripts
node --test tests/*.test.mjs            # 前端 leaf 测试（需要 node）
```

实测基线（2026-09-23，Python 3.12.14）：

```
pytest     : 1574 passed / 6 failed / 85 skipped
前 端 leaf : 207 passed
ruff       : All checks passed
```

**6 个 failed 全部在 `tests/test_lab_golden.py`，是跨平台浮点差异，不是代码 bug。**

goldens 在 Windows 上生成，服务器是 Linux 的 OpenBLAS，BLAS/LAPACK 后端不同导致末位 ULP 漂移。量化结果：

```
1027 处数值差异
  在 1e-15 内收敛:  246/1027
  在 1e-13 内收敛: 1027/1027    ← 全部收敛
  最大相对误差: 2.143e-14       （1 ULP ≈ 2.2e-16）
```

测试用精确相等实现"锁定 wire-shape 漂移"的意图。这个测试**在 Linux CI 上应当同样失败**，但 CI 的 `test` job 只在 ubuntu 跑、goldens 却来自 Windows，属于项目自身的跨平台盲点。**未修改任何测试**，要不要改成 `math.isclose` / 或为 Linux 单独锁一套 goldens 是项目决策。

85 个 skip 来自未安装的 extra：`jax not installed`、`could not import 'thewalrus'`。

## 踩过的坑（重建时必读）

### 1. `dnf` 会把整机打挂 —— 已修

`dnf-makecache.timer`（系统自带，每小时跑一次）在 498 MiB 的机器上做 `dnf makecache`，Python 进程吃 327 MB，直接触发内核全局 OOM。OOM 期间整机 swap 抖动，**连 sshd 的 banner 都发不出来**（表现为 SSH 连接卡死）。

boot 内共 4 次 OOM，其中 2 次来自 SSH 会话里的手工 `sudo dnf`（走 `user.slice`），1 次来自定时器（走 `system.slice/dnf-makecache.service`）。

已做的修复：

```bash
# 1. 停掉定时器（反正永远失败）
sudo systemctl disable --now dnf-makecache.timer
sudo systemctl reset-failed dnf-makecache.service

# 2. 加 4G swap —— 这才是真解药
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

```
/etc/systemd/system/dnf-makecache.service.d/memory-cap.conf
    MemoryMax=400M        MemorySwapMax=3G      OOMScoreAdjust=500

/etc/systemd/system/user.slice.d/memory-cap.conf
    MemoryHigh=300M       MemoryMax=450M        MemorySwapMax=3G
```

**两条关键教训**：

- **cgroup 上限必须低于物理内存才会生效**。曾设 `MemoryMax=600M`，而机器只有 498 MiB —— 上限永远触发不了，内核全局 OOM 抢先。实测 dnf 峰值 341 MB，才定到 400M。
- **`MemorySwapMax=0` 会重现原 bug**。它把进程钉死在 RAM 里。实测 dnf 需要 2665 MB swap，所以设 3G。
- `user.slice` 用 **`MemoryHigh`（软限，节流不杀）** 而非硬限。因为 498 − 190（系统基线）≈ 300 MB 可用，而 dnf 需要 341 MB —— 任何"允许 dnf 跑通"的硬上限都必然超过物理内存，于是永远失效。软限让会话里跑重活变慢，但不被杀。

`fstab` 改动前有备份：`/etc/fstab.bak-20260923-021622`。

### 2. systemd 起不来 —— SELinux 拦的，不是文件权限

报错 `Failed to locate executable ... Permission denied`（`status=203/EXEC`）**与文件权限无关**。真正原因是 SELinux（`Enforcing`）的标签：

```
systemd 服务的域   system_u:system_r:init_t:s0
~/.local/bin/uv    标签 user_tmp_t   ← init_t 无法 exec
venv python        标签 data_home_t  ← init_t 无法 exec
```

`ausearch` 能抓到明确的 AVC denial（`avc: denied { execute } ... tclass=file permissive=0`）。

两处修法并用：

1. `uv` 复制到 `/usr/local/bin`（标签自动变为 `bin_t`，任何域可 exec）
2. `ExecStart` 用 `/bin/bash -c '...'` 包一层 —— bash 是 `shell_exec_t`，由它去启动 venv python

```
ExecStart=/bin/bash -c 'exec $HOME/cv-photonic-notes/.venv/bin/python -m uvicorn cvsim.lab.server:app ...'
```

顺带解决了另一个问题：`.venv/bin/python` 是符号链接，指向 `~/.local/share/uv/python/cpython-3.12.../python3.12`，直接指向它同样会被 systemd 拒。

### 3. 别在 SSH 会话里跑长脚本

这台机器上，跑耗时超过几分钟的脚本时 SSH 连接容易 `Connection reset`（内存抖动导致 sshd 拿不到 CPU）。可靠做法是**完全脱离**再轮询结果：

```bash
scp script.sh oracle1:/tmp/ && ssh oracle1 "setsid nohup bash /tmp/script.sh </dev/null >/tmp/out 2>&1 & echo LAUNCHED"
# 之后用短连接轮询 /tmp/out
```

### 4. 传代码用 `git archive`，不要直接传目录

本机项目目录 1.14 GB / 34009 文件，其中 `.venv` 910 MB + `.mypy_cache` 197 MB 都是可重生成的。只传 git 跟踪的 343 文件：

```bash
git archive --format=tar.gz -o /tmp/src.tar.gz HEAD   # 1.28 MB
scp /tmp/src.tar.gz oracle1:/tmp/ && ssh oracle1 "mkdir -p ~/cv-photonic-notes && tar -xzf /tmp/src.tar.gz -C ~/cv-photonic-notes"
```

Windows 上的 venv 在 Linux 用不了，必须重建。

## 防火墙

```
firewalld public 区：ports: 8000/tcp   （永久规则）
SSH 22：通过 services: ssh 放行
```

OCI 侧 Security List 也已放行 8000（无需改云控制台）。

```bash
# 查看
sudo firewall-cmd --list-all --zone=public
# 关掉 8000
sudo firewall-cmd --permanent --zone=public --remove-port=8000/tcp && sudo firewall-cmd --reload
```

## 回滚全部改动

```bash
# Lab 服务下线
sudo systemctl disable --now cvsim-lab
sudo rm /etc/systemd/system/cvsim-lab.service && sudo systemctl daemon-reload

# 防火墙收回
sudo firewall-cmd --permanent --zone=public --remove-port=8000/tcp && sudo firewall-cmd --reload

# 内存加固还原
sudo systemctl enable --now dnf-makecache.timer
sudo rm -rf /etc/systemd/system/dnf-makecache.service.d /etc/systemd/system/user.slice.d
sudo systemctl daemon-reload
sudo swapoff /swapfile && sudo rm /swapfile
sudo cp /etc/fstab.bak-20260923-021622 /etc/fstab
```

## 已知遗留问题

1. **`mcelog.service` 会失败**（`enabled` 但 CPU 不支持）：
   ```
   mcelog: ERROR: AMD Processor family 25: mcelog does not support this processor.
           Please use the edac_mce_amd module instead.
   ```
   与本项目无关，只是让 `systemctl is-system-running` 显示 `degraded`。要清干净：`sudo systemctl disable --now mcelog.service`。

2. **OCC 自升级会复发同类内存压力**。Oracle Cloud Agent 用 `runcommand` 跑 `yum install oracle-cloud-agent-*.rpm`，同样吃 330 MB，走 `system.slice` 下的 OCC 单元 —— 两份护栏都盖不到。现在有 4G swap，能扛住不再 OOM，但机器会短暂变卡。

3. **`nmode=8/16` 返回 500 而非 422**。参数校验遗漏被当内部错误抛出，属项目侧小 bug（`cvsim` 代码问题，非部署问题）。

4. **项目目录不是 git 仓库**。用 `git archive` 传的，没带 `.git`。要在服务器上做版本管理需另建，或改用 `gh repo clone`。
