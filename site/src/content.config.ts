import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';
import { docsLoader, i18nLoader } from '@astrojs/starlight/loaders';
import { docsSchema, i18nSchema } from '@astrojs/starlight/schema';

import { AUDIENCES, KINDS } from './lib/taxonomy';

const docs = defineCollection({
	loader: docsLoader(),
	schema: docsSchema({
		extend: z.object({
			// Both are read from the page's folder; a page outside the usual folders names them here.
			audience: z.enum(AUDIENCES).optional(),
			kind: z.enum(KINDS).optional(),
		}),
	}),
});

const i18n = defineCollection({
	loader: i18nLoader(),
	schema: i18nSchema({
		extend: z.object({
			'casebench.nav.label': z.string(),
			'casebench.audience.developers': z.string(),
			'casebench.audience.lawyers': z.string(),
			'casebench.audience.everyone': z.string(),
			'casebench.kind.tutorial': z.string(),
			'casebench.kind.how-to': z.string(),
			'casebench.kind.concept': z.string(),
			'casebench.kind.reference': z.string(),
			'casebench.kind.overview': z.string(),
			'casebench.kind.example': z.string(),
			'casebench.nav.developers': z.string(),
			'casebench.nav.lawyers': z.string(),
			'casebench.nav.integrations': z.string(),
			'casebench.nav.examples': z.string(),
			'casebench.nav.changelog': z.string(),
		}),
	}),
});

// The release notes the release tooling writes at the repository's root, shown on the changelog page.
const changelog = defineCollection({ loader: glob({ pattern: 'CHANGELOG.md', base: '..' }) });

export const collections = { docs, i18n, changelog };
