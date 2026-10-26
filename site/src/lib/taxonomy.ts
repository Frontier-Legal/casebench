/**
 * Which reader a page is for and which of the four kinds of documentation it is, read from the page's folder.
 *
 * The folders follow the same split everywhere: `<audience>/tutorials`, `<audience>/guides`,
 * `<audience>/concepts` and `<audience>/reference`. A page's frontmatter may name either value instead.
 */

export const AUDIENCES = ['developers', 'lawyers', 'everyone'] as const;
export const KINDS = ['tutorial', 'how-to', 'concept', 'reference', 'overview', 'example'] as const;

export type Audience = (typeof AUDIENCES)[number];
export type Kind = (typeof KINDS)[number];

export interface Placement {
	audience: Audience;
	kind: Kind;
}

const KIND_BY_FOLDER: Record<string, Kind> = {
	tutorials: 'tutorial',
	guides: 'how-to',
	concepts: 'concept',
	reference: 'reference',
};

/** Each top-level section with the reader it is written for and the kind its pages are when no folder says. */
const SECTIONS: Record<string, Placement> = {
	developers: { audience: 'developers', kind: 'overview' },
	lawyers: { audience: 'lawyers', kind: 'overview' },
	integrations: { audience: 'developers', kind: 'how-to' },
	examples: { audience: 'developers', kind: 'example' },
	changelog: { audience: 'everyone', kind: 'reference' },
};

/**
 * The placement of the page with this content id, or `null` for a page outside every section, such as the home page.
 * `locales` are the locale folders to skip at the start of the id.
 */
export function placement(
	id: string,
	declared: Partial<Placement> = {},
	locales: readonly string[] = [],
): Placement | null {
	const parts = id.split('/').filter(Boolean);
	if (parts.length && locales.includes(parts[0]!)) parts.shift();

	const section = SECTIONS[parts[0] ?? ''];
	if (!section) return null;

	// A section's own index page is its overview; examples keep their kind even in a subfolder.
	const folder = parts.length > 2 ? KIND_BY_FOLDER[parts[1]!] : undefined;
	const kind = parts.length === 1 ? 'overview' : (folder ?? section.kind);

	return {
		audience: declared.audience ?? section.audience,
		kind: declared.kind ?? kind,
	};
}
