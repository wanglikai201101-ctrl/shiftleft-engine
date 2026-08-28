const header = document.querySelector("[data-header]");
const traceNodes = [...document.querySelectorAll("[data-trace-node]")];
const readoutCode = document.querySelector("[data-readout-code]");
const readoutTitle = document.querySelector("[data-readout-title]");
const readoutCopy = document.querySelector("[data-readout-copy]");
const scenarioTabs = [...document.querySelectorAll("[data-scenario]")];
const scenarioPanels = [...document.querySelectorAll("[data-panel]")];
const pilotDialog = document.querySelector("[data-pilot-dialog]");
const openPilotButtons = document.querySelectorAll("[data-open-pilot]");
const closePilotButton = document.querySelector("[data-close-pilot]");
const copyPilotButton = document.querySelector("[data-copy-pilot]");
const copyStatus = document.querySelector("[data-copy-status]");

const setHeaderState = () => {
  header?.classList.toggle("is-scrolled", window.scrollY > 24);
};

setHeaderState();
window.addEventListener("scroll", setHeaderState, { passive: true });

traceNodes.forEach((node) => {
  node.addEventListener("click", () => {
    traceNodes.forEach((item) => item.classList.remove("is-active"));
    node.classList.add("is-active");

    if (readoutCode) readoutCode.textContent = node.dataset.code;
    if (readoutTitle) readoutTitle.textContent = node.dataset.title;
    if (readoutCopy) readoutCopy.textContent = node.dataset.copy;
  });
});

const activateScenario = (nextTab) => {
  const key = nextTab.dataset.scenario;

  scenarioTabs.forEach((tab) => {
    const isSelected = tab === nextTab;
    tab.setAttribute("aria-selected", String(isSelected));
    tab.tabIndex = isSelected ? 0 : -1;
  });

  scenarioPanels.forEach((panel) => {
    panel.hidden = panel.dataset.panel !== key;
  });
};

scenarioTabs.forEach((tab, index) => {
  tab.addEventListener("click", () => activateScenario(tab));

  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;

    event.preventDefault();
    const direction = ["ArrowRight", "ArrowDown"].includes(event.key) ? 1 : -1;
    const nextIndex = (index + direction + scenarioTabs.length) % scenarioTabs.length;
    const nextTab = scenarioTabs[nextIndex];
    activateScenario(nextTab);
    nextTab.focus();
  });
});

const revealElements = document.querySelectorAll(".reveal");
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (prefersReducedMotion || !("IntersectionObserver" in window)) {
  revealElements.forEach((element) => element.classList.add("is-visible"));
} else {
  const revealObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.14, rootMargin: "0px 0px -40px" }
  );

  revealElements.forEach((element) => revealObserver.observe(element));
}

const openPilot = () => {
  if (!pilotDialog) return;
  copyStatus.textContent = "";
  pilotDialog.showModal();
};

const closePilot = () => {
  pilotDialog?.close();
};

openPilotButtons.forEach((button) => button.addEventListener("click", openPilot));
closePilotButton?.addEventListener("click", closePilot);

pilotDialog?.addEventListener("click", (event) => {
  if (event.target === pilotDialog) closePilot();
});

const pilotChecklist = `ShiftLeft Engine 联合验证清单

1. 一条真实、边界清晰的业务需求
2. 与需求相关的前后端代码范围
3. 当前测试方式与主要交付痛点
4. 双方认可的准确性与可用性标准

建议验证产出：模块知识库、双向追溯图谱、变更影响范围、API/UI/E2E 测试用例。`;

const pilotChecklistWithContact = `${pilotChecklist}\n\n合作联系：wanglikai201101@gmail.com`;

copyPilotButton?.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(pilotChecklistWithContact);
    copyStatus.textContent = "已复制，可以直接发给合作伙伴。";
    copyPilotButton.textContent = "已复制联合验证清单";
    window.setTimeout(() => {
      copyPilotButton.textContent = "复制联合验证清单";
    }, 2200);
  } catch {
    copyStatus.textContent = "浏览器未允许自动复制，请手动选择上方清单。";
  }
});
