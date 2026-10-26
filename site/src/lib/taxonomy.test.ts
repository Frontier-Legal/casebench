import assert from 'node:assert/strict';
import { test } from 'node:test';

import { placement } from './taxonomy.ts';

test('a developer tutorial is labelled as a tutorial for developers', () => {
	assert.deepEqual(placement('developers/tutorials/first-report'), {
		audience: 'developers',
		kind: 'tutorial',
	});
});

test('a lawyer guide is labelled as a how-to guide for lawyers', () => {
	assert.deepEqual(placement('lawyers/guides/write-a-case-by-hand'), {
		audience: 'lawyers',
		kind: 'how-to',
	});
});

test('a nested how-to guide keeps its kind', () => {
	assert.deepEqual(placement('developers/guides/connect/python-agent'), {
		audience: 'developers',
		kind: 'how-to',
	});
});

test('a section index is its overview', () => {
	assert.deepEqual(placement('lawyers'), { audience: 'lawyers', kind: 'overview' });
	assert.deepEqual(placement('integrations'), { audience: 'developers', kind: 'overview' });
});

test('an integration page is a how-to guide unless it says otherwise', () => {
	assert.deepEqual(placement('integrations/sdks/anthropic'), { audience: 'developers', kind: 'how-to' });
	assert.deepEqual(placement('integrations/tracing/opentelemetry', { kind: 'reference' }), {
		audience: 'developers',
		kind: 'reference',
	});
});

test('an example in a subfolder stays an example', () => {
	assert.deepEqual(placement('examples/walkthroughs/typescript-agent'), {
		audience: 'developers',
		kind: 'example',
	});
});

test('the home page has no placement', () => {
	assert.equal(placement('index'), null);
	assert.equal(placement(''), null);
});

test('a translated page is placed like the original', () => {
	assert.deepEqual(placement('tr/lawyers/concepts/scores', {}, ['tr']), {
		audience: 'lawyers',
		kind: 'concept',
	});
});
