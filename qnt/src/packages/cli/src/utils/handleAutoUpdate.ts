/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

export function _setUpdateStateForTesting(_value: boolean) {}

export function isUpdateInProgress() {
  return false;
}

export async function waitForUpdateCompletion(
  _timeoutMs = 30000,
): Promise<void> {
  return;
}

export function handleAutoUpdate(
  _info: unknown,
  _settings: unknown,
  _projectRoot: string,
  _spawnFn: unknown = null,
) {
  // Auto-update disabled for qnt stability
  return;
}

export function setUpdateHandler(
  _addItem: unknown,
  _setUpdateInfo: unknown,
) {
  return () => {};
}
