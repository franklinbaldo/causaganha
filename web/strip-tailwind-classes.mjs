#!/usr/bin/env node
/**
 * Strip non-functional Tailwind-like utility classes from .astro and .tsx files.
 * Preserves custom project classes and Pico CSS classes.
 */
import { readFileSync, writeFileSync } from 'fs';
import { glob } from 'fs/promises';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Classes to KEEP (project-specific + Pico CSS)
const KEEP_PREFIXES = [
  'card', 'badge', 'stat-value', 'stat-label',
  'heatmap-', 'bar-',
  'gradient-bg', 'hero-pattern', 'floating', 'stat-card', 'nav-focus',
  'shimmer',
  // Pico
  'container', 'grid', 'secondary', 'outline', 'contrast',
  // Custom semantic colors
  'cg-', 'text-accent', 'text-success', 'text-danger', 'text-warning', 'text-info',
  'bg-accent', 'bg-success', 'bg-danger', 'bg-warning', 'bg-info',
  'bg-accent-muted', 'bg-accent-light', 'bg-success-muted', 'bg-danger-muted', 'bg-warning-muted',
  'border-l-danger',
  // Keep color-related custom classes used in the project
  'accent',
];

// Exact classes to keep
const KEEP_EXACT = new Set([
  'card', 'card-hover', 'badge', 'badge-success', 'badge-warning', 'badge-danger', 'badge-accent',
  'stat-value', 'stat-label',
  'gradient-bg', 'hero-pattern', 'floating', 'stat-card', 'nav-focus', 'shimmer',
  'container', 'grid', 'secondary', 'outline', 'contrast',
  'text-accent', 'text-success', 'text-danger', 'text-warning', 'text-info',
  'bg-accent', 'bg-accent-muted', 'bg-accent-light',
  'bg-success-muted', 'bg-danger-muted', 'bg-warning-muted',
  'border-l-danger',
]);

function shouldKeep(cls) {
  if (KEEP_EXACT.has(cls)) return true;
  for (const prefix of KEEP_PREFIXES) {
    if (cls.startsWith(prefix)) return true;
  }
  return false;
}

// Tailwind-like utility patterns
const TW_PATTERNS = [
  // Dark mode
  /^dark:/,
  // Responsive
  /^(sm|md|lg|xl|2xl):/,
  // Pseudo
  /^(hover|focus|focus-visible|active|group-hover|focus-within|disabled):/,
  // Colors / backgrounds / borders
  /^(bg|text|border|ring|outline|divide|placeholder)-(transparent|current|black|white|slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)/,
  /^(from|via|to)-(transparent|current|black|white|slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)/,
  // Spacing
  /^-?(p|px|py|pt|pb|pl|pr|ps|pe|m|mx|my|mt|mb|ml|mr|ms|me)-/,
  /^(space-[xy]|gap)-/,
  /^gap-/,
  // Sizing
  /^(w|h|min-w|min-h|max-w|max-h)-/,
  /^(size)-/,
  // Typography
  /^(text-(xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl|8xl|9xl))/,
  /^text-\[/,
  /^(font-(sans|serif|mono|thin|extralight|light|normal|medium|semibold|bold|extrabold|black))/,
  /^(tracking|leading)-/,
  /^(uppercase|lowercase|capitalize|normal-case)$/,
  /^(tabular-nums|oldstyle-nums|proportional-nums|lining-nums)$/,
  /^font-variant-numeric$/,
  /^(underline|overline|line-through|no-underline)$/,
  /^(truncate|text-ellipsis|text-clip)$/,
  /^(whitespace|break|hyphens)-/,
  // Layout
  /^(flex|inline-flex|block|inline-block|inline|hidden|table|contents|flow-root|list-item)$/,
  /^(flex-(row|col|wrap|nowrap|1|auto|initial|none|grow|shrink))/,
  /^flex$/,
  /^(items|justify|content|self|place)-(start|end|center|between|around|evenly|stretch|baseline|auto)/,
  /^(order)-/,
  /^grid$/,
  /^(grid-cols|grid-rows|col-span|row-span|auto-cols|auto-rows|grid-flow)-/,
  /^(gap|gap-x|gap-y)-/,
  // Positioning
  /^(static|fixed|absolute|relative|sticky)$/,
  /^(inset|top|right|bottom|left|start|end)-/,
  /^-?(top|right|bottom|left|inset)-/,
  /^z-/,
  // Borders / Rounding / Shadow
  /^(rounded|border|shadow|ring|outline)-/,
  /^(rounded|border|shadow)$/,
  // Display helpers
  /^(sr-only|not-sr-only)$/,
  /^(visible|invisible|collapse)$/,
  /^(opacity)-/,
  // Transitions / Animations
  /^(transition|duration|ease|delay|animate)-/,
  /^transition$/,
  // Transforms
  /^(scale|rotate|translate|skew|origin)-/,
  /^transform$/,
  // Overflow / Scroll
  /^(overflow|overscroll|scroll)-/,
  // Filters
  /^(blur|brightness|contrast|drop-shadow|grayscale|hue-rotate|invert|saturate|sepia|backdrop)-/,
  // Misc
  /^(cursor|select|resize|appearance|pointer-events|will-change)-/,
  /^antialiased$/,
  /^subpixel-antialiased$/,
  /^(object|aspect)-/,
  /^(isolate|isolation-auto)$/,
  /^(mix-blend|bg-blend)-/,
  /^(accent|caret)-/,
  /^(columns)-/,
  /^(break-(before|after|inside))-/,
  /^(decoration|box-decoration)-/,
  /^(float|clear)-/,
  /^(fill|stroke)-/,
  // Tailwind arbitrary values
  /^\[.*\]$/,
  /^!/,
  // bg-gradient, bg-clip
  /^bg-(gradient|clip|origin|repeat|size|position|no-repeat|cover|contain)/,
  // flex-shrink-0, grow-0 etc
  /^(grow|shrink)-/,
  /^(grow|shrink)$/,
  /^(basis)-/,
  // Misc single-word utilities that aren't custom
  /^(container)$/, // we'll add this back with Pico
];

function isTailwindUtility(cls) {
  if (shouldKeep(cls)) return false;
  for (const pattern of TW_PATTERNS) {
    if (pattern.test(cls)) return true;
  }
  return false;
}

function processClassAttribute(classStr) {
  const classes = classStr.split(/\s+/).filter(Boolean);
  const kept = [];
  const removed = [];
  for (const cls of classes) {
    if (isTailwindUtility(cls)) {
      removed.push(cls);
    } else {
      kept.push(cls);
    }
  }
  return { kept, removed };
}

function processFile(filePath) {
  const content = readFileSync(filePath, 'utf-8');
  let totalRemoved = [];

  // Process class="..." and className="..." (static string attributes)
  const processed = content.replace(
    /(class(?:Name)?)\s*=\s*"([^"]*?)"/g,
    (match, attr, classes) => {
      const { kept, removed } = processClassAttribute(classes);
      totalRemoved.push(...removed);
      if (kept.length === 0) {
        return ''; // Remove the entire attribute
      }
      return `${attr}="${kept.join(' ')}"`;
    }
  );

  // Also handle className={`...`} template literals - strip TW classes from static parts
  // and className={"..."} expressions
  const processed2 = processed.replace(
    /(class(?:Name)?)\s*=\s*\{`([^`]*?)`\}/g,
    (match, attr, templateContent) => {
      // Process static text portions of template literal (not ${...} expressions)
      const newContent = templateContent.replace(
        /(?:^|(?<=\}))([\w\s/.:[\]-]+?)(?=$|\$\{)/g,
        (staticPart) => {
          const { kept, removed } = processClassAttribute(staticPart);
          totalRemoved.push(...removed);
          return kept.join(' ');
        }
      );
      // Clean up extra whitespace
      const cleaned = newContent.replace(/\s+/g, ' ').trim();
      if (!cleaned && !templateContent.includes('${')) {
        return '';
      }
      return `${attr}={\`${newContent}\`}`;
    }
  );

  // Clean up leftover empty attributes and whitespace issues
  let final = processed2;
  // Remove completely empty class/className attributes
  final = final.replace(/\s*class(?:Name)?=""\s*/g, ' ');
  // Clean up double+ spaces in tags
  final = final.replace(/(<\w+(?:\s+[^>]*?))\s{2,}/g, '$1 ');
  // Clean up space before >
  final = final.replace(/\s+>/g, '>');

  if (totalRemoved.length > 0) {
    writeFileSync(filePath, final);
  }

  return totalRemoved;
}

// Main
const files = [];
for await (const f of glob('src/**/*.{astro,tsx}', { cwd: __dirname })) {
  files.push(__dirname + '/' + f);
}

let totalClasses = 0;
let totalFiles = 0;

for (const file of files.sort()) {
  const removed = processFile(file);
  if (removed.length > 0) {
    totalFiles++;
    totalClasses += removed.length;
    const shortPath = file.replace(__dirname + '/', '');
    console.log(`${shortPath}: removed ${removed.length} classes`);
    // Show first few unique removed classes
    const unique = [...new Set(removed)].slice(0, 8);
    console.log(`  examples: ${unique.join(', ')}${removed.length > 8 ? '...' : ''}`);
  }
}

console.log(`\nTotal: ${totalClasses} utility classes removed from ${totalFiles} files`);
