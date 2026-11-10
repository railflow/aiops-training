// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import mermaid from 'astro-mermaid';
import starlightLinksValidator from 'starlight-links-validator';

// astro-mermaid must come before starlight so it can handle ```mermaid blocks first.
export default defineConfig({
	integrations: [
		mermaid({ theme: 'default', autoTheme: true }),
		starlight({
			title: 'Example product docs',
			description: 'A small docs-as-code site: Markdown in git, built by CI, served by nginx. Day 28 of the course.',
			favicon: '/favicon.svg',
			logo: {
				light: './src/assets/logo-light.svg',
				dark: './src/assets/logo-dark.svg',
				alt: 'Docs home',
				replacesTitle: true,
			},
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/railflow/aiops-training' }],
			// Our pages legitimately show http://localhost:... URLs.
			plugins: [starlightLinksValidator({ errorOnLocalLinks: false })],
			customCss: ['./src/styles/custom.css'],
			sidebar: [
				{ label: 'Start here', items: [{ autogenerate: { directory: 'start' } }] },
				{ label: 'How-to guides', items: [{ autogenerate: { directory: 'how-to' } }] },
				{ label: 'Reference', items: [{ autogenerate: { directory: 'reference' } }] },
			],
		}),
	],
});
