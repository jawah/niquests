/* Progressive terminal examples inspired by termynal.js (MIT). */
(function () {
  "use strict";

  const rootSelector = ".termy";
  const inputPrefixes = [
    [">>> ", ">>>"],
    ["... ", "..."],
    ["$ ", "$"],
  ];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  function transcriptLines(text) {
    const normalized = text.replace(/\r\n?/g, "\n").replace(/\n$/, "");
    return normalized.split("\n").map((source) => {
      for (const [prefix, prompt] of inputPrefixes) {
        if (source.startsWith(prefix)) {
          return { kind: "input", prompt, value: source.slice(prefix.length) };
        }
      }
      return { kind: "output", value: source };
    });
  }

  function sourceBlock(pre) {
    const highlight = pre.closest(".highlight");
    if (!highlight) return pre;
    const outer = highlight.parentElement;
    if (outer && [...outer.classList].some((name) => name.startsWith("highlight-"))) {
      return outer;
    }
    return highlight;
  }

  function button(label, action) {
    const element = document.createElement("button");
    element.className = "termynal-control";
    element.type = "button";
    element.dataset.action = action;
    element.textContent = label;
    return element;
  }

  function createTerminal(root, pre) {
    const text = pre.textContent || "";
    const data = transcriptLines(text);
    const terminal = document.createElement("div");
    terminal.dataset.termynal = "";

    const toolbar = document.createElement("div");
    toolbar.className = "termynal-toolbar";
    toolbar.innerHTML = '<span class="termynal-dots" aria-hidden="true"></span>' +
      '<span class="termynal-title">Python console</span>';

    const controls = document.createElement("div");
    controls.className = "termynal-controls";
    const copy = button("Copy", "copy");
    const finish = button("Finish", "finish");
    const replay = button("Replay", "replay");
    replay.hidden = true;
    controls.append(copy, finish, replay);
    toolbar.appendChild(controls);

    const body = document.createElement("div");
    body.className = "termynal-body";
    body.setAttribute("aria-hidden", "true");
    body.style.minHeight = `${Math.max(data.length, 1) * 1.55 + 2.15}em`;

    const lines = data.map((item) => {
      const line = document.createElement("span");
      line.className = "termynal-line";
      line.dataset.ty = item.kind === "input" ? "input" : "";
      if (item.prompt) line.dataset.tyPrompt = item.prompt;
      line.dataset.value = item.value;
      line.hidden = true;
      body.appendChild(line);
      return line;
    });

    const accessible = document.createElement("pre");
    accessible.className = "termynal-sr-only";
    accessible.textContent = text;

    terminal.append(toolbar, body, accessible);
    root.appendChild(terminal);
    sourceBlock(pre).style.display = "none";

    return {
      body,
      copy,
      data,
      finish,
      lines,
      replay,
      run: 0,
      terminal,
    };
  }

  function wait(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
  }

  function revealAll(state) {
    state.run += 1;
    for (const line of state.lines) {
      line.hidden = false;
      line.classList.remove("termynal-cursor");
      line.textContent = line.dataset.value;
    }
    state.finish.hidden = true;
    state.replay.hidden = false;
  }

  async function typeLine(state, line, run) {
    const value = line.dataset.value || "";
    line.hidden = false;
    line.textContent = "";
    line.classList.add("termynal-cursor");
    for (const character of value) {
      if (run !== state.run || state.finish.hidden) return;
      line.textContent += character;
      await wait(22);
    }
    line.classList.remove("termynal-cursor");
  }

  async function play(state) {
    state.run += 1;
    const run = state.run;
    state.finish.hidden = false;
    state.replay.hidden = true;
    for (const line of state.lines) {
      line.hidden = true;
      line.textContent = "";
      line.classList.remove("termynal-cursor");
    }

    if (reduceMotion.matches) {
      revealAll(state);
      return;
    }

    await wait(180);
    for (const line of state.lines) {
      if (run !== state.run || state.finish.hidden) return;
      if (line.dataset.ty === "input") {
        await typeLine(state, line, run);
        await wait(90);
      } else {
        line.hidden = false;
        line.textContent = line.dataset.value;
        await wait(line.dataset.value ? 75 : 20);
      }
    }
    if (run === state.run) {
      state.finish.hidden = true;
      state.replay.hidden = false;
    }
  }

  async function copyInputs(state) {
    const value = state.data
      .filter((line) => line.kind === "input")
      .map((line) => line.value)
      .join("\n");
    try {
      await navigator.clipboard.writeText(value);
      state.copy.textContent = "Copied";
      window.setTimeout(() => { state.copy.textContent = "Copy"; }, 1200);
    } catch (_) {
      state.copy.textContent = "Unavailable";
      window.setTimeout(() => { state.copy.textContent = "Copy"; }, 1200);
    }
  }

  function bind(state) {
    state.terminal.addEventListener("click", (event) => {
      const control = event.target.closest("[data-action]");
      if (!control) return;
      if (control.dataset.action === "finish") revealAll(state);
      if (control.dataset.action === "replay") play(state);
      if (control.dataset.action === "copy") copyInputs(state);
    });
  }

  function setup() {
    const roots = [...document.querySelectorAll(rootSelector)];
    if (!roots.length) return;

    const states = roots.flatMap((root) => {
      const pre = root.querySelector(".highlight pre");
      if (!pre) return [];
      const state = createTerminal(root, pre);
      bind(state);
      return [state];
    });

    if (!("IntersectionObserver" in window)) {
      states.forEach(play);
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const state = states.find((candidate) => candidate.terminal === entry.target);
        if (state) play(state);
        observer.unobserve(entry.target);
      }
    }, { rootMargin: "120px 0px" });

    states.forEach((state) => observer.observe(state.terminal));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup, { once: true });
  } else {
    setup();
  }
})();
