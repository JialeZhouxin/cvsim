// Trellis workflow-state breadcrumb for DeepSeek Harness.
//
// At every agent pre-step, resolves the active Trellis task from
// `.trellis/.runtime/sessions/` and injects the matching
// `[workflow-state:STATUS]` block from `.trellis/workflow.md` as a durable
// user-role message — the DSH equivalent of Trellis' UserPromptSubmit hook
// (inject-workflow-state.py). Non-Trellis projects get zero output; failures
// fail open (log + no injection).
//
// Convention: DSH sessions run trellis scripts with
// `TRELLIS_CONTEXT_ID=dsh-<session.id>` so the runtime session file is
// `dsh-<session.id>.json`; when absent, the newest session file wins
// (single-user local fallback).

import { createHash } from "node:crypto";
import { readdir, readFile, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { createUserMessage } from "@deepseek-ai/dsh-llm";

export const name = "trellis-breadcrumb";
export const inject = ["agents"];
export const Config = {};

const WORKFLOW_TAG = /\[workflow-state:([A-Za-z0-9_-]+)\]([\s\S]*?)\[\/workflow-state:\1\]/g;
const FALLBACK = "Refer to workflow.md for current step.";

export function apply(ctx) {
	ctx.on("agent/pre-step", async ({ agent, messages, signal }, next) => {
		let decision;
		try {
			decision = await next();
			if (decision.kind === "reject") return decision;
			signal.throwIfAborted();
			const text = await renderBreadcrumb(agent);
			if (text === null) return decision;
			const digest = createHash("sha256").update(text).digest("hex");
			if (visibleDigest(agent) === digest) return decision;
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
			return decision ?? { kind: "enter", messages };
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
	let status = "no_task";
	if (activeTask !== null) {
		const taskJson = await readFile(join(root, activeTask, "task.json"), "utf8").catch(() => null);
		if (taskJson !== null) {
			try {
				status = JSON.parse(taskJson).status ?? "planning";
			} catch {
				status = "planning";
			}
		}
	}
	const body = blocks.get(status) ?? FALLBACK;
	const block = `<workflow-state:${status}>\n${body}\n</workflow-state:${status}>`;
	return activeTask === null ? block : `Active task: ${activeTask}\n${block}`;
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
 * Active task path from `.trellis/.runtime/sessions/`, preferring the
 * `dsh-<session.id>.json` file, else the newest session file.
 */
async function resolveActiveTask(root, sessionId) {
	const sessionsDir = join(root, ".trellis", ".runtime", "sessions");
	const files = await readdir(sessionsDir).catch(() => null);
	if (files === null) return null;
	const jsons = files.filter((file) => file.endsWith(".json"));
	const preferred = `dsh-${sessionId}.json`;
	const ordered = jsons.includes(preferred)
		? [preferred, ...jsons.filter((file) => file !== preferred)]
		: jsons;
	const entries = [];
	for (const file of ordered) {
		const info = await stat(join(sessionsDir, file)).catch(() => null);
		if (info !== null) entries.push({ file, mtime: info.mtimeMs });
	}
	entries.sort((a, b) => b.mtime - a.mtime);
	for (const { file } of entries) {
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
		return createHash("sha256").update(block.text).digest("hex");
	}
	return null;
}
