/*
 * Niquests docs — fine-grained GA4 event tracking.
 *
 * The default sphinxcontrib-googleanalytics extension only emits the implicit
 * `page_view`. Static, anchor-driven docs barely produce any other signal,
 * which makes it impossible to tell which sections, examples, or links are
 * actually consumed.
 *
 * This script piggybacks on the existing gtag() instance and emits a handful
 * of high-signal custom events:
 *
 *   - section_view   when an <h1..h4> with an id scrolls into view
 *   - scroll_depth   at the 25 / 50 / 75 / 100 % milestones (once each)
 *   - toc_click      when an in-page TOC / sidebar link is clicked
 *   - anchor_click   when a heading permalink (¶) is clicked / copied
 *   - code_copy      when a code block is copied via the Furo copy button
 *   - outbound_click when a link to an external host is clicked
 *   - section_feedback   when the reader rates a section helpful / not helpful
 *
 * All events are best-effort: they degrade silently if gtag or the matching
 * DOM elements are unavailable.
 */
(function () {
  "use strict";

  function track(name, params) {
    if (typeof window.gtag !== "function") {
      return;
    }
    try {
      window.gtag("event", name, params || {});
    } catch (_) {
      /* never break the page over analytics */
    }
  }

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  function pagePath() {
    return location.pathname + location.search;
  }

  function trackSectionViews() {
    if (!("IntersectionObserver" in window)) {
      return;
    }
    var seen = new Set();
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) {
            return;
          }
          var el = entry.target;
          var id = el.id || (el.parentElement && el.parentElement.id);
          if (!id || seen.has(id)) {
            return;
          }
          seen.add(id);
          track("section_view", {
            section_id: id,
            section_title: (el.textContent || "").trim().slice(0, 120),
            page_path: pagePath(),
          });
        });
      },
      { rootMargin: "0px 0px -60% 0px", threshold: 0.1 }
    );

    document
      .querySelectorAll("article h1[id], article h2[id], article h3[id], article h4[id], section[id] > h1, section[id] > h2, section[id] > h3, section[id] > h4")
      .forEach(function (el) {
        observer.observe(el);
      });
  }

  function trackScrollDepth() {
    var milestones = [25, 50, 75, 100];
    var fired = new Set();

    function compute() {
      var doc = document.documentElement;
      var scrollTop = window.scrollY || doc.scrollTop || 0;
      var viewport = window.innerHeight || doc.clientHeight;
      var total = (doc.scrollHeight || document.body.scrollHeight) - viewport;
      if (total <= 0) {
        return 100;
      }
      return Math.min(100, Math.round((scrollTop / total) * 100));
    }

    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        var pct = compute();
        milestones.forEach(function (m) {
          if (pct >= m && !fired.has(m)) {
            fired.add(m);
            track("scroll_depth", {
              percent_scrolled: m,
              page_path: pagePath(),
            });
          }
        });
        ticking = false;
      });
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // ---------------------------------------------------------------- click hooks
  function trackClicks() {
    document.addEventListener(
      "click",
      function (e) {
        var a = e.target.closest && e.target.closest("a");
        if (!a) return;

        var href = a.getAttribute("href") || "";

        // Heading permalink (¶)
        if (a.classList.contains("headerlink")) {
          var section = a.parentElement && a.parentElement.id;
          track("anchor_click", {
            section_id: section || href.replace(/^#/, ""),
            page_path: pagePath(),
          });
          return;
        }

        // In-page TOC / sidebar links
        if (href.startsWith("#")) {
          track("toc_click", {
            target_id: href.slice(1),
            link_text: (a.textContent || "").trim().slice(0, 120),
            page_path: pagePath(),
          });
          return;
        }

        // Outbound links
        try {
          var url = new URL(a.href, location.href);
          if (url.host && url.host !== location.host) {
            track("outbound_click", {
              outbound_url: url.href,
              outbound_host: url.host,
              link_text: (a.textContent || "").trim().slice(0, 120),
              page_path: pagePath(),
            });
          } else {
            // Internal navigation (page-to-page)
            if (url.pathname !== location.pathname) {
              track("internal_nav", {
                target_path: url.pathname,
                link_text: (a.textContent || "").trim().slice(0, 120),
                page_path: pagePath(),
              });
            }
          }
        } catch (_) {
          /* ignore malformed hrefs */
        }
      },
      true
    );
  }

  // ---------------------------------------------------------------- code_copy
  function trackCodeCopy() {
    // Furo injects a <button class="copy"> inside <pre> blocks.
    document.addEventListener(
      "click",
      function (e) {
        var btn = e.target.closest && e.target.closest("button.copy, .copybtn");
        if (!btn) return;

        var pre = btn.closest("pre, div.highlight");
        var lang = "";
        if (pre) {
          var cls = pre.className || "";
          var m = cls.match(/highlight-(\w+)/) || cls.match(/language-(\w+)/);
          if (m) lang = m[1];
        }

        // Find the nearest section heading for context.
        var section = "";
        var sec = btn.closest("section, article");
        if (sec && sec.id) {
          section = sec.id;
        }

        track("code_copy", {
          language: lang || "unknown",
          section_id: section,
          page_path: pagePath(),
        });
      },
      true
    );
  }

  // Renders a tiny "Was this section helpful?" widget under every <h2> /
  // <h3> heading and reports the verdict to GA. We keep a per-section flag
  // in localStorage so a single visitor can't pollute the metric by spamming
  // the buttons (one vote per section per browser).
  function trackSectionFeedback() {
    var STORAGE_KEY = "niquests-docs-feedback";
    var store;
    try {
      store = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    } catch (_) {
      store = {};
    }

    function persist() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
      } catch (_) {
        /* private mode / quota exceeded — ignore */
      }
    }

    function keyFor(sectionId) {
      return location.pathname + "#" + sectionId;
    }

    function build(section) {
      var sectionId = section.id;
      if (!sectionId) return null;

      var wrapper = document.createElement("div");
      wrapper.className = "niq-feedback";
      wrapper.setAttribute("data-section-id", sectionId);

      var label = document.createElement("span");
      label.className = "niq-feedback__label";
      label.textContent = "Was this helpful?";

      var up = document.createElement("button");
      up.type = "button";
      up.className = "niq-feedback__btn niq-feedback__btn--up";
      up.setAttribute("aria-label", "Mark this section as helpful");
      up.innerHTML = "<span aria-hidden=\"true\">\uD83D\uDC4D</span>";

      var down = document.createElement("button");
      down.type = "button";
      down.className = "niq-feedback__btn niq-feedback__btn--down";
      down.setAttribute("aria-label", "Mark this section as not helpful");
      down.innerHTML = "<span aria-hidden=\"true\">\uD83D\uDC4E</span>";

      var ack = document.createElement("span");
      ack.className = "niq-feedback__ack";
      ack.setAttribute("role", "status");

      wrapper.appendChild(label);
      wrapper.appendChild(up);
      wrapper.appendChild(down);
      wrapper.appendChild(ack);

      function vote(value) {
        var k = keyFor(sectionId);
        if (store[k]) {
          // Visitor already voted — let them change their mind silently
          // but only emit a new event if the verdict actually flipped.
          if (store[k] === value) {
            return;
          }
        }
        store[k] = value;
        persist();

        wrapper.classList.add("niq-feedback--voted");
        wrapper.classList.toggle("niq-feedback--up", value === "up");
        wrapper.classList.toggle("niq-feedback--down", value === "down");
        ack.textContent =
          value === "up" ? "Thanks for the feedback!" : "Thanks — we'll improve this.";

        track("section_feedback", {
          section_id: sectionId,
          section_title: (function () {
            var h = section.querySelector("h1, h2, h3, h4");
            return h ? (h.textContent || "").replace(/¶$/, "").trim().slice(0, 120) : "";
          })(),
          verdict: value, // "up" | "down"
          page_path: pagePath(),
        });
      }

      up.addEventListener("click", function () {
        vote("up");
      });
      down.addEventListener("click", function () {
        vote("down");
      });

      // Restore prior vote (visual only — does NOT re-emit the event).
      var prior = store[keyFor(sectionId)];
      if (prior) {
        wrapper.classList.add("niq-feedback--voted");
        wrapper.classList.toggle("niq-feedback--up", prior === "up");
        wrapper.classList.toggle("niq-feedback--down", prior === "down");
        ack.textContent = "You already rated this section.";
      }

      return wrapper;
    }

    // Attach to every "real" content section (skip the page-level h1).
    document
      .querySelectorAll("article section section[id], article > section section[id]")
      .forEach(function (section) {
        // Only attach to sections whose first child is an h2/h3 heading —
        // i.e. genuine content sections, not arbitrary anchored wrappers.
        var heading = section.querySelector(":scope > h2, :scope > h3");
        if (!heading) return;
        var widget = build(section);
        if (!widget) return;
        section.appendChild(widget);
      });
  }

  ready(function () {
    trackSectionViews();
    trackScrollDepth();
    trackClicks();
    trackCodeCopy();
    trackSectionFeedback();
  });
})();
