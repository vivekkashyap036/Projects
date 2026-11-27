// Reads the Server-Sent Events stream from POST /chat/stream.
// (EventSource only supports GET, so we parse the stream ourselves with fetch + ReadableStream.)
export async function streamChat({ question, employeeId, sessionId }, { onStep, onToken, onFinal }) {
  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, employee_id: employeeId, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split(/\r?\n\r?\n/); // SSE events are separated by a blank line
    buffer = events.pop();
    for (const raw of events) {
      const event = raw.match(/^event: ?(.*)$/m)?.[1];
      const data = raw.match(/^data: ?(.*)$/m)?.[1];
      if (!event || !data) continue;
      const payload = JSON.parse(data);
      if (event === "step") onStep?.(payload.node);
      if (event === "token") onToken?.(payload.text);
      if (event === "final") onFinal?.(payload);
    }
  }
}
