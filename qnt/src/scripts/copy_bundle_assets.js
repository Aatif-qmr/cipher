/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import { copyFileSync, existsSync, mkdirSync, cpSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { glob } from 'glob';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const bundleDir = join(root, 'bundle');

// Create the bundle directory if it doesn't exist
if (!existsSync(bundleDir)) {
  mkdirSync(bundleDir);
}

// 1. Copy Sandbox definitions (.sb)
const sbFiles = glob.sync('packages/**/*.sb', { cwd: root });
for (const file of sbFiles) {
  copyFileSync(join(root, file), join(bundleDir, basename(file)));
}

// 2. Copy Policy definitions (.toml)
const policyDir = join(bundleDir, 'policies');
if (!existsSync(policyDir)) {
  mkdirSync(policyDir);
}

// Locate policy files specifically in the core package
const policyFiles = glob.sync('packages/core/src/policy/policies/*.toml', {
  cwd: root,
});

for (const file of policyFiles) {
  copyFileSync(join(root, file), join(policyDir, basename(file)));
}

console.log(`Copied ${policyFiles.length} policy files to bundle/policies/`);

// 3. Copy Documentation (docs/)
const docsSrc = join(root, 'docs');
const docsDest = join(bundleDir, 'docs');
if (existsSync(docsSrc)) {
  cpSync(docsSrc, docsDest, { recursive: true, dereference: true });
  console.log('Copied docs to bundle/docs/');
}

// 4. Copy Built-in Skills (packages/core/src/skills/builtin)
const builtinSkillsSrc = join(root, 'packages/core/src/skills/builtin');
const builtinSkillsDest = join(bundleDir, 'builtin');
if (existsSync(builtinSkillsSrc)) {
  cpSync(builtinSkillsSrc, builtinSkillsDest, {
    recursive: true,
    dereference: true,
  });
  console.log('Copied built-in skills to bundle/builtin/');
}

// 5. Copy DevTools package so the external dynamic import resolves at runtime
const devtoolsSrc = join(root, 'packages/devtools');
const devtoolsDest = join(
  bundleDir,
  'node_modules',
  '@google',
  'gemini-cli-devtools',
);
const devtoolsDistSrc = join(devtoolsSrc, 'dist');
if (existsSync(devtoolsDistSrc)) {
  mkdirSync(devtoolsDest, { recursive: true });
  cpSync(devtoolsDistSrc, join(devtoolsDest, 'dist'), {
    recursive: true,
    dereference: true,
  });
  copyFileSync(
    join(devtoolsSrc, 'package.json'),
    join(devtoolsDest, 'package.json'),
  );
  console.log('Copied devtools package to bundle/node_modules/');
}

// 6. Copy bundled chrome-devtools-mcp
const bundleMcpSrc = join(root, 'packages/core/dist/bundled');
const bundleMcpDest = join(bundleDir, 'bundled');
if (existsSync(bundleMcpSrc)) {
  cpSync(bundleMcpSrc, bundleMcpDest, { recursive: true, dereference: true });
  console.log('Copied bundled chrome-devtools-mcp to bundle/bundled/');
}

// 7. Copy extension examples
const extensionExamplesSrc = join(root, 'packages/cli/examples');
const extensionExamplesDest = join(bundleDir, 'examples');
const EXCLUDED_EXAMPLE_DIRS = ['.git', 'node_modules', 'dist'];
if (existsSync(extensionExamplesSrc)) {
  cpSync(extensionExamplesSrc, extensionExamplesDest, {
    recursive: true,
    dereference: true,
    filter: (src) => !EXCLUDED_EXAMPLE_DIRS.some((dir) => src.includes(dir)),
  });
  console.log('Copied extension examples to bundle/examples/');
}

// 8. Copy vendor directory
const vendorSrc = join(root, 'packages/core/vendor');
const vendorDest = join(bundleDir, 'vendor');
if (existsSync(vendorSrc)) {
  cpSync(vendorSrc, vendorDest, { recursive: true, dereference: true });
  console.log('Copied vendor directory to bundle/vendor/');
}

console.log('Assets copied to bundle/');
