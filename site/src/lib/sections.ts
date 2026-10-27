/** The site's top-level sections, in the order the header lists them, and which one a path is in. */

const SECTIONS = [
	{ href: '/developers/', label: 'casebench.nav.developers' },
	{ href: '/lawyers/', label: 'casebench.nav.lawyers' },
	{ href: '/integrations/', label: 'casebench.nav.integrations' },
	{ href: '/examples/', label: 'casebench.nav.examples' },
	{ href: '/changelog/', label: 'casebench.nav.changelog' },
] as const;

export interface Section {
	href: string;
	/** A UI string key, translated by the page. */
	label: (typeof SECTIONS)[number]['label'];
	current: boolean;
}

/** Every section, with the one holding `pathname` marked; a locale folder in front of the path is ignored. */
export function sections(pathname: string, locales: readonly string[] = []): Section[] {
	const parts = pathname.split('/').filter(Boolean);
	if (parts.length && locales.includes(parts[0]!)) parts.shift();
	const first = `/${parts[0] ?? ''}/`;
	return SECTIONS.map((section) => ({ ...section, current: section.href === first }));
}
