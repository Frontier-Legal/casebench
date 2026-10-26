import assert from 'node:assert/strict';
import { globSync, readFileSync } from 'node:fs';
import { test } from 'node:test';

const pages = globSync('src/content/docs/**/*.{md,mdx}');

const frontmatter = (text: string) => text.match(/^---\n([\s\S]*?)\n---/)?.[1] ?? '';

test('every page says what it is for in a description search engines and link previews show', () => {
	assert.ok(pages.length > 0);
	for (const page of pages) {
		const description = frontmatter(readFileSync(page, 'utf8')).match(/^description:\s*"?(.+?)"?\s*$/m)?.[1] ?? '';
		assert.ok(description.length >= 40, `${page} has no description of 40 characters or more`);
	}
});

test('no page uses an em dash or an en dash', () => {
	for (const page of pages) {
		assert.doesNotMatch(readFileSync(page, 'utf8'), /[–—]/, page);
	}
});
