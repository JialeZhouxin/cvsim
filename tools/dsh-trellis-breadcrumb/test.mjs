// Self-check for dsh-trellis-breadcrumb: drives the pre-step handler with a
// fake agent/ctx. Deterministic cases run against a throwaway fixture tree;
// one smoke case runs against the live project (state-dependent, soft).
// Run: node test.mjs (exit 0 = pass).
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { apply } from "./lib/index.js";

const PROJECT = process.env.TRELLIS_BREADCRUMB_TEST_PROJECT ?? "E:/02_Projects/turingQ/cv-photonic-notes";

function makeAgent(cwd, id = "test-session") {
	return {
		session: {
			id,
			header: { cwd },
			surface: { nodes: new Set() },
			events: [] // simulated durable log; injected messages land here like the runtime's
		}
	};
}

function runPreStep(agent) {
	let handler;
	const ctx = {
		logger: { warn: () => {} },
		on: (_event, fn) => { handler = fn; }
	};
	apply(ctx);
	return handler({ agent, messages: [], signal: { throwIfAborted() {} } }, async () => ({ kind: "enter", messages: [] }));
}

function recordInjection(agent, decision, seq) {
	const message = decision.messages.at(-1);
	agent.session.events.push({ type: "user/message", seq, data: { source: message.source, content: message.content } });
	agent.session.surface.nodes.add(seq);
}

const lastText = (decision) => decision.messages.at(-1)?.content?.[0]?.text ?? null;

async function fixtureProject(workflow, sessionFile, taskStatus) {
	const dir = await mkdtemp(join(tmpdir(), "trellis-bc-"));
	await mkdir(join(dir, ".trellis", ".runtime", "sessions"), { recursive: true });
	await writeFile(join(dir, ".trellis", "workflow.md"), workflow);
	await writeFile(join(dir, ".trellis", ".runtime", "sessions", sessionFile),
		JSON.stringify({ platform: "session", current_task: "task-1" }));
	await mkdir(join(dir, "task-1"));
	await writeFile(join(dir, "task-1", "task.json"), JSON.stringify({ status: taskStatus }));
	return dir;
}

const WORKFLOW = [
	"[workflow-state:no_task]\nNo active task.\n[/workflow-state:no_task]",
	"[workflow-state:planning]\nStay in planning.\n[/workflow-state:planning]",
	"[workflow-state:in_progress]\nImplement now.\n[/workflow-state:in_progress]"
].join("\n");

const fixture = await fixtureProject(WORKFLOW, "dsh-test-session.json", "in_progress");
try {
	// 1. Injection with active task + in_progress block
	const agent = makeAgent(fixture);
	const decision = await runPreStep(agent);
	const text = lastText(decision);
	assert.ok(text !== null && text.includes("Active task: task-1"), "active task line expected");
	assert.ok(text.includes("<workflow-state:in_progress>"), "in_progress block expected");
	recordInjection(agent, decision, 1);

	// 2. Digest dedup: same state second run injects nothing
	const again = await runPreStep(agent);
	assert.ok(again.messages.length === 0, "same state must not re-inject");

	// 3. Status change planning -> in_progress re-injects (digest differs)
	const agent2 = makeAgent(fixture);
	const first = await runPreStep(agent2);
	const firstText = lastText(first);
	assert.ok(firstText !== null && firstText.includes("<workflow-state:in_progress>"), "fixture starts in_progress");
	recordInjection(agent2, first, 1);
	await writeFile(join(fixture, "task-1", "task.json"), JSON.stringify({ status: "planning" }));
	const second = await runPreStep(agent2);
	const secondText = lastText(second);
	assert.ok(secondText !== null && secondText.includes("<workflow-state:planning>"), "status change must re-inject planning");
} finally {
	await rm(fixture, { recursive: true, force: true });
}

// 4. Non-Trellis cwd → no injection
const other = makeAgent("C:/Windows");
const decision2 = await runPreStep(other);
assert.ok(decision2.messages.length === 0, "non-Trellis project must inject nothing");

// 5. Live project smoke: a workflow-state block appears (state-dependent, soft)
const live = await runPreStep(makeAgent(PROJECT));
const liveText = lastText(live);
if (liveText !== null) {
	assert.match(liveText, /<workflow-state:[A-Za-z0-9_-]+>/, "live project breadcrumb block expected");
}

console.log("PASS: injection, dedup, status-change refresh, non-Trellis silence, live smoke");
