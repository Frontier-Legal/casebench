import assert from 'node:assert/strict';
import { test } from 'node:test';

import { sections } from './sections.ts';

const current = (pathname: string, locales: string[] = []) =>
	sections(pathname, locales)
		.filter((s) => s.current)
		.map((s) => s.href);

test('a lawyer page marks the lawyer section in the header', () => {
	assert.deepEqual(current('/lawyers/concepts/scores/'), ['/lawyers/']);
});

test('a generated API page marks the developer section', () => {
	assert.deepEqual(current('/developers/reference/capture-api/operations/forward/'), ['/developers/']);
});

test('the home page marks no section', () => {
	assert.deepEqual(current('/'), []);
});

test('a translated path marks the same section', () => {
	assert.deepEqual(current('/tr/examples/', ['tr']), ['/examples/']);
});
