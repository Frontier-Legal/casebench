// @ts-check
import starlight from '@astrojs/starlight';
import { defineConfig } from 'astro/config';
import starlightLinksValidator from 'starlight-links-validator';
import starlightOpenAPI, { openAPISidebarGroups } from 'starlight-openapi';
import starlightSidebarTopics from 'starlight-sidebar-topics';

const SITE = 'https://casebench.dev';
const REPOSITORY = 'https://github.com/Frontier-Legal/casebench';

/**
 * A sidebar group whose pages are listed in the order of their `sidebar.order`.
 * @param {string} label
 * @param {string} directory
 */
const group = (label, directory, collapsed = false) => ({
	label,
	collapsed,
	items: [{ autogenerate: { directory } }],
});

export default defineConfig({
	site: SITE,
	trailingSlash: 'always',
	integrations: [
		starlight({
			title: 'Casebench',
			description:
				'Measure the legal accuracy of an AI system against real court decisions and lawyer-written references.',
			logo: { src: './src/assets/logo.svg', alt: '' },
			favicon: '/favicon.svg',
			social: [{ icon: 'github', label: 'GitHub', href: REPOSITORY }],
			editLink: { baseUrl: `${REPOSITORY}/edit/main/site/` },
			lastUpdated: true,
			defaultLocale: 'root',
			locales: {
				root: { label: 'English', lang: 'en' },
			},
			customCss: [
				'@fontsource-variable/geist',
				'@fontsource-variable/source-serif-4',
				'@fontsource-variable/jetbrains-mono',
				'./src/styles/tokens.css',
				'./src/styles/content.css',
			],
			expressiveCode: {
				themes: ['github-dark-default', 'github-light-default'],
				styleOverrides: {
					borderRadius: '0.625rem',
					borderColor: 'var(--cb-border)',
					codeFontFamily: 'var(--sl-font-mono)',
					codeFontSize: '0.8125rem',
					codeLineHeight: '1.7',
					uiFontFamily: 'var(--sl-font)',
					frames: {
						shadowColor: 'transparent',
						editorTabBarBackground: 'var(--cb-surface-raised)',
						terminalTitlebarBackground: 'var(--cb-surface-raised)',
					},
				},
			},
			head: [
				{ tag: 'meta', attrs: { property: 'og:image', content: `${SITE}/og.png` } },
				{ tag: 'meta', attrs: { property: 'og:image:width', content: '1200' } },
				{ tag: 'meta', attrs: { property: 'og:image:height', content: '630' } },
				{ tag: 'meta', attrs: { name: 'twitter:card', content: 'summary_large_image' } },
				{ tag: 'meta', attrs: { name: 'theme-color', content: '#fbfbfa', media: '(prefers-color-scheme: light)' } },
				{ tag: 'meta', attrs: { name: 'theme-color', content: '#0c0d10', media: '(prefers-color-scheme: dark)' } },
			],
			components: {
				Header: './src/components/overrides/Header.astro',
				PageTitle: './src/components/overrides/PageTitle.astro',
			},
			plugins: [
				starlightOpenAPI([
					{
						base: 'developers/reference/capture-api',
						schema: './openapi/capture-server.yaml',
						sidebar: { label: 'Capture server API', collapsed: true, operations: { badges: true } },
					},
				]),
				starlightSidebarTopics(
					[
						{
							id: 'developers',
							label: 'Developers',
							link: '/developers/',
							icon: 'seti:config',
							items: [
								{ label: 'Start here', items: ['developers', 'developers/install'] },
								group('Tutorials', 'developers/tutorials'),
								{
									label: 'How-to guides',
									items: [
										group('Set up', 'developers/guides/setup'),
										group('Connect', 'developers/guides/connect', true),
										group('Capture', 'developers/guides/capture', true),
										group('Build suites', 'developers/guides/suites', true),
										group('Run and compare', 'developers/guides/runs', true),
										group('Work with lawyers', 'developers/guides/team', true),
										group('Maintain a setup', 'developers/guides/maintain', true),
									],
								},
								group('Concepts', 'developers/concepts', true),
								{
									label: 'Reference',
									collapsed: true,
									items: [
										'developers/reference/cli',
										'developers/reference/configuration',
										group('File formats', 'developers/reference/formats', true),
										'developers/reference/run-folder',
										'developers/reference/labels',
										'developers/reference/environment',
										...openAPISidebarGroups,
									],
								},
							],
						},
						{
							id: 'lawyers',
							label: 'Lawyers',
							link: '/lawyers/',
							icon: 'open-book',
							items: [
								{ label: 'Start here', items: ['lawyers'] },
								group('Tutorials', 'lawyers/tutorials'),
								group('How-to guides', 'lawyers/guides'),
								group('Concepts', 'lawyers/concepts'),
								group('Reference', 'lawyers/reference'),
							],
						},
						{
							id: 'integrations',
							label: 'Integrations',
							link: '/integrations/',
							icon: 'puzzle',
							items: [
								'integrations',
								group('Agent SDKs', 'integrations/sdks'),
								group('Document stores', 'integrations/stores'),
								group('Judge models', 'integrations/models'),
								group('Tracing', 'integrations/tracing'),
								group('Extend Casebench', 'integrations/extend'),
							],
						},
						{
							id: 'examples',
							label: 'Examples',
							link: '/examples/',
							icon: 'document',
							items: ['examples', group('Worked examples', 'examples/walkthroughs')],
						},
						{
							label: 'Changelog',
							link: '/changelog/',
							icon: 'list-format',
						},
					],
					{
						exclude: ['/', '/changelog'],
						topics: { developers: ['/developers/reference/capture-api', '/developers/reference/capture-api/**'] },
					},
				),
				// The API pages are generated by starlight-openapi, which the validator does not see.
				starlightLinksValidator({ exclude: ['/developers/reference/capture-api/', '/developers/reference/capture-api/**'] }),
			],
		}),
	],
});
