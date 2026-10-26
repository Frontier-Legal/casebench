import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { shapes, typeOf } from './json-schema.ts';

const published = (name: string) =>
	JSON.parse(
		readFileSync(new URL(`../../../casebench/formats/schemas/${name}/1.0.json`, import.meta.url), 'utf8'),
	);

test('an optional reference reads as the definition or null', () => {
	assert.deepEqual(typeOf({ anyOf: [{ $ref: '#/$defs/Provenance' }, { type: 'null' }] }), {
		type: 'Provenance | null',
		refs: ['Provenance'],
	});
});

test('a list and a map name what they hold', () => {
	assert.equal(typeOf({ type: 'array', items: { $ref: '#/$defs/Fact' } }).type, 'Fact[]');
	assert.equal(typeOf({ type: 'object', additionalProperties: { type: 'integer' } }).type, 'map of integer');
	assert.equal(typeOf({ type: 'array', items: { enum: ['documents', 'searches'] } }).type, '("documents" | "searches")[]');
});

test('the case reference lists the top level first, then each definition once', () => {
	const tables = shapes(published('case'));
	assert.equal(tables[0]!.name, null);
	assert.deepEqual(
		tables[0]!.fields.map((f) => f.name),
		['id', 'task', 'reference', 'metrics', 'tags', 'provenance', 'approval', 'extensions'],
	);
	const names = tables.slice(1).map((t) => t.name);
	assert.equal(new Set(names).size, names.length);
	for (const needed of ['Task', 'Reference', 'Fact', 'Evidence', 'Criterion', 'Approval']) {
		assert.ok(names.includes(needed), needed);
	}
});

test('an enumeration definition lists its values', () => {
	const approval = shapes(published('case')).find((t) => t.name === 'Approval');
	assert.deepEqual(approval?.values, ['draft', 'approved']);
});

test('every published format can be read into tables', () => {
	for (const name of ['case', 'suite', 'report', 'document', 'profile']) {
		const tables = shapes(published(name));
		assert.ok(tables[0]!.fields.length > 0, name);
	}
});
