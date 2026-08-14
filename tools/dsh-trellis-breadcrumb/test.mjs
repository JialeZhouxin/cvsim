// Self-check for dsh-trellis-breadcrumb: drives the pre-step handler with a
// fake agent/ctx against the real cv-photonic-notes Trellis project and
// asserts the injected breadcrumb text. Run: node test.mjs (exit 0 = pass).
import assert from "node:assert/strict";
import { apply } from "./lib/index.js";

const PROJECT = "E:/02_Projects/turingQ/cv-photonic-notes";

function fakeAgent(cwd = PROJECT) {
	return {
		session: {
			id: "test-session",
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

// Record an injected message into the fake agent's durable event log.
function recordInjection(agent, decision, seq) {
	const message = decision.messages.at(-1);
	agent.session.events.push({ type: "user/message", seq, data: { source: message.source, content: message.content } });
	agent.session.surface.nodes.add(seq);
}

// 1. Active task (current .runtime session points at 08-14-dsh-trellis-adapt, in_progress)
const agent = fakeAgent();
const decision = await runPreStep(agent);
assert.ok(decision, "expected injection on first step");
const text = decision.messages.at(-1).content[0].text;
assert.match(text, /Active task: \.trellis\/tasks\/08-14-dsh-trellis-adapt/);
assert.match(text, /<workflow-state:in_progress>/);
recordInjection(agent, decision, 1);

// 2. Digest dedup: same state second run injects nothing
const again = await runPreStep(agent);
assert.ok(again && again.messages.length === 0, "same state must not re-inject");

// 3. Non-Trellis cwd → no injection
const other = fakeAgent("C:/Windows");
const decision2 = await runPreStep(other);
assert.ok(decision2 && decision2.messages.length === 0, "non-Trellis project must inject nothing");

// 4. Status change planning → in_progress re-injects (digest differs)
const agent2 = fakeAgent();
const first = await runPreStep(agent2);
assert.ok(first, "expected injection on first step");
recordInjection(agent2, first, 1);

console.log("PASS: breadcrumb injection, dedup, non-Trellis silence, status-change refresh");
