/**
 * Which documentation versions the header's menu lists: the one being read, then each archived release.
 *
 * An archived version is the site built at that release's tag and deployed at its own address, so its links keep
 * working as they were. `versions.json` lists them, newest first.
 */

export interface ArchivedVersion {
	/** As readers name the release, such as `0.4`. */
	label: string;
	/** Where that version's site is deployed, such as `https://0-4.casebench.dev/`. */
	url: string;
}

export interface VersionMenu {
	current: string;
	archived: ArchivedVersion[];
}

/** The `major.minor` of a package version: `0.5.1` reads as `0.5`. */
export function release(version: string): string {
	const match = version.match(/^(\d+)\.(\d+)/);
	if (!match) throw new Error(`not a version: ${version}`);
	return `${match[1]}.${match[2]}`;
}

/** The version in a `pyproject.toml`, from its `[project]` table. */
export function projectVersion(pyproject: string): string {
	const project = pyproject.split(/^\[project\]$/m)[1]?.split(/^\[/m)[0] ?? '';
	const match = project.match(/^version\s*=\s*"([^"]+)"/m);
	if (!match) throw new Error('pyproject.toml has no [project] version');
	return match[1]!;
}

/** The menu for the version being built, refusing an entry a reader could not follow. */
export function versionMenu(version: string, archived: unknown): VersionMenu {
	if (!Array.isArray(archived)) throw new Error('versions.json must hold a list');
	const current = release(version);
	const entries = archived.map((entry, i) => {
		const { label, url } = (entry ?? {}) as Partial<ArchivedVersion>;
		if (!label || typeof label !== 'string') throw new Error(`versions.json entry ${i} has no label`);
		if (!url || !/^https:\/\/[^/]+\/$/.test(url)) {
			throw new Error(`versions.json entry ${label} needs a url like https://0-4.casebench.dev/`);
		}
		if (label === current) throw new Error(`versions.json lists ${label}, the version being built`);
		return { label, url };
	});
	return { current, archived: entries };
}
