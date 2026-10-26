import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { projectVersion, release, versionMenu } from './versions.ts';

test('the menu names the release being read by its major and minor version', () => {
	assert.equal(release('0.5.1'), '0.5');
	assert.deepEqual(versionMenu('0.5.1', []), { current: '0.5', archived: [] });
});

test('the version comes from the package being documented', () => {
	const pyproject = readFileSync(new URL('../../../pyproject.toml', import.meta.url), 'utf8');
	assert.match(projectVersion(pyproject), /^\d+\.\d+\.\d+/);
});

test('an archived release is listed by its label and address', () => {
	const menu = versionMenu('0.6.0', [{ label: '0.5', url: 'https://0-5.casebench.dev/' }]);
	assert.deepEqual(menu.archived, [{ label: '0.5', url: 'https://0-5.casebench.dev/' }]);
});

test('an entry a reader could not follow fails the build', () => {
	assert.throws(() => versionMenu('0.6.0', [{ label: '0.5' }]), /needs a url/);
	assert.throws(() => versionMenu('0.6.0', [{ label: '0.5', url: 'http://0-5.casebench.dev' }]), /needs a url/);
	assert.throws(() => versionMenu('0.6.0', [{ label: '0.6', url: 'https://0-6.casebench.dev/' }]), /being built/);
});

test('the repository lists only valid archived versions', () => {
	const listed = JSON.parse(readFileSync(new URL('../../versions.json', import.meta.url), 'utf8'));
	assert.doesNotThrow(() => versionMenu('999.0.0', listed));
});
