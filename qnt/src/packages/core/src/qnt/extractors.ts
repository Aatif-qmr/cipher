/**
 * QNT Browser Extractors
 * Specific logic for crypto and research data sources.
 */

import { extractText, extractStructured, saveContent } from './browser_engine.js';

/**
 * Extract Fear & Greed Index value and classification.
 */
export async function extractFearGreed(): Promise<string> {
  const url = 'https://alternative.me/crypto/fear-and-greed-index/';
  const result = await extractText(url, '.fng-value');
  return saveContent(result, url, 'feargreed');
}

/**
 * Extract liquidation and funding data from CoinGlass.
 */
export async function extractCoinGlass(): Promise<string> {
  const url = 'https://www.coinglass.com/LiquidationData';
  const data = await extractStructured(url);
  const content = [
    'COINGLASS LIQUIDATIONS',
    '=====================',
    data.text,
    '',
    'TABLES FOUND:',
    ...data.tables.map(t => t.join('\n')),
  ].join('\n');
  return saveContent(content, url, 'coinglass');
}

/**
 * Extract recent papers from ArXiv.
 */
export async function extractArxivRecent(category = 'q-fin.TR'): Promise<string> {
  const url = `https://arxiv.org/list/${category}/recent`;
  const result = await extractText(url, '.list-title');
  return saveContent(result, url, 'arxiv');
}

/**
 * Generic page extraction.
 */
export async function extractAnyPage(url: string): Promise<string> {
  const result = await extractText(url);
  return saveContent(result, url, 'page');
}
