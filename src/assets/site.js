// Advenue digital: shared behaviour for every page. Page-specific parts run only
// when their elements exist, so one file serves the whole site.
(function () {
  // Customer journey: four stages on one baseline, the customer hops between them.
  if (document.getElementById("nodes")) (function () {
    var xs = [70, 210, 350, 490], baseY = 160, hopH = 95;
    var colors = ["#198fd9", "#198fd9", "#3e5fc4", "#65bd7d"];
    var nodes = document.getElementById("nodes");
    var still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var ns = "http://www.w3.org/2000/svg";
    var rings = xs.map(function (x, i) {
      var ring = document.createElementNS(ns, "circle");
      ring.setAttribute("cx", x); ring.setAttribute("cy", baseY); ring.setAttribute("r", 16);
      ring.setAttribute("fill", colors[i]); ring.setAttribute("opacity", "0.18");
      var dot = document.createElementNS(ns, "circle");
      dot.setAttribute("cx", x); dot.setAttribute("cy", baseY); dot.setAttribute("r", 9);
      dot.setAttribute("fill", colors[i]);
      nodes.appendChild(ring); nodes.appendChild(dot);
      return ring;
    });

    // Each hop follows the dashed arc (x linear, y a parabola); short pause on every landing.
    // Rests on the last stage when motion is reduced.
    var pulse = document.getElementById("pulse");
    function place(x, y) { pulse.setAttribute("cx", x); pulse.setAttribute("cy", y); }
    if (still) { place(xs[3], baseY); } else {
      var hop = 650, rest = 450, end = 1200;
      var cycle = 3 * (hop + rest) + end, start = null;
      (function tick(ts) {
        if (start === null) start = ts;
        var t = (ts - start) % cycle, at = 0, landed = -1, since = 0;
        for (var i = 0; i < 3; i++) {
          var seg = t - i * (hop + rest);
          if (seg < 0) break;
          if (seg < rest) { at = i; landed = i; since = seg; break; }
          if (seg < rest + hop) {
            var k = (seg - rest) / hop;
            place(xs[i] + (xs[i + 1] - xs[i]) * k, baseY - 4 * hopH * k * (1 - k));
            at = -1; break;
          }
          at = i + 1; landed = i + 1; since = seg - rest - hop;
        }
        if (at >= 0) place(xs[at], baseY);
        rings.forEach(function (r, i) {
          var pop = i === landed && since < 400 ? 1 - since / 400 : 0;
          r.setAttribute("r", 16 + 10 * pop);
        });
        requestAnimationFrame(tick);
      })(performance.now());
    }
  })();

  // Budget demo: week by week the budget moves to the channel that converts best.
  if (document.getElementById("stack")) (function () {
    var weeks = [[34, 33, 33], [42, 26, 32], [49, 20, 31], [55, 15, 30]];
    var segs = document.querySelectorAll("#stack i");
    var vals = document.querySelectorAll(".alloc b");
    var weekEl = document.getElementById("alloc-week");
    function showWeek(w) {
      weeks[w].forEach(function (v, i) { segs[i].style.flexGrow = v; vals[i].textContent = v + " %"; });
      weekEl.textContent = "Týden " + (w + 1);
    }
    var still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var wk = still ? weeks.length - 1 : 0;
    showWeek(wk);
    if (!still) setInterval(function () { wk = (wk + 1) % weeks.length; showWeek(wk); }, 2200);
  })();

  // Copy buttons: data-copy names the element whose text is copied.
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    var label = btn.textContent;
    btn.addEventListener("click", function () {
      var src = document.getElementById(btn.dataset.copy);
      function done(msg) { btn.textContent = msg; setTimeout(function () { btn.textContent = label; }, 1800); }
      function fallback() {
        if (src.hidden) { done("Kopírování nejde"); return; }
        var r = document.createRange(); r.selectNodeContents(src);
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        done("Označeno, stiskněte ⌘C");
      }
      try {
        navigator.clipboard.writeText(src.textContent).then(function () { done("Zkopírováno"); }, fallback);
      } catch (e) { fallback(); }
    });
  });

  // Sticky top bar: tighten and add a hairline once the page is scrolled.
  var topbar = document.getElementById("topbar");
  function onScroll() { topbar.classList.toggle("is-scrolled", window.scrollY > 8); }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Mobile menu: the hamburger opens the links; picking one or pressing Esc closes it.
  var nav = document.querySelector(".nav");
  var menuBtn = document.getElementById("menu-btn");
  function setMenu(open) {
    nav.classList.toggle("is-open", open);
    menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
    menuBtn.setAttribute("aria-label", open ? "Zavřít menu" : "Otevřít menu");
  }
  menuBtn.addEventListener("click", function () { setMenu(!nav.classList.contains("is-open")); });
  document.getElementById("nav-links").addEventListener("click", function (e) { if (e.target.closest("a")) setMenu(false); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && nav.classList.contains("is-open")) { setMenu(false); menuBtn.focus(); } });

  // Contact form: validate, send the lead to the Make.com webhook, and fall back
  if (document.getElementById("form")) (function () {
    // to the visitor's own e-mail when no webhook is set or sending fails.
    var MAKE_WEBHOOK_URL = "https://hook.eu2.make.com/5u4simd7dhpczknq8f94xd09n8njjos0";
    var form = document.getElementById("form");
    var err = document.getElementById("form-error");
    var submitBtn = document.getElementById("form-submit");

    function showMailFallback(body) {
      document.getElementById("sent-text").textContent = body;
      document.getElementById("sent-mail").href = "mailto:info@advenue.cz?subject=" +
        encodeURIComponent("Poptávka z webu") + "&body=" + encodeURIComponent(body);
      var sent = document.getElementById("sent");
      sent.hidden = false;
      sent.scrollIntoView({ block: "nearest" });
    }

    function leadData(needs) {
      var q = new URLSearchParams(location.search);
      var data = {
        jmeno: form.elements.name.value.trim(),
        firma: form.elements.company.value.trim(),
        email: form.elements.email.value.trim(),
        telefon: form.elements.phone.value.trim(),
        sluzby: needs.join(", "),
        zprava: form.elements.message.value.trim(),
        stranka: location.href,
        odeslano: new Date().toISOString()
      };
      ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"].forEach(function (k) {
        data[k] = q.get(k) || "";
      });
      return data;
    }

    // Form-encoded body is a "simple" request: no CORS preflight, and Make parses it into fields.
    function sendToMake(data) {
      var ctrl = "AbortController" in window ? new AbortController() : null;
      var timer = ctrl && setTimeout(function () { ctrl.abort(); }, 10000);
      return fetch(MAKE_WEBHOOK_URL, {
        method: "POST",
        body: new URLSearchParams(data),
        signal: ctrl ? ctrl.signal : undefined
      }).then(function (r) {
        clearTimeout(timer);
        if (!r.ok) throw new Error("HTTP " + r.status);
      }, function (e) { clearTimeout(timer); throw e; });
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var name = form.elements.name, mail = form.elements.email;
      var problems = [];
      if (!name.value.trim()) problems.push("vyplňte jméno");
      if (!mail.value.trim() || !mail.checkValidity()) problems.push("zadejte platný e-mail");
      if (problems.length) {
        err.textContent = "Ještě prosím " + problems.join(" a ") + ".";
        (problems[0].indexOf("jméno") > -1 ? name : mail).focus();
        return;
      }
      err.textContent = "";
      var needs = Array.prototype.filter.call(form.querySelectorAll('[name="need"]'), function (c) { return c.checked; })
        .map(function (c) { return c.value; });
      var lines = [
        "Dobrý den,",
        "",
        form.elements.message.value.trim() || "mám zájem o nezávazný audit zdarma.",
        "",
        needs.length ? "Zajímá mě: " + needs.join(", ") : "",
        "",
        name.value.trim() + (form.elements.company.value.trim() ? ", " + form.elements.company.value.trim() : ""),
        mail.value.trim(),
        form.elements.phone.value.trim()
      ].filter(function (l, i, arr) { return l !== "" || arr[i - 1] !== ""; });
      var body = lines.join("\n").trim();
      var ok = document.getElementById("sent-ok");
      // Bots fill the hidden field; pretend success and send nothing.
      if (form.elements.website.value) { ok.hidden = false; return; }
      if (!MAKE_WEBHOOK_URL) { showMailFallback(body); return; }
      submitBtn.disabled = true;
      submitBtn.firstChild.nodeValue = "Odesílám… ";
      sendToMake(leadData(needs)).then(function () {
        form.reset();
        document.getElementById("sent").hidden = true;
        ok.hidden = false;
        ok.scrollIntoView({ block: "nearest" });
      }, function () {
        err.textContent = "Poptávku se nepodařilo odeslat. Pošlete nám ji prosím e-mailem, text je připravený.";
        showMailFallback(body);
      }).then(function () {
        submitBtn.disabled = false;
        submitBtn.firstChild.nodeValue = "Odeslat poptávku\n          ";
      });
    });
  })();

})();
