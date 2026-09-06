import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';
import axe from 'axe-core';

const baseUrl = process.env.SURFACE_BASE_URL ?? 'http://127.0.0.1:4174/causaganha/';
const revision = process.env.SURFACE_REVISION ?? process.env.GITHUB_SHA ?? 'unknown';
const output = process.env.SURFACE_ACCESSIBILITY_OUTPUT ?? 'captures/accessibility.json';
const routes = [
  '',
  'index.html',
  'processo.html',
  'publicacoes.html',
  'sobre.html',
  'agentes.html',
  'minhas-consultas.html',
];
const viewports = [
  { width: 1280, height: 900 },
  { width: 390, height: 844 },
];

const browser = await chromium.launch({ headless: true });
const results = [];
let failed = false;

for (const viewport of viewports) {
  const context = await browser.newContext({ viewport });
  for (const route of routes) {
    const page = await context.newPage();
    const url = new URL(route, baseUrl).toString();
    const response = await page.goto(url, { waitUntil: 'networkidle' });
    if (!response?.ok()) {
      throw new Error(`${route || '/'} respondeu HTTP ${response?.status() ?? 'sem resposta'}`);
    }

    let uiGeneration = null;
    let uiGenerationMatches = true;
    if (route === '') {
      uiGeneration = await page.locator('[data-ui-generation]').first().getAttribute('data-ui-generation');
      uiGenerationMatches = uiGeneration === 'cobogo-panda';
    }

    await page.addScriptTag({ content: axe.source });
    const violations = await page.evaluate(async () => {
      const report = await globalThis.axe.run(document, {
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'],
        },
      });
      return report.violations
        .filter((item) => item.impact === 'serious' || item.impact === 'critical')
        .map((item) => ({
          id: item.id,
          impact: item.impact,
          help: item.help,
          nodes: item.nodes.map((node) => node.target),
        }));
    });

    const expected = await page.evaluate(() => {
      const selector = [
        'a[href]',
        'button:not([disabled])',
        'summary',
        'input:not([disabled]):not([type="hidden"])',
        'select:not([disabled])',
        'textarea:not([disabled])',
        '[tabindex]:not([tabindex="-1"])',
      ].join(',');
      const visible = (element) => {
        if (element.closest('details:not([open])') && element.tagName !== 'SUMMARY') return false;
        if (element.closest('dialog:not([open])')) return false;
        if (typeof element.checkVisibility === 'function') {
          return element.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
        }
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
      };
      return [...document.querySelectorAll(selector)]
        .filter(visible)
        .map((element, index) => {
          const id = `cobogo-${index}`;
          element.dataset.cobogoA11yId = id;
          return {
            id,
            tag: element.tagName.toLowerCase(),
            label: element.getAttribute('aria-label') || element.textContent?.trim().replace(/\s+/g, ' ').slice(0, 80) || element.getAttribute('name') || '',
          };
        });
    });

    await page.evaluate(() => {
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    });

    const reached = new Set();
    const focusFailures = [];
    const maxTabs = Math.max(expected.length * 2 + 8, 12);
    for (let step = 0; step < maxTabs; step += 1) {
      await page.keyboard.press('Tab');
      const state = await page.evaluate(() => {
        const element = document.activeElement;
        if (!(element instanceof HTMLElement)) return null;
        const id = element.dataset.cobogoA11yId ?? null;
        const style = getComputedStyle(element);
        const visibleFocus = element.matches(':focus-visible') && (
          (style.outlineStyle !== 'none' && style.outlineWidth !== '0px') ||
          style.boxShadow !== 'none'
        );
        return { id, visibleFocus };
      });
      if (!state?.id) continue;
      reached.add(state.id);
      if (!state.visibleFocus) focusFailures.push(state.id);
      if (reached.size === expected.length) break;
    }

    const missing = expected.filter((control) => !reached.has(control.id));
    const uniqueFocusFailures = [...new Set(focusFailures)];
    const result = {
      route: route || '/',
      url,
      viewport,
      ui_generation: uiGeneration,
      ui_generation_matches: uiGenerationMatches,
      expected_controls: expected.length,
      reached_controls: reached.size,
      missing_controls: missing,
      focus_failures: uniqueFocusFailures,
      serious_or_critical_axe_violations: violations,
    };
    results.push(result);

    if (!uiGenerationMatches || violations.length || missing.length || uniqueFocusFailures.length) failed = true;
    await page.close();
  }
  await context.close();
}

await browser.close();
const resolvedOutput = path.resolve(output);
fs.mkdirSync(path.dirname(resolvedOutput), { recursive: true });
fs.writeFileSync(resolvedOutput, JSON.stringify({ revision, base_url: baseUrl, results }, null, 2));
console.log(JSON.stringify({ revision, results }, null, 2));

if (failed) process.exit(1);
