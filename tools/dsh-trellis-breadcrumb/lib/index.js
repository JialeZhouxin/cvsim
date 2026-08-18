// Trellis workflow-state breadcrumb for DeepSeek Harness.
//
// At every agent pre-step, resolves the active Trellis task from
// `.trellis/.runtime/sessions/` and injects the matching
// `[workflow-state:STATUS]` block from `.trellis/workflow.md` as a durable
// user-role message — the DSH equivalent of Trellis' UserPromptSubmit hook
// (inject-workflow-state.py). Non-Trellis projects get zero output; failures
// of this plugin's own logic fail open (log + no injection), upstream
// failures propagate.
//
// Convention: DSH sessions run trellis scripts with
// `TRELLIS_CONTEXT_ID=dsh-<session.id>` so the runtime session file is
// `dsh-<session.id>.json`; that file wins regardless of mtime, other files
// fall back by newest (single-user local).

import { createHash } from "node:crypto";
import { readdir, readFile, stat } from "node:fs/promises";
import { dirname, join, resolve, sep } from "node:path";
import { createUserMessage } from "@deepseek-ai/dsh-llm";

export const name = "trellis-breadcrumb";
export const inject = ["agents"];
// cordis rc.6 requires Config to implement the Standard Schema interface
// (cordis resolveConfig: runtime.Config["~standard"].validate(config)).
export const Config = {
	"~standard": {
		version: 1,
		vendor: "trellis-breadcrumb",
		validate: (value) => ({ value })
	}
};

const WORKFLOW_TAG = /\[workflow-state:([A-Za-z0-9_-]+)\]([\s\S]*?)\[\/workflow-state:\1\]/g;
const FALLBACK = "Refer to workflow.md for current step.";
const digest = (text) => createHash("sha256").update(text).digest("hex");

export function apply(ctx) {
	ctx.on("agent/pre-step", async ({ agent, messages, signal }, next) => {
		const decision = await next();
		if (decision.kind === "reject") return decision;
		signal.throwIfAborted();
		try {
			const text = await renderBreadcrumb(agent);
			if (text === null) return decision;
			if (visibleDigest(agent) === digest(text)) return decision;
			const message = createUserMessage({
				content: [{ type: "text", text }],
				source: { kind: "trellis-breadcrumb", form: "text" }
			});
			const index = decision.messages.findIndex((m) => m.source?.kind === "trellis-breadcrumb");
			return {
				kind: "enter",
				messages: index >= 0
					? decision.messages.map((m, i) => (i === index ? message : m))
					: [...decision.messages, message]
			};
		} catch (error) {
			ctx.logger?.warn?.(`trellis-breadcrumb: ${error?.message ?? error}`);
			return decision;
		}
	});
}

/** Breadcrumb text for the agent's session, or null when not a Trellis project. */
async function renderBreadcrumb(agent) {
	const root = await findTrellisRoot(agent.session.header.cwd);
	if (root === null) return null;
	const workflow = await readFile(join(root, ".trellis", "workflow.md"), "utf8").catch(() => null);
	if (workflow === null) return null;
	const blocks = new Map();
	for (const match of workflow.matchAll(WORKFLOW_TAG)) {
		blocks.set(match[1], match[2].trim());
	}
	const activeTask = await resolveActiveTask(root, agent.session.id);
	let status = activeTask === null ? "no_task" : "planning";
	if (activeTask !== null) {
		const taskPath = contained(root, activeTask);
		if (taskPath !== null) {
			const taskJson = await readFile(join(taskPath, "task.json"), "utf8").catch(() => null);
			if (taskJson !== null) {
				try {
					status = JSON.parse(taskJson).status ?? "planning";
				} catch {
					status = "planning";
				}
			}
		}
	}
	const body = blocks.get(status) ?? FALLBACK;
	const block = `<workflow-state:${status}>\n${body}\n</workflow-state:${status}>`;
	return activeTask === null ? block : `Active task: ${activeTask}\n${block}`;
}

/** Resolve a repo-relative task path and require containment under root. */
function contained(root, relPath) {
	const target = resolve(root, relPath);
	const prefix = root.endsWith(sep) ? root : root + sep;
	return target === root || target.startsWith(prefix) ? target : null;
}

/** Nearest ancestor of cwd containing `.trellis/workflow.md`, or null. */
async function findTrellisRoot(cwd) {
	let dir = cwd;
	for (;;) {
		if (await readFile(join(dir, ".trellis", "workflow.md"), "utf8").then(() => true).catch(() => false)) {
			return dir;
		}
		const parent = dirname(dir);
		if (parent === dir) return null;
		dir = parent;
	}
}

/**
 * Active task path from `.trellis/.runtime/sessions/`. The session file
 * matching `dsh-<session.id>` wins regardless of mtime; otherwise the newest
 * file decides (single-user fallback).
 */
async function resolveActiveTask(root, sessionId) {
	const sessionsDir = join(root, ".trellis", ".runtime", "sessions");
	const files = await readdir(sessionsDir).catch(() => null);
	if (files === null) return null;
	const jsons = files.filter((file) => file.endsWith(".json"));
	const preferred = `dsh-${sessionId}.json`;
	const infos = (await Promise.all(jsons.map(async (file) => {
		const info = await stat(join(sessionsDir, file)).catch(() => null);
		return info === null ? null : { file, mtime: info.mtimeMs };
	}))).filter((entry) => entry !== null);
	infos.sort((a, b) => {
		if (a.file === preferred) return -1;
		if (b.file === preferred) return 1;
		return b.mtime - a.mtime;
	});
	for (const { file } of infos) {
		const data = await readFile(join(sessionsDir, file), "utf8").then(JSON.parse).catch(() => null);
		if (data !== null && typeof data.current_task === "string" && data.current_task !== "") {
			return data.current_task;
		}
	}
	return null;
}

/** Digest of the last visible breadcrumb message in session history, or null. */
function visibleDigest(agent) {
	const visible = new Set(agent.session.surface.nodes);
	for (let index = agent.session.events.length - 1; index >= 0; index -= 1) {
		const event = agent.session.events[index];
		if (event.type !== "user/message" || event.data.source?.kind !== "trellis-breadcrumb") continue;
		if (!visible.has(event.seq)) continue;
		const block = event.data.content.find((part) => part.type === "text");
		if (block === undefined) return null;
		return digest(block.text);
	}
	return null;
}
