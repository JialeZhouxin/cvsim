/* 探针平台解析 — 让 CDP 探针不再硬编码 Windows Edge 路径（审计 §4.4）。

   原先 12 个探针各自写死
     const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
   与 spawn(process.cwd() + "/.venv/Scripts/uvicorn.exe")，**无 process.platform
   分支、无环境变量覆盖** → 在 ubuntu CI / macOS 上永远跑不了；端口还手工分且
   有两对撞车（8860+9224、8771+9229）。

   本模块只做一件事：把「浏览器在哪 / uvicorn 在哪 / 用哪个端口」从代码里
   挪到环境变量 + 平台默认值。探针逻辑本身零改动。

   覆盖方式：
     EDGE_PATH  浏览器可执行文件（默认按 process.platform 猜）
     UVICORN    uvicorn 可执行文件（默认 .venv 下的那个）
     PROBE_PORT / PROBE_CDP_PORT  避开撞车或并行跑多个探针
*/
"use strict";

import { existsSync } from "node:fs";

/** 平台默认的 Edge/Chromium 路径。找不到就返回裸命令名，让 PATH 决定。 */
function defaultBrowser() {
  if (process.platform === "win32") {
    const candidates = [
      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
      "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    ];
    return candidates.find((p) => existsSync(p)) || candidates[0];
  }
  if (process.platform === "darwin") {
    return "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge";
  }
  // linux: 依赖 PATH（CI 上通常是 microsoft-edge / chromium）
  return process.env.CHROME_PATH || "microsoft-edge";
}

/** 浏览器可执行文件：EDGE_PATH 优先。 */
export const EDGE = process.env.EDGE_PATH || defaultBrowser();

/** uvicorn 可执行文件：UVICORN 优先，否则 .venv 里那个（按平台选目录）。 */
export function uvicornPath() {
  if (process.env.UVICORN) return process.env.UVICORN;
  return process.platform === "win32" ? ".venv/Scripts/uvicorn.exe" : ".venv/bin/uvicorn";
}

/** 端口：环境变量优先，否则用探针自己的历史默认值（保持既有手跑习惯）。 */
export function port(fallback, envName) {
  const v = process.env[envName];
  return v ? Number(v) : fallback;
}

/** 探针 profile 目录：放系统临时目录，别往仓库根写（§4.10 同类问题）。 */
export function userDataDir(tag) {
  const tmp = process.env.TEMP || process.env.TMPDIR || "/tmp";
  return `${tmp.replace(/\/$/, "")}/${tag}`;
}

/** 启动 uvicorn（stdio ignore，与各探针原先的调用形状一致）。 */
export function spawnUvicorn(spawn, port_, extraArgs = []) {
  return spawn(uvicornPath(), [
    "cvsim.lab.server:app", "--port", String(port_), "--log-level", "warning",
    ...extraArgs,
  ], { cwd: process.cwd(), stdio: "ignore" });
}

/** 启动 headless 浏览器指向 CDP 端口。 */
export function spawnBrowser(spawn, cdpPort, { profileTag = "probe-edge", size = "1920,1200", url = "about:blank" } = {}) {
  return spawn(EDGE, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${cdpPort}`,
    `--user-data-dir=${userDataDir(profileTag)}`,
    `--window-size=${size}`,
    url,
  ], { stdio: "ignore" });
}
