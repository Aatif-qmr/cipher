/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import type semver from 'semver';

export const FETCH_TIMEOUT_MS = 2000;

export interface UpdateInfo {
  latest: string;
  current: string;
  name: string;
  type?: semver.ReleaseType;
}

export interface UpdateObject {
  message: string;
  update: UpdateInfo;
  isUpdating?: boolean;
}

export async function checkForUpdates(
  _settings: unknown,
): Promise<UpdateObject | null> {
  // Auto-update disabled for qnt stability
  return null;
}
